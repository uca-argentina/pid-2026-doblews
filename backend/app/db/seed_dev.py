"""Development seed: the accounts and firms needed to log in for the first time.

A script and not a migration, because a migration runs on every database that
applies `alembic upgrade head` — production included — and these are fake users
with a known password. Idempotent: running it twice changes nothing.

    uv run python -m app.db.seed_dev
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    Account,
    Firm,
    FirmMember,
    PlatformMember,
    Project,
    Recipe,
    Resource,
    Role,
    UnitOfMeasure,
)
from app.services.catalog_admin import CatalogError, InvalidReferenceError, RecipeLineInput
from app.services.firm_recipes import create_firm_recipe
from app.services.project import ProjectError, create_project
from app.services.takeoff import add_line

SUPPORT = ("Soporte warchitecture", "soporte@warchitecture.test")

# Two firms and not one: isolation between tenants is only demonstrable when
# there is a second firm to be excluded from.
FIRMS = [
    ("Estudio Norte", "contacto@estudionorte.test", "Ana Gómez", "ana@estudionorte.test"),
    ("Estudio Sur", "contacto@estudiosur.test", "Bruno Díaz", "bruno@estudiosur.test"),
]

# The rest of Estudio Norte's roster, so the roster screen (HU-2) does not open
# with only its owner in it, and HU-3's client picker has a client to offer.
# (firm, name, email, firm role)
MEMBERS = [
    ("Estudio Norte", "Alba Ruiz", "alba@estudionorte.test", "architect"),
    ("Estudio Norte", "Carla Méndez", "carla@estudionorte.test", "client"),
]

# One work with a take-off already loaded, so HU-5's screen can be reviewed
# without typing quantities first. Led by the architect, with the firm's client
# on it, so both views — with and without costs — have someone to log in as.
# (firm, work, lead email, client email, [(recipe, quantity, note)])
DEMO_WORK = (
    "Estudio Norte",
    "Casa Rodríguez",
    "alba@estudionorte.test",
    "carla@estudionorte.test",
    [
        ("Pared de ladrillo común 15cm", "70", "planta baja"),
        ("Pared de ladrillo común 15cm", "50", "planta alta"),
        ("Contrapiso de cascote", "60", None),
    ],
)


# One recipe of Estudio Norte's own (HU-9), so its catalogue shows both origins
# and Estudio Sur has something it must not see.
# (firm, recipe, unit code, description, [(resource, quantity per unit)])
FIRM_RECIPE = (
    "Estudio Norte",
    "Revoque grueso a la cal",
    "m2",
    "Revoque grueso de 1,5 cm, mezcla 1/4:1:4 (cemento : cal : arena fina). "
    "Así lo resuelve el estudio; no es parte del catálogo del sistema.",
    [
        ("Cemento portland (bolsa 50 kg)", "0.0500"),
        ("Cal hidratada (bolsa 25 kg)", "0.1500"),
        ("Arena fina", "0.0200"),
        ("Oficial", "0.6000"),
        ("Ayudante", "0.6000"),
    ],
)


def _role(session: Session, code: str, scope: str) -> Role:
    role = session.scalar(select(Role).where(Role.code == code, Role.scope == scope))
    if role is None:
        raise RuntimeError(
            f"The role {code}/{scope} does not exist. Run `alembic upgrade head` first: "
            "the permission catalogue is seeded by migration, not by this script."
        )
    return role


def _account(session: Session, name: str, email: str, password: str) -> tuple[Account, bool]:
    """Find by email, or create. Email is the identity, so it is the lookup key."""
    email = email.lower()
    account = session.scalar(select(Account).where(Account.email == email))
    if account is not None:
        return account, False

    account = Account(name=name, email=email, password_hash=hash_password(password))
    session.add(account)
    session.flush()  # assigns the id the membership rows below need
    return account, True


def _firm(session: Session, name: str, contact_email: str) -> tuple[Firm, bool]:
    firm = session.scalar(select(Firm).where(Firm.name == name))
    if firm is not None:
        return firm, False

    firm = Firm(name=name, contact_email=contact_email.lower())
    session.add(firm)
    session.flush()
    return firm, True


def seed(session: Session, password: str) -> None:
    support_role = _role(session, "support", "platform")
    owner_role = _role(session, "owner", "firm")

    name, email = SUPPORT
    support, created = _account(session, name, email, password)
    print(f"{'creada ' if created else 'ya estaba'}  cuenta   {email}")

    if not session.get(PlatformMember, (support.id, support_role.id)):
        session.add(PlatformMember(account_id=support.id, role_id=support_role.id))
        print(f"creada    rol      {email} -> support (platform)")

    firms: dict[str, Firm] = {}
    for firm_name, firm_email, owner_name, owner_email in FIRMS:
        firm, created = _firm(session, firm_name, firm_email)
        firms[firm_name] = firm
        print(f"{'creado  ' if created else 'ya estaba'}  estudio  {firm_name}")

        owner, created = _account(session, owner_name, owner_email, password)
        print(f"{'creada ' if created else 'ya estaba'}  cuenta   {owner_email}")

        if not session.get(FirmMember, (firm.id, owner.id)):
            session.add(FirmMember(firm_id=firm.id, account_id=owner.id, role_id=owner_role.id))
            print(f"creada    padron   {owner_email} -> owner de {firm_name}")

    for firm_name, member_name, member_email, role_code in MEMBERS:
        firm = firms[firm_name]
        role = _role(session, role_code, "firm")

        member, created = _account(session, member_name, member_email, password)
        print(f"{'creada ' if created else 'ya estaba'}  cuenta   {member_email}")

        # Only a missing row is added. One that exists is left as it is, active
        # or not: whoever removed that person from the roster by hand while
        # trying the app did it on purpose, and re-seeding should not undo it.
        if not session.get(FirmMember, (firm.id, member.id)):
            session.add(FirmMember(firm_id=firm.id, account_id=member.id, role_id=role.id))
            print(f"creada    padron   {member_email} -> {role_code} de {firm_name}")

    _seed_firm_recipe(session, firms)
    _seed_demo_work(session, firms)


def _seed_firm_recipe(session: Session, firms: dict[str, Firm]) -> None:
    """The firm's own recipe, through the same service HU-9's routes use.

    Created only if the firm has no active recipe of that name, and left alone
    otherwise, so edits made on the screen survive a re-seed. Skipped with a
    notice when the catalogue it draws from was edited by hand and a resource
    it needs is gone.
    """
    firm_name, recipe_name, unit_code, description, lines = FIRM_RECIPE
    firm = firms[firm_name]

    exists = session.scalar(
        select(Recipe.id).where(
            Recipe.firm_id == firm.id, Recipe.name == recipe_name, Recipe.is_active
        )
    )
    if exists is not None:
        print(f"ya estaba  receta   {recipe_name} ({firm_name})")
        return

    session.flush()  # the firm row, if it was created above
    unit_id = session.scalar(select(UnitOfMeasure.id).where(UnitOfMeasure.code == unit_code))
    resource_ids = {
        name: resource_id
        for name, resource_id in session.execute(
            select(Resource.name, Resource.id).where(Resource.is_active)
        )
    }
    try:
        create_firm_recipe(
            session,
            firm.id,
            name=recipe_name,
            description=description,
            unit_of_measure_id=unit_id,
            lines=[
                RecipeLineInput(resource_ids[name], Decimal(quantity)) for name, quantity in lines
            ],
        )
    except KeyError as missing:
        print(f"salteada  receta   {recipe_name}: el catálogo ya no tiene {missing}")
        return
    except (CatalogError, InvalidReferenceError) as error:
        print(f"salteada  receta   {recipe_name}: {error.detail}")
        return
    print(f"creada    receta   {recipe_name} ({firm_name})")


def _seed_demo_work(session: Session, firms: dict[str, Firm]) -> None:
    """The demo work and its take-off, through the same services the API uses.

    Created only if no work of that name exists in the firm, and left alone
    otherwise: lines someone edited or removed while trying the screen stay as
    they left them. Going through create_project and add_line means the lead
    assignment and the recipe check happen exactly as they would over HTTP.

    Skipped with a notice, rather than failing the whole seed, when the roster
    no longer fits: whoever changed Alba or Carla's role by hand did it on
    purpose, and create_project refuses before writing anything.
    """
    firm_name, work_name, lead_email, client_email, lines = DEMO_WORK
    firm = firms[firm_name]

    exists = session.scalar(
        select(Project.id).where(Project.firm_id == firm.id, Project.name == work_name)
    )
    if exists is not None:
        print(f"ya estaba  obra     {work_name}")
        return

    lead = session.scalar(select(Account).where(Account.email == lead_email))
    client = session.scalar(select(Account).where(Account.email == client_email))
    session.flush()  # the roster rows added above, so the client check can see them

    try:
        project = create_project(
            session,
            firm.id,
            created_by=lead.id,
            name=work_name,
            address="Av. Siempreviva 742",
            client_account_id=client.id,
        )
    except ProjectError as error:
        print(f"salteada  obra     {work_name}: {error.detail}")
        return
    print(f"creada    obra     {work_name} (lead {lead_email}, cliente {client_email})")

    for recipe_name, quantity, note in lines:
        # General recipes only: a firm may own one with the same name (HU-9).
        recipe_id = session.scalar(
            select(Recipe.id).where(Recipe.name == recipe_name, Recipe.firm_id.is_(None))
        )
        add_line(session, project, recipe_id=recipe_id, quantity=Decimal(quantity), note=note)
        print(f"creada    computo  {quantity} x {recipe_name}")


def main() -> None:
    settings = get_settings()
    # Printed on purpose: this writes rows, and the only thing standing between
    # a demo seed and a real database is which URL is configured.
    print(f"sembrando en {settings.database_url}\n")

    with SessionLocal() as session:
        seed(session, settings.seed_password)
        session.commit()

    print(f"\nlisto. contraseña de todas las cuentas: {settings.seed_password!r}")


if __name__ == "__main__":
    main()
