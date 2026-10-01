"""create budget version schema

The three tables of ADR-007 section 1, which HU-12 freezes a work's budget into:
budget_version (the saved budget), budget_version_item (its numbers, grouped by
resource) and budget_version_line (its take-off lines, so it can be loaded back).

Three things here are deliberate rather than forgotten:

- None of the three gets a trg_*_updated_at trigger, and none carries is_active
  or updated_at. A version is never edited and never deactivated, so the trigger
  of modelo-datos 3.11 has nothing to keep. These are the first tables in the
  project where that is true, which is why it is written down here instead of
  being read later as an omission.
- budget_version_item.resource_id has no foreign key. A frozen item is a
  receipt: it has to render even if that resource is gone (ADR-007 section 2).
  budget_version_line.recipe_id does have one, because loading a version needs
  to know whether that recipe is still active today.
- The cascades from budget_version down to its items and lines go against the
  rule that a foreign key to business data never cascades (modelo-datos 3.3).
  That rule is about entities; these two are pure composition of one aggregate,
  the same category recipe_resource occupies with respect to recipe.

Revision ID: a4f7d2c8b901
Revises: c3e9a5d17f42
Create Date: 2026-10-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4f7d2c8b901"
down_revision: str | Sequence[str] | None = "c3e9a5d17f42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "budget_version",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("firm_id", sa.BigInteger(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=150), nullable=True),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'ARS'"), nullable=False),
        sa.Column("prices_as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version_number > 0", name=op.f("ck_budget_version_version_number_positive")
        ),
        sa.CheckConstraint("total >= 0", name=op.f("ck_budget_version_total_not_negative")),
        sa.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'", name=op.f("ck_budget_version_currency_iso_4217")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["account.id"], name=op.f("fk_budget_version_created_by")
        ),
        # Composite, against project (id, firm_id): a version of another firm's
        # work cannot be written, not merely refused.
        sa.ForeignKeyConstraint(
            ["project_id", "firm_id"],
            ["project.id", "project.firm_id"],
            name=op.f("fk_budget_version_project_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_budget_version")),
        sa.UniqueConstraint(
            "project_id", "version_number", name=op.f("uq_budget_version_project_id_version_number")
        ),
    )
    op.create_index("ix_budget_version_firm_id", "budget_version", ["firm_id"], unique=False)
    op.create_index("ix_budget_version_project_id", "budget_version", ["project_id"], unique=False)

    op.create_table(
        "budget_version_item",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("budget_version_id", sa.BigInteger(), nullable=False),
        # No foreign key on purpose. See the module docstring.
        sa.Column("resource_id", sa.BigInteger(), nullable=False),
        sa.Column("resource_name", sa.String(length=150), nullable=False),
        sa.Column("resource_type", sa.String(length=20), nullable=False),
        sa.Column("unit_abbreviation", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'ARS'"), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.CheckConstraint(
            "resource_type IN ('material', 'labor', 'equipment')",
            name=op.f("ck_budget_version_item_resource_type_valid"),
        ),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_budget_version_item_quantity_positive")),
        sa.CheckConstraint(
            "unit_price >= 0", name=op.f("ck_budget_version_item_unit_price_not_negative")
        ),
        sa.CheckConstraint(
            "subtotal >= 0", name=op.f("ck_budget_version_item_subtotal_not_negative")
        ),
        sa.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'", name=op.f("ck_budget_version_item_currency_iso_4217")
        ),
        sa.ForeignKeyConstraint(
            ["budget_version_id"],
            ["budget_version.id"],
            name=op.f("fk_budget_version_item_budget_version_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_budget_version_item")),
    )
    op.create_index(
        "ix_budget_version_item_budget_version_id",
        "budget_version_item",
        ["budget_version_id"],
        unique=False,
    )

    op.create_table(
        "budget_version_line",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("budget_version_id", sa.BigInteger(), nullable=False),
        # A real foreign key, unlike the item's resource_id. See the docstring.
        sa.Column("recipe_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("note", sa.String(length=150), nullable=True),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_budget_version_line_quantity_positive")),
        sa.ForeignKeyConstraint(
            ["budget_version_id"],
            ["budget_version.id"],
            name=op.f("fk_budget_version_line_budget_version_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"], ["recipe.id"], name=op.f("fk_budget_version_line_recipe_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_budget_version_line")),
    )
    op.create_index(
        "ix_budget_version_line_budget_version_id",
        "budget_version_line",
        ["budget_version_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema.

    No trigger to drop, unlike every other table-creating migration here: these
    three never had one.
    """
    op.drop_index("ix_budget_version_line_budget_version_id", table_name="budget_version_line")
    op.drop_table("budget_version_line")
    op.drop_index("ix_budget_version_item_budget_version_id", table_name="budget_version_item")
    op.drop_table("budget_version_item")
    op.drop_index("ix_budget_version_project_id", table_name="budget_version")
    op.drop_index("ix_budget_version_firm_id", table_name="budget_version")
    op.drop_table("budget_version")
