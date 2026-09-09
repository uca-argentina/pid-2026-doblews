"""What the API says about a firm and about the caller's place in it.

Lives apart from auth.py because HU-2 and HU-3 keep reading these shapes long
after the login screen stops being interesting.
"""

from pydantic import BaseModel


class RoleOut(BaseModel):
    """A role as the UI needs it: the stable code plus the label to render.

    name is the Spanish label already seeded in role.name ("Propietario",
    "Arquitecto"). Sending it means the frontend never keeps its own code ->
    label dictionary, which would drift from the seed the day a role is renamed.
    """

    # Stable identifier. The frontend may branch on it to decide which menu to
    # paint, and never to decide what is allowed: that is resolved against the
    # database on every request (ADR-002 section 9).
    code: str
    name: str


class FirmSummary(BaseModel):
    """One row of "the firms I belong to", as the firm picker renders it."""

    id: int
    name: str
    role: RoleOut
