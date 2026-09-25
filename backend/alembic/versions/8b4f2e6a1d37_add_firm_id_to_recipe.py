"""add firm_id to recipe

HU-9, ADR-006: a recipe can now belong to a firm. The catalogue gains a second
source of recipes next to the system one instead of a second table — a NULL
firm_id is a general recipe, exactly what every existing row already is, and a
value is the firm that owns it. project_recipe.recipe_id keeps pointing at one
table, which is the reason ADR-006 gives for not splitting it.

**Two unique indexes replace one (ADR-006 section 2).** A single index on
(firm_id, lower(name)) would stop protecting the general recipes: Postgres never
treats two NULLs as equal inside a unique index, so two general recipes could
share a name. The first index below is today's, narrowed to the general
recipes; the second is "unique within this firm". They never compare against
each other, so a firm's recipe may share a general recipe's name.

Revision ID: 8b4f2e6a1d37
Revises: 3d8e1b7a9c24
Create Date: 2026-09-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b4f2e6a1d37"
down_revision: str | Sequence[str] | None = "3d8e1b7a9c24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Give recipe an optional owner and scope its name uniqueness by it."""
    op.add_column("recipe", sa.Column("firm_id", sa.BigInteger(), nullable=True))
    # Simple and not composite: a recipe hangs off the firm directly, there is
    # no project in between to tie it to (ADR-006 section 1).
    op.create_foreign_key(op.f("fk_recipe_firm_id"), "recipe", "firm", ["firm_id"], ["id"])

    op.drop_index("uq_recipe_name_active", table_name="recipe")
    op.create_index(
        "uq_recipe_name_active_general",
        "recipe",
        [sa.literal_column("lower(name)")],
        unique=True,
        postgresql_where=sa.text("is_active AND firm_id IS NULL"),
    )
    op.create_index(
        "uq_recipe_name_active_firm",
        "recipe",
        ["firm_id", sa.literal_column("lower(name)")],
        unique=True,
        postgresql_where=sa.text("is_active AND firm_id IS NOT NULL"),
    )
    # "This firm's recipes": HU-9's screen and HU-5's picker. Partial, because
    # the general recipes are never looked up by firm.
    op.create_index(
        "ix_recipe_firm_id",
        "recipe",
        ["firm_id"],
        postgresql_where=sa.text("firm_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Back to one global catalogue of recipes.

    Fails if any firm has loaded a recipe: dropping the column would turn those
    rows into general recipes every firm sees, which is a leak, not a rollback.
    """
    firm_recipes = (
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM recipe WHERE firm_id IS NOT NULL"))
        .scalar_one()
    )
    if firm_recipes:
        raise RuntimeError(
            f"{firm_recipes} firm recipe(s) exist. Remove them before downgrading: "
            "without firm_id they would become general recipes visible to every firm."
        )

    op.drop_index("ix_recipe_firm_id", table_name="recipe")
    op.drop_index("uq_recipe_name_active_firm", table_name="recipe")
    op.drop_index("uq_recipe_name_active_general", table_name="recipe")
    op.create_index(
        "uq_recipe_name_active",
        "recipe",
        [sa.literal_column("lower(name)")],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.drop_constraint(op.f("fk_recipe_firm_id"), "recipe", type_="foreignkey")
    op.drop_column("recipe", "firm_id")
