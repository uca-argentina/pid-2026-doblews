"""Development seed: the accounts and firms needed to log in for the first time.

A script and not a migration, because a migration runs on every database that
applies `alembic upgrade head` — production included — and these are fake users
with a known password. Idempotent: running it twice changes nothing.

    uv run python -m app.db.seed_dev
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Account, Firm, FirmMember, PlatformMember, Role

SUPPORT = ("Soporte warchitecture", "soporte@warchitecture.test")

# Two firms and not one: isolation between tenants is only demonstrable when
# there is a second firm to be excluded from.
FIRMS = [
    ("Estudio Norte", "contacto@estudionorte.test", "Ana Gómez", "ana@estudionorte.test"),
    ("Estudio Sur", "contacto@estudiosur.test", "Bruno Díaz", "bruno@estudiosur.test"),
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

    for firm_name, firm_email, owner_name, owner_email in FIRMS:
        firm, created = _firm(session, firm_name, firm_email)
        print(f"{'creado  ' if created else 'ya estaba'}  estudio  {firm_name}")

        owner, created = _account(session, owner_name, owner_email, password)
        print(f"{'creada ' if created else 'ya estaba'}  cuenta   {owner_email}")

        if not session.get(FirmMember, (firm.id, owner.id)):
            session.add(FirmMember(firm_id=firm.id, account_id=owner.id, role_id=owner_role.id))
            print(f"creada    padron   {owner_email} -> owner de {firm_name}")


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
