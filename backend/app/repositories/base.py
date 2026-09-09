"""The one place a read remembers which firm it belongs to.

ADR-002 section 8 is blunt about why this exists: "Los permisos responden '¿qué
podés hacer?'; el tenant responde '¿sobre qué universo de filas?'. Un permiso no
salva de un WHERE olvidado." Guarding an endpoint with a permission says the
caller may list projects, not that they may list *these* projects.

So every read of a business table goes through a subclass of this, and no
service builds a select() by hand. modelo-datos-sprint-1.md section 3.2 asks for
exactly that, and section 3.3 puts the is_active filter in the same place,
"porque el día que se olviden en uno solo aparece un material dado de baja en un
desplegable".
"""

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.base import Base

# Every model this can scope has to carry both. Checked when the subclass is
# defined rather than trusted, since getting it wrong would silently widen a
# read instead of failing.
REQUIRED_COLUMNS = ("firm_id", "is_active")


class FirmScopedRepository[ModelT: Base]:
    """Reads of one table, already narrowed to one firm and to live rows.

    Built with the firm resolved from the URL, so a repository instance cannot
    outlive the request that proved the caller belongs there.
    """

    model: type[ModelT]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        missing = [column for column in REQUIRED_COLUMNS if not hasattr(cls.model, column)]
        if missing:
            raise TypeError(
                f"{cls.__name__} scopes {cls.model.__name__}, which has no {', '.join(missing)}. "
                "A firm-scoped repository can only read a table that carries the tenant."
            )

    def __init__(self, db: Session, firm_id: int) -> None:
        self.db = db
        self.firm_id = firm_id

    def select(self) -> Select:
        """The starting point of every read: this firm's live rows, and nothing else.

        Subclasses narrow it further; none of them may widen it, because there
        is no way to remove a where() from a Select.
        """
        return select(self.model).where(
            self.model.firm_id == self.firm_id,
            self.model.is_active,
        )
