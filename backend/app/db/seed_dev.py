"""Development seed: the accounts and firms needed to log in for the first time.

A script and not a migration, because a migration runs on every database that
applies `alembic upgrade head` — production included — and these are fake users
with a known password. Idempotent: running it twice changes nothing.

    uv run python -m app.db.seed_dev
"""

from decimal import Decimal

from sqlalchemy import make_url, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    Account,
    BudgetVersion,
    Firm,
    FirmMember,
    PlatformMember,
    Project,
    Recipe,
    Resource,
    Role,
    Supplier,
    UnitOfMeasure,
)
from app.services.budget_versions import BudgetVersionError, save_version
from app.services.catalog_admin import CatalogError, InvalidReferenceError, RecipeLineInput
from app.services.firm_recipes import create_firm_recipe
from app.services.project import ProjectError, create_project
from app.services.suppliers import InvalidMaterialError, add_price, create_supplier
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

# The demo work's first saved budget (HU-12), and a line loaded after it, so
# HU-19's dashboard opens with the updated budget above the original. The line
# is the firm's own recipe (FIRM_RECIPE), measured after the walls were.
# (version note, (recipe, quantity, note))
DEMO_BUDGET = ("Presupuesto inicial", ("Revoque grueso a la cal", "220", "interior"))


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


# Estudio Norte's suppliers (HU-17), priced so HU-18's comparison has something
# to show on Casa Rodríguez. Norte is cheaper per unit but charges for delivery,
# Sur delivers free: Norte wins the work's 7,200 bricks, Sur wins a hundred, and
# at exactly 1,000 they tie. The lime is on nobody's list, so the work shows a
# material "sin proveedor".
# (firm, supplier, contact, phone, [(material, unit price, shipping)])
SUPPLIERS = [
    (
        "Estudio Norte",
        "Corralón Norte",
        "Marta Ríos",
        "388 555 0101",
        [
            ("Ladrillo común", "220.00", "5000.00"),
            ("Cemento portland (bolsa 50 kg)", "15500.00", "8000.00"),
        ],
    ),
    (
        "Estudio Norte",
        "Corralón Sur",
        "Hugo Paz",
        "388 555 0202",
        [
            ("Ladrillo común", "225.00", "0.00"),
            ("Cemento portland (bolsa 50 kg)", "15800.00", "0.00"),
        ],
    ),
    (
        "Estudio Norte",
        "Arenera del Río",
        None,
        "388 555 0303",
        [
            ("Arena gruesa", "42000.00", "12000.00"),
            ("Cascote", "36000.00", "12000.00"),
        ],
    ),
]


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
    _seed_demo_budget(session, firms)
    _seed_suppliers(session, firms)


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


def _demo_project(session: Session, firms: dict[str, Firm]) -> Project | None:
    """The demo work, if it is there and active.

    None when it was archived by hand, or never created because the roster
    was edited first (_seed_demo_work skips it then).
    """
    firm_name, work_name, *_ = DEMO_WORK
    session.flush()  # the work, if _seed_demo_work just created it
    return session.scalar(
        select(Project).where(
            Project.firm_id == firms[firm_name].id,
            Project.name == work_name,
            Project.is_active,
        )
    )


def _seed_demo_budget(session: Session, firms: dict[str, Firm]) -> None:
    """Save the demo work's v1, then load one more line on top of it.

    A step of its own and not part of _seed_demo_work, because the deployed
    environment already has the work from an earlier seed and that function
    skips it whole. This one asks its own question: does the work have any
    saved version? If it does, someone saved one on the screen, and the
    version numbers are theirs.
    """
    _, work_name, lead_email, *_ = DEMO_WORK
    note, (recipe_name, quantity, line_note) = DEMO_BUDGET

    project = _demo_project(session, firms)
    if project is None:
        print(f"salteado  presupuesto: la obra {work_name} no existe o no está activa")
        return
    saved = session.scalar(
        select(BudgetVersion.id).where(BudgetVersion.project_id == project.id).limit(1)
    )
    if saved is not None:
        print(f"ya estaba  presupuesto de {work_name}")
        return

    lead = session.scalar(select(Account).where(Account.email == lead_email))
    try:
        version = save_version(session, project, account_id=lead.id, note=note)
    except BudgetVersionError as error:
        print(f"salteado  presupuesto: {error.detail}")
        return
    print(f"creada    version  v{version.version_number} de {work_name} ({note})")

    # The firm's own recipe, not a general one of the same name.
    recipe_id = session.scalar(
        select(Recipe.id).where(
            Recipe.firm_id == project.firm_id, Recipe.name == recipe_name, Recipe.is_active
        )
    )
    if recipe_id is None:
        print(f"salteada  computo  {recipe_name}: el estudio ya no tiene esa receta")
        return
    add_line(session, project, recipe_id=recipe_id, quantity=Decimal(quantity), note=line_note)
    print(f"creada    computo  {quantity} x {recipe_name}, después de la v{version.version_number}")


def _seed_suppliers(session: Session, firms: dict[str, Firm]) -> None:
    """The firm's suppliers and their lists, through HU-17's own service.

    A supplier is created with its list only if the firm has no active one of
    that name, and left alone otherwise, so prices edited on the screen survive a
    re-seed. A material the catalogue no longer has is skipped with a notice.
    """
    for firm_name, name, contact, phone, prices in SUPPLIERS:
        firm = firms[firm_name]
        exists = session.scalar(
            select(Supplier.id).where(
                Supplier.firm_id == firm.id, Supplier.name == name, Supplier.is_active
            )
        )
        if exists is not None:
            print(f"ya estaba  proveedor {name} ({firm_name})")
            continue

        session.flush()  # the firm row, if it was created above
        supplier = create_supplier(session, firm.id, name=name, contact_name=contact, phone=phone)
        print(f"creado    proveedor {name} ({firm_name})")

        for material, unit_price, shipping in prices:
            resource_id = session.scalar(select(Resource.id).where(Resource.name == material))
            try:
                add_price(
                    session,
                    firm.id,
                    supplier.id,
                    resource_id=resource_id,
                    unit_price=Decimal(unit_price),
                    shipping_cost=Decimal(shipping),
                )
            except InvalidMaterialError as error:
                print(f"salteado  precio    {material}: {error.detail}")
                continue
            print(f"creado    precio    {material} a {unit_price} + envío {shipping}")


def main() -> None:
    settings = get_settings()
    # Printed on purpose: this writes rows, and the only thing standing between
    # a demo seed and a real database is which URL is configured. Without the
    # password, which against a deployed database is a real secret.
    target = make_url(settings.database_url).render_as_string(hide_password=True)
    print(f"sembrando en {target}\n")

    with SessionLocal() as session:
        seed(session, settings.seed_password)
        session.commit()

    print(f"\nlisto. contraseña de todas las cuentas: {settings.seed_password!r}")


if __name__ == "__main__":
    main()
