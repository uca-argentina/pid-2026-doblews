"""seed hour unit and labor/equipment

T-06 (docs/historias/sprint-2.md): the unit `h`, two labour resources and one
piece of equipment, and the hours each of the three seeded recipes takes per m2.
Without these rows HU-10 and HU-11 have nothing to show. No DDL: ADR-003 section
3, as precised by T-05, already says what the columns mean for these rows — the
unit is always `h`, reference_price is the cost per hour, and quantity_per_unit
is the yield, hours of that resource per unit of recipe.

**It seeds what is missing and never overwrites (ADR-005 section 4).** This
migration runs after HU-8 shipped, so an environment's catalogue may already
differ from the seed by the time it applies. Every insert is conditional, in SQL:
a resource support already loaded under the same name is kept as it is, and a
seeded recipe support renamed or deactivated simply gets no hours. That is also
why this seed does not use bulk_insert like the ones before it.

**The yields, and where they come from.** Reference figures for a student
project, round and defensible, meant to be corrected by someone who knows the
trade — the same standard as T-04's materials. A bricklayer and a helper raise
about 8 m2 of 15cm common-brick wall per 8-hour day, hence 1 h/m2 each; the
wall's mortar is mixed by hand, so it takes no mixer. The sub-floor and the
screed are mixer work: the helper carries and the mixer runs for a fraction of
the hour the crew spends per m2. Prices sit at the same level as the materials
seeded by T-04.

Written out literally rather than imported from app/, for the same reason as the
seeds before it: a migration is a frozen snapshot.

Revision ID: 3d8e1b7a9c24
Revises: 5c12ccef2ab5
Create Date: 2026-09-25

"""

from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d8e1b7a9c24"
down_revision: str | Sequence[str] | None = "5c12ccef2ab5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (code, name, abbreviation, magnitude), the same shape as HU-0's seven units.
HOUR = ("h", "Hora", "h", "tiempo")

# (type, name, cost per hour in ARS). Every one of them is measured in `h`.
RESOURCES: list[tuple[str, str, Decimal]] = [
    ("labor", "Oficial", Decimal("5500.00")),
    ("labor", "Ayudante", Decimal("4600.00")),
    ("equipment", "Hormigonera", Decimal("3000.00")),
]

# recipe name -> [(resource name, hours per one m2 of the recipe)]
RECIPE_HOURS: dict[str, list[tuple[str, Decimal]]] = {
    "Pared de ladrillo común 15cm": [
        ("Oficial", Decimal("1.0000")),
        ("Ayudante", Decimal("1.0000")),
    ],
    "Contrapiso de cascote": [
        ("Oficial", Decimal("0.3000")),
        ("Ayudante", Decimal("0.6000")),
        ("Hormigonera", Decimal("0.1000")),
    ],
    "Carpeta de cemento": [
        ("Oficial", Decimal("0.4000")),
        ("Ayudante", Decimal("0.4000")),
        ("Hormigonera", Decimal("0.0500")),
    ],
}


def upgrade() -> None:
    """Seed the hour unit, the three resources and their recipe lines, where missing."""
    bind = op.get_bind()

    code, name, abbreviation, magnitude = HOUR
    bind.execute(
        sa.text(
            "INSERT INTO unit_of_measure (code, name, abbreviation, magnitude)"
            " VALUES (:code, :name, :abbreviation, :magnitude)"
            " ON CONFLICT (code) DO NOTHING"
        ),
        {"code": code, "name": name, "abbreviation": abbreviation, "magnitude": magnitude},
    )

    # Mirrors uq_resource_name_active: an active resource with the same name,
    # in any case, is the one support already loaded, and it wins. :name is cast
    # once because it is used twice, and Postgres will not guess one type for both.
    for resource_type, resource_name, price in RESOURCES:
        bind.execute(
            sa.text(
                "INSERT INTO resource (type, name, unit_of_measure_id, reference_price)"
                " SELECT :type, CAST(:name AS varchar),"
                "        (SELECT id FROM unit_of_measure WHERE code = :unit), :price"
                " WHERE NOT EXISTS ("
                "     SELECT 1 FROM resource"
                "      WHERE lower(name) = lower(CAST(:name AS varchar)) AND is_active"
                " )"
            ),
            {"type": resource_type, "name": resource_name, "unit": code, "price": price},
        )

    # Both ends resolved by name among active rows: a recipe that is gone or
    # renamed matches nothing, and a line that already exists is left alone.
    for recipe_name, lines in RECIPE_HOURS.items():
        for resource_name, hours in lines:
            bind.execute(
                sa.text(
                    "INSERT INTO recipe_resource (recipe_id, resource_id, quantity_per_unit)"
                    " SELECT rc.id, rs.id, :hours"
                    "   FROM recipe rc, resource rs"
                    "  WHERE lower(rc.name) = lower(:recipe) AND rc.is_active"
                    "    AND lower(rs.name) = lower(:resource) AND rs.is_active"
                    " ON CONFLICT (recipe_id, resource_id) DO NOTHING"
                ),
                {"recipe": recipe_name, "resource": resource_name, "hours": hours},
            )


def downgrade() -> None:
    """Remove the rows this migration adds, in the reverse order of their FKs.

    Lines first and by hand, as in the T-04 seed. The unit goes last, and fails
    loudly if support has since loaded another resource in hours: dropping it
    would leave that resource with nothing to be measured in.
    """
    bind = op.get_bind()

    for recipe_name, lines in RECIPE_HOURS.items():
        for resource_name, _ in lines:
            bind.execute(
                sa.text(
                    "DELETE FROM recipe_resource"
                    " WHERE recipe_id IN (SELECT id FROM recipe WHERE name = :recipe)"
                    "   AND resource_id IN (SELECT id FROM resource WHERE name = :resource)"
                ),
                {"recipe": recipe_name, "resource": resource_name},
            )

    for _, resource_name, _ in RESOURCES:
        bind.execute(sa.text("DELETE FROM resource WHERE name = :name"), {"name": resource_name})

    bind.execute(sa.text("DELETE FROM unit_of_measure WHERE code = :code"), {"code": HOUR[0]})
