"""What the API says about a work's saved budget versions (HU-12).

The detail reuses the three-group shape of HU-11, so the same screen renders a
version and the draft. It is not the same schema, though, and the difference is
the point: a frozen item carries its unit as the abbreviation it was saved with,
not a reference to the unit catalogue, because a receipt must render even if
that unit row changed since.
"""

from typing import Annotated

from pydantic import BaseModel, StringConstraints, field_validator

# Same limit as a take-off line's note: it is the same kind of label, written in
# the same kind of box.
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=150)]


class Comparacion(BaseModel):
    """The save form: a name or note, and nothing else.

    Nothing about the numbers is sent. What gets frozen is what the server
    computes at that moment — a client that could propose its own totals would
    be a client that could propose the wrong ones.
    """

    note: Note | None = None

    @field_validator("note")
    @classmethod
    def blank_is_no_note(cls, note: str | None) -> str | None:
        # Same normalisation as a take-off line: "   " is not a label.
        return note or None
