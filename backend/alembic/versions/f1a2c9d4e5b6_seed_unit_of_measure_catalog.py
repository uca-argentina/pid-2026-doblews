"""seed unit of measure catalog

HU-0 (docs/historias/sprint-1.md): the seven units materials and recipes are
allowed to be expressed in. Global to the platform and read-only at runtime
(ADR-003 section 7), so this is the only place these rows are ever written.

Written out literally rather than imported from app/, for the same reason as
the permission catalogue seed it follows: a migration is a frozen snapshot,
and importing live code would make this one seed whatever the model happens
to look like months from now.

Revision ID: f1a2c9d4e5b6
Revises: e0b3ec8a57c3
Create Date: 2026-09-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2c9d4e5b6"
down_revision: str | Sequence[str] | None = "e0b3ec8a57c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


unit_of_measure_table = sa.table(
    "unit_of_measure",
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("abbreviation", sa.String),
    sa.column("magnitude", sa.String),
)

# (code, name, abbreviation, magnitude), from HU-0's acceptance criteria.
UNITS_OF_MEASURE: list[tuple[str, str, str, str]] = [
    ("m2", "Metro cuadrado", "m2", "superficie"),
    ("m3", "Metro cúbico", "m3", "volumen"),
    ("ml", "Metro lineal", "ml", "longitud"),
    ("u", "Unidad", "u", "cantidad"),
    ("kg", "Kilogramo", "kg", "peso"),
    ("bolsa", "Bolsa", "bolsa", "cantidad"),
    ("lt", "Litro", "lt", "volumen"),
]


def upgrade() -> None:
    """Seed the seven units of measure."""
    op.bulk_insert(
        unit_of_measure_table,
        [
            {"code": code, "name": name, "abbreviation": abbreviation, "magnitude": magnitude}
            for code, name, abbreviation, magnitude in UNITS_OF_MEASURE
        ],
    )


def downgrade() -> None:
    """Remove exactly the seven units this migration added."""
    bind = op.get_bind()

    for code, *_ in UNITS_OF_MEASURE:
        bind.execute(
            sa.text("DELETE FROM unit_of_measure WHERE code = :code"),
            {"code": code},
        )
