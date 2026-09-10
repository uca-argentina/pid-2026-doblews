"""Model registry: importing this package registers every table on Base.metadata.

Alembic imports it so autogenerate and `alembic check` compare the database against
the whole schema; without it they see an empty one and propose dropping every table.
"""

from app.models.account import Account
from app.models.firm import Firm
from app.models.membership import FirmMember, PlatformMember
from app.models.project import Project, ProjectMember
from app.models.role import Permission, Role, RolePermission
from app.models.unit_of_measure import UnitOfMeasure

# Listed so the imports above read as the deliberate registry they are, rather
# than as unused imports waiting for someone to tidy them away.
__all__ = [
    "Account",
    "Firm",
    "FirmMember",
    "Permission",
    "PlatformMember",
    "Project",
    "ProjectMember",
    "Role",
    "RolePermission",
    "UnitOfMeasure",
]
