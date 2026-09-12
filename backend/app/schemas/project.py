"""What the API says about a work and about who it is being built for (HU-3)."""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, StringConstraints

# The same limits the columns carry, so an over-long name is a 422 naming the
# field rather than a DataError surfacing as a 500.
ProjectName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
Address = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]


class ProjectClientOut(BaseModel):
    """The client of a work, as the listing and the detail render them.

    Nested rather than flattened into client_id/client_name, because there is
    either a client or there is not, and one optional object says that once.
    """

    account_id: int
    name: str


class ProjectSummary(BaseModel):
    """One row of the project listing.

    Exactly what HU-3 asks the listing to show — "nombre, dirección, fecha
    estimada de inicio y cliente" — and not the description, which is a
    paragraph and belongs on the detail screen.
    """

    id: int
    name: str
    address: str | None
    estimated_start_date: date | None
    client: ProjectClientOut | None


class ProjectOut(ProjectSummary):
    """One work in full, for its detail screen."""

    description: str | None


class ProjectWrite(BaseModel):
    """The add and edit form: the whole editable state of a work.

    One schema for both, because HU-3 has one form and it sends every field
    every time. That is also why the edit is a PUT and not a PATCH: with the
    full body there is no difference between "I left this out" and "I cleared
    it", and null means empty in both directions — including for the client,
    which HU-3 says may stay empty.

    Nothing here is the tenant. firm_id comes from the URL, already checked
    against the caller's roster row, and a body that tried to name another firm
    would simply not be read.
    """

    name: ProjectName
    description: str | None = None
    address: Address | None = None
    # A calendar date, not an instant: "it starts on October 15th" has no time
    # and no timezone (modelo-datos 3.6).
    estimated_start_date: date | None = None
    # An account id and not an email: the picker is fed by this firm's roster
    # (HU-3), so the frontend already holds the id of everyone it may offer.
    client_account_id: int | None = None
