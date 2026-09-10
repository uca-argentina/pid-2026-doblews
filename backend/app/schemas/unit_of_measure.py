"""What the API says about a unit of measure."""

from pydantic import BaseModel


class UnitOfMeasureOut(BaseModel):
    """One row of the platform's unit of measure catalogue."""

    id: int
    code: str
    name: str
    abbreviation: str
    magnitude: str
