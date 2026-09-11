"""What the API says about the people on a firm's roster (HU-2)."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.firm import RoleOut


class MemberOut(BaseModel):
    """One row of the roster listing.

    Keyed by account_id because that is what identifies a member inside a firm:
    firm_member's primary key is (firm_id, account_id), and the firm already
    comes from the URL.
    """

    account_id: int
    # From the global account, not from this firm. The owner cannot edit either:
    # they are the person's identity everywhere, not a detail of this roster.
    name: str
    email: str
    role: RoleOut
    # Roster state, not account state: False means they left this firm and can
    # still log in and work in any other.
    is_active: bool
    joined_at: datetime
