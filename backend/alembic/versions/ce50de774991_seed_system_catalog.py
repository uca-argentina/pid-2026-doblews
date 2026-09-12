"""seed system catalog

The initial content of the catalogue T-04 created: seven materials and the three
recipes ADR-003 promises — wall, sub-floor and screed. This is what makes the
application useful from the first login, which is the argument ADR-003 section 1
used to decide the catalogue belongs to the platform and not to each firm.

Its meaning changes the day HU-8 ships (ADR-005 section 4): it stops being *the*
way the catalogue is loaded and becomes its starting content, still used by tests
and by fresh environments. Until then, this is the only place these rows are
written.

Written out literally rather than imported from app/, for the same reason as the
three seeds before it: a migration is a frozen snapshot, and importing live code
would make this one seed whatever the catalogue happens to look like months from
now.

**The proportions, and where they come from.** Each recipe states what *one* unit
takes, and its description carries the assumption that makes the number readable —
a per-m2 recipe without a declared thickness is ambiguous. The wall reproduces the
worked example of ADR-003 (60 bricks and 0.25 bags of cement per m2, which is the
"7.200 ladrillos y 30 bolsas de cemento" its Consequences section promises for a
120 m2 wall). These are reference figures for a student project, not a quantity
surveyor's table: they are meant to be defensible and round, and to be corrected
by someone who knows the trade.

Revision ID: ce50de774991
Revises: 7669bb30b200
Create Date: 2026-09-12

"""

from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ce50de774991"
down_revision: str | Sequence[str] | None = "7669bb30b200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


resource_table = sa.table(
    "resource",
    sa.column("type", sa.String),
    sa.column("name", sa.String),
    sa.column("unit_of_measure_id", sa.BigInteger),
    sa.column("reference_price", sa.Numeric),
)

recipe_table = sa.table(
    "recipe",
    sa.column("name", sa.String),
    sa.column("description", sa.Text),
    sa.column("unit_of_measure_id", sa.BigInteger),
)

recipe_resource_table = sa.table(
    "recipe_resource",
    sa.column("recipe_id", sa.BigInteger),
    sa.column("resource_id", sa.BigInteger),
    sa.column("quantity_per_unit", sa.Numeric),
)


# (name, unit code, reference price in ARS). Every row is type 'material': the
# other two values of the CHECK exist without rows until labour and equipment are
# seeded (ADR-003 section 3). Names are trade names and stay in Spanish — they are
# displayed, not compared in code.
MATERIALS: list[tuple[str, str, Decimal]] = [
    ("Ladrillo común", "u", Decimal("230.00")),
    ("Cemento portland (bolsa 50 kg)", "bolsa", Decimal("16000.00")),
    ("Cal hidratada (bolsa 25 kg)", "bolsa", Decimal("11500.00")),
    ("Arena gruesa", "m3", Decimal("45000.00")),
    ("Arena fina", "m3", Decimal("48000.00")),
    ("Cascote", "m3", Decimal("38000.00")),
    ("Hidrófugo", "kg", Decimal("4500.00")),
]

# (name, unit code, description). The description is where the assumption lives:
# the thickness the per-m2 figures were computed at, and the mortar mix.
RECIPES: list[tuple[str, str, str]] = [
    (
        "Pared de ladrillo común 15cm",
        "m2",
        "Mampostería de ladrillo común de 0,15 m de espesor, asentada con mortero "
        "1:¼:3 (cemento : cal : arena). Se computan 0,045 m³ de mortero por m², que "
        "contempla las juntas de 1,5 a 2 cm que pide un ladrillo común.",
    ),
    (
        "Contrapiso de cascote",
        "m2",
        "Contrapiso de cascote de 0,10 m de espesor, mezcla 1:4:8 (cemento : arena : cascote).",
    ),
    (
        "Carpeta de cemento",
        "m2",
        "Carpeta de nivelación de 0,025 m de espesor, mezcla 1:3 (cemento : arena fina) "
        "con hidrófugo en el agua de empaste.",
    ),
]

# recipe name -> [(material name, quantity per one unit of the recipe)]
RECIPE_LINES: dict[str, list[tuple[str, Decimal]]] = {
    "Pared de ladrillo común 15cm": [
        ("Ladrillo común", Decimal("60.0000")),
        ("Cemento portland (bolsa 50 kg)", Decimal("0.2500")),
        ("Cal hidratada (bolsa 25 kg)", Decimal("0.2000")),
        ("Arena gruesa", Decimal("0.0470")),
    ],
    "Contrapiso de cascote": [
        ("Cemento portland (bolsa 50 kg)", Decimal("0.3000")),
        ("Arena gruesa", Decimal("0.0450")),
        ("Cascote", Decimal("0.0900")),
    ],
    "Carpeta de cemento": [
        ("Cemento portland (bolsa 50 kg)", Decimal("0.2250")),
        ("Arena fina", Decimal("0.0250")),
        ("Hidrófugo", Decimal("0.3000")),
    ],
}


def _ids_by(bind, column: str, table: str) -> dict[str, int]:
    """Map a natural key to its id.

    The ids are IDENTITY, so nothing guarantees which number a given unit or
    material was assigned. Everything below joins by name or by code.
    """
    rows = bind.execute(sa.text(f"SELECT {column}, id FROM {table}")).all()
    return {key: row_id for key, row_id in rows}


def upgrade() -> None:
    """Seed the seven materials, the three recipes and their lines."""
    bind = op.get_bind()
    unit_id = _ids_by(bind, "code", "unit_of_measure")

    op.bulk_insert(
        resource_table,
        [
            {
                "type": "material",
                "name": name,
                "unit_of_measure_id": unit_id[unit_code],
                "reference_price": price,
            }
            for name, unit_code, price in MATERIALS
        ],
    )
    op.bulk_insert(
        recipe_table,
        [
            {
                "name": name,
                "description": description,
                "unit_of_measure_id": unit_id[unit_code],
            }
            for name, unit_code, description in RECIPES
        ],
    )

    # Resolved after the inserts above, because that is when the ids exist.
    resource_id = _ids_by(bind, "name", "resource")
    recipe_id = _ids_by(bind, "name", "recipe")

    op.bulk_insert(
        recipe_resource_table,
        [
            {
                "recipe_id": recipe_id[recipe_name],
                "resource_id": resource_id[material_name],
                "quantity_per_unit": quantity,
            }
            for recipe_name, lines in RECIPE_LINES.items()
            for material_name, quantity in lines
        ],
    )


def downgrade() -> None:
    """Remove exactly the rows this migration added, and nothing else.

    The lines go first and by hand: recipe_resource cascades from recipe, but
    relying on that would also delete lines somebody added to a seeded recipe
    through HU-8's screen.
    """
    bind = op.get_bind()

    for recipe_name, lines in RECIPE_LINES.items():
        for material_name, _ in lines:
            bind.execute(
                sa.text(
                    "DELETE FROM recipe_resource"
                    " WHERE recipe_id = (SELECT id FROM recipe WHERE name = :recipe)"
                    "   AND resource_id = (SELECT id FROM resource WHERE name = :material)"
                ),
                {"recipe": recipe_name, "material": material_name},
            )

    for name, *_ in RECIPES:
        bind.execute(sa.text("DELETE FROM recipe WHERE name = :name"), {"name": name})

    for name, *_ in MATERIALS:
        bind.execute(sa.text("DELETE FROM resource WHERE name = :name"), {"name": name})
