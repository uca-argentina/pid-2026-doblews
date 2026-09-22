"""The only place that knows how a password is stored and checked.

Hides the algorithm behind two functions, so changing it later touches this file
and nothing else, and so no code path can write a plaintext password by accident.
"""

import bcrypt

# bcrypt silently ignores anything past the 72nd byte, which would make two
# different long passwords authenticate each other. Rejecting is safer than
# truncating, and API schemas should cap the field well below this.
MAX_PASSWORD_BYTES = 72


class PasswordTooLongError(ValueError):
    """Raised instead of letting bcrypt quietly ignore the tail of a password."""


def hash_password(password: str) -> str:
    """Return the hash to store in account.password_hash.

    The salt is generated per call, so the same password hashes differently for
    two accounts and a leaked table cannot be attacked with one rainbow table.
    """
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(
            f"password is {len(encoded)} bytes, bcrypt accepts at most {MAX_PASSWORD_BYTES}"
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password against a stored hash.

    Returns False rather than raising on a malformed or empty hash: callers are
    login paths, and there the answer to "is this hash broken?" is still no.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False
