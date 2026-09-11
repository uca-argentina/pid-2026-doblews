"""The rules for changing who is on a firm's roster (HU-2).

Plain functions over the session, like the rest of the services: they return
data and never raise HTTPException. Turning a broken rule into a status code is
the API layer's job.
"""

from typing import Literal, get_args

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Role

# The firm roles an owner may hand out, and the one place that leaves owner out.
# A second owner would break "exactly one active owner per firm" (ADR-002
# section 11.1), and transferring ownership is out of HU-2's scope. Keeping
# owner out of every add and every edit is what makes that invariant hold by
# construction instead of by checking.
#
# A Literal rather than a list so the request schemas can use it as a field
# type: asking for owner is then a 422 from Pydantic before any code runs.
AssignableFirmRole = Literal["architect", "client"]


def list_assignable_roles(db: Session) -> list[Role]:
    """The firm roles the add and edit forms offer, with their seeded labels.

    Read from the role table rather than written out here, so the labels are
    the ones the seed holds and the frontend keeps no dictionary of its own.
    No firm filter: the catalogue is the same for every firm (ADR-002 section 4).
    """
    return list(
        db.scalars(
            select(Role)
            .where(Role.scope == "firm", Role.code.in_(get_args(AssignableFirmRole)))
            .order_by(Role.code)
        )
    )
