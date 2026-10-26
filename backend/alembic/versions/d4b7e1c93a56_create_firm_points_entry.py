"""create firm points entry

The one table HU-23 writes: an entry per order line that earned points, written
when the order became received (ADR-012 section 4).

Two things here are deliberate rather than forgotten:

- No is_active, no updated_at and no trg_*_updated_at trigger. The table is
  immutable, like budget_version and its items: nothing deactivates an entry,
  because an order that was received is never reopened, and nothing updates one,
  because a points system that rewrote its past could not explain a number with
  the rule that earned it.
- No column holds a level or a running total. The firm's points are the sum of
  these rows, computed on every read, which is what the two indexes are for.

Revision ID: d4b7e1c93a56
Revises: c7f2a94b1e68
Create Date: 2026-10-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4b7e1c93a56"
down_revision: str | Sequence[str] | None = "c7f2a94b1e68"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RULE_CHECK = (
    "rule IN ('same_material_similar_quantity', 'same_material',"
    " 'same_supplier', 'first_purchase')"
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "firm_points_entry",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("firm_id", sa.BigInteger(), nullable=False),
        sa.Column("supplier_id", sa.BigInteger(), nullable=False),
        sa.Column("purchase_order_id", sa.BigInteger(), nullable=False),
        sa.Column("purchase_order_line_id", sa.BigInteger(), nullable=False),
        sa.Column("resource_id", sa.BigInteger(), nullable=False),
        sa.Column("rule", sa.String(length=40), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("previous_quantity", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(RULE_CHECK, name=op.f("ck_firm_points_entry_rule_valid")),
        # first_purchase earns zero on purpose; nothing ever subtracts.
        sa.CheckConstraint("points >= 0", name=op.f("ck_firm_points_entry_points_not_negative")),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_firm_points_entry_quantity_positive")),
        sa.CheckConstraint(
            "previous_quantity IS NULL OR previous_quantity > 0",
            name=op.f("ck_firm_points_entry_previous_quantity_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["firm_id"], ["firm.id"], name=op.f("fk_firm_points_entry_firm_id")
        ),
        sa.ForeignKeyConstraint(
            ["purchase_order_id"],
            ["purchase_order.id"],
            name=op.f("fk_firm_points_entry_purchase_order_id"),
        ),
        sa.ForeignKeyConstraint(
            ["purchase_order_line_id"],
            ["purchase_order_line.id"],
            name=op.f("fk_firm_points_entry_purchase_order_line_id"),
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"], ["resource.id"], name=op.f("fk_firm_points_entry_resource_id")
        ),
        # Composite, so an entry cannot name another firm's supplier.
        sa.ForeignKeyConstraint(
            ["supplier_id", "firm_id"],
            ["supplier.id", "supplier.firm_id"],
            name=op.f("fk_firm_points_entry_supplier_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_firm_points_entry")),
        # A line earns once, however the service is called.
        sa.UniqueConstraint(
            "purchase_order_line_id",
            name=op.f("uq_firm_points_entry_purchase_order_line_id"),
        ),
    )
    op.create_index("ix_firm_points_entry_firm_id", "firm_points_entry", ["firm_id"], unique=False)
    op.create_index(
        "ix_firm_points_entry_firm_id_supplier_id",
        "firm_points_entry",
        ["firm_id", "supplier_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_firm_points_entry_firm_id_supplier_id", table_name="firm_points_entry")
    op.drop_index("ix_firm_points_entry_firm_id", table_name="firm_points_entry")
    op.drop_table("firm_points_entry")
