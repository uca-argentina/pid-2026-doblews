"""The platform's unit of measure catalogue (HU-0)."""

from fastapi import APIRouter

from app.api.deps import CurrentAccount, DbSession
from app.schemas.unit_of_measure import UnitOfMeasureOut
from app.services.catalog import list_units_of_measure

router = APIRouter(prefix="/units-of-measure", tags=["catalog"])


@router.get("", response_model=list[UnitOfMeasureOut])
def read_units_of_measure(account: CurrentAccount, db: DbSession) -> list[UnitOfMeasureOut]:
    """The whole catalogue: global to the platform, same for every caller.

    Requires a session (any active account) but no specific permission: there
    is no firm_id/project_id in the path to hang a requires(...) scope off, and
    every firm role needs to fill a "unidad" field with it sooner or later.
    """
    return [
        UnitOfMeasureOut(
            id=unit.id,
            code=unit.code,
            name=unit.name,
            abbreviation=unit.abbreviation,
            magnitude=unit.magnitude,
        )
        for unit in list_units_of_measure(db)
    ]
