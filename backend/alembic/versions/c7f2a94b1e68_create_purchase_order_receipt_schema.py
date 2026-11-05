"""create purchase order receipt schema

The two tables HU-22 writes, the ones ADR-011 section 1 left for the story that
would fill them: purchase_order_receipt and purchase_order_receipt_line.

Three things here are deliberate rather than forgotten:

- The receipt carries the delivery's freight, nullable, and the receipt line only
  what the material cost. A remito charges the freight once for the whole truck,
  so hanging it off each line would mean splitting by hand a number the supplier
  never split (ADR-011 section 8, precisado al implementar HU-22).
- purchase_order_receipt_line has neither firm_id nor is_active: it is pure
  composition of its receipt, like budget_version_item of its version, reached
  only through receipt_id and cancelled with the receipt that holds it.
- Only the receipt gets a trg_*_updated_at trigger. Its lines are never updated:
  a correction cancels the whole receipt (ADR-011 section 3).

Revision ID: c7f2a94b1e68
Revises: b9d4f6a82c35
Create Date: 2026-10-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7f2a94b1e68"
down_revision: str | Sequence[str] | None = "b9d4f6a82c35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "purchase_order_receipt",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("purchase_order_id", sa.BigInteger(), nullable=False),
        sa.Column("firm_id", sa.BigInteger(), nullable=False),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=150), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("shipping_cost", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # NULL is "the supplier charged no freight", which is not the same as a
        # zero it did charge and wrote down.
        sa.CheckConstraint(
            "shipping_cost IS NULL OR shipping_cost >= 0",
            name=op.f("ck_purchase_order_receipt_shipping_cost_not_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["account.id"], name=op.f("fk_purchase_order_receipt_created_by")
        ),
        # Composite, so a receipt cannot be written against another firm's order.
        sa.ForeignKeyConstraint(
            ["purchase_order_id", "firm_id"],
            ["purchase_order.id", "purchase_order.firm_id"],
            name=op.f("fk_purchase_order_receipt_purchase_order_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_order_receipt")),
    )
    op.create_index(
        "ix_purchase_order_receipt_purchase_order_id",
        "purchase_order_receipt",
        ["purchase_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_purchase_order_receipt_firm_id", "purchase_order_receipt", ["firm_id"], unique=False
    )

    op.create_table(
        "purchase_order_receipt_line",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("receipt_id", sa.BigInteger(), nullable=False),
        sa.Column("purchase_order_line_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("actual_cost", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.CheckConstraint(
            "quantity > 0", name=op.f("ck_purchase_order_receipt_line_quantity_positive")
        ),
        sa.CheckConstraint(
            "actual_cost >= 0",
            name=op.f("ck_purchase_order_receipt_line_actual_cost_not_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["purchase_order_receipt.id"],
            name=op.f("fk_purchase_order_receipt_line_receipt_id"),
        ),
        sa.ForeignKeyConstraint(
            ["purchase_order_line_id"],
            ["purchase_order_line.id"],
            name=op.f("fk_purchase_order_receipt_line_purchase_order_line_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_order_receipt_line")),
        # One row per line per delivery. Named by hand: the convention's own name
        # would be 64 characters and Postgres keeps 63 (see the model).
        sa.UniqueConstraint(
            "receipt_id",
            "purchase_order_line_id",
            name=op.f("uq_purchase_order_receipt_line_once"),
        ),
    )
    op.create_index(
        "ix_purchase_order_receipt_line_receipt_id",
        "purchase_order_receipt_line",
        ["receipt_id"],
        unique=False,
    )

    # Hand-written: autogenerate does not know about triggers. set_updated_at()
    # already exists (4701f7919bbb created it).
    op.execute("""
        CREATE TRIGGER trg_purchase_order_receipt_updated_at
        BEFORE UPDATE ON purchase_order_receipt
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """)


def downgrade() -> None:
    """Downgrade schema. set_updated_at() stays: it belongs to 4701f7919bbb."""
    op.execute("DROP TRIGGER trg_purchase_order_receipt_updated_at ON purchase_order_receipt;")
    op.drop_index(
        "ix_purchase_order_receipt_line_receipt_id", table_name="purchase_order_receipt_line"
    )
    op.drop_table("purchase_order_receipt_line")
    op.drop_index("ix_purchase_order_receipt_firm_id", table_name="purchase_order_receipt")
    op.drop_index(
        "ix_purchase_order_receipt_purchase_order_id", table_name="purchase_order_receipt"
    )
    op.drop_table("purchase_order_receipt")
