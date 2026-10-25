"""create purchase order schema

The two tables HU-20 writes, out of the four of ADR-011 section 1: purchase_order
and purchase_order_line. The receipts arrive with HU-22, the story that writes
them, in a migration of their own.

Three things here are deliberate rather than forgotten:

- The status columns of an issued, cancelled or received order are created now,
  with every CHECK that ties them to the status, although HU-20 only writes
  drafts. The status is pinned by the schema from the first row, not once the
  later stories get around to it.
- purchase_order_line.firm_id is redundant with its order's, like
  supplier_price.firm_id: the composite FK stops the two from diverging.
- Both tables get a trg_*_updated_at trigger: a draft is edited one line at a
  time (modelo-datos 3.11).

Revision ID: a8c3e5f71b24
Revises: e7b2c5a93f68
Create Date: 2026-10-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8c3e5f71b24"
down_revision: str | Sequence[str] | None = "e7b2c5a93f68"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMPED_TABLES = ("purchase_order", "purchase_order_line")


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "purchase_order",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("firm_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("supplier_id", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default=sa.text("'draft'"), nullable=False
        ),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("issued_by", sa.BigInteger(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.BigInteger(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('draft', 'issued', 'partially_received', 'received', 'cancelled')",
            name=op.f("ck_purchase_order_status_valid"),
        ),
        sa.CheckConstraint("number > 0", name=op.f("ck_purchase_order_number_positive")),
        sa.CheckConstraint(
            "status <> 'draft' OR issued_at IS NULL",
            name=op.f("ck_purchase_order_draft_not_issued"),
        ),
        sa.CheckConstraint(
            "status NOT IN ('issued', 'partially_received', 'received') OR issued_at IS NOT NULL",
            name=op.f("ck_purchase_order_issued_has_date"),
        ),
        sa.CheckConstraint(
            "(issued_at IS NULL) = (issued_by IS NULL)",
            name=op.f("ck_purchase_order_issued_by_with_date"),
        ),
        sa.CheckConstraint(
            "(status = 'cancelled') = (cancelled_at IS NOT NULL)",
            name=op.f("ck_purchase_order_cancelled_has_date"),
        ),
        sa.CheckConstraint(
            "(cancelled_at IS NULL) = (cancelled_by IS NULL)",
            name=op.f("ck_purchase_order_cancelled_by_with_date"),
        ),
        sa.CheckConstraint(
            "(status = 'received') = (received_at IS NOT NULL)",
            name=op.f("ck_purchase_order_received_has_date"),
        ),
        sa.ForeignKeyConstraint(["firm_id"], ["firm.id"], name=op.f("fk_purchase_order_firm_id")),
        sa.ForeignKeyConstraint(
            ["created_by"], ["account.id"], name=op.f("fk_purchase_order_created_by")
        ),
        sa.ForeignKeyConstraint(
            ["issued_by"], ["account.id"], name=op.f("fk_purchase_order_issued_by")
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by"], ["account.id"], name=op.f("fk_purchase_order_cancelled_by")
        ),
        # Composite, against project (id, firm_id) and supplier (id, firm_id): an
        # order for another firm's work or supplier cannot be written at all.
        sa.ForeignKeyConstraint(
            ["project_id", "firm_id"],
            ["project.id", "project.firm_id"],
            name=op.f("fk_purchase_order_project_id"),
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id", "firm_id"],
            ["supplier.id", "supplier.firm_id"],
            name=op.f("fk_purchase_order_supplier_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_order")),
        sa.UniqueConstraint("firm_id", "number", name=op.f("uq_purchase_order_firm_id_number")),
        sa.UniqueConstraint("id", "firm_id", name=op.f("uq_purchase_order_id_firm_id")),
    )
    op.create_index("ix_purchase_order_firm_id", "purchase_order", ["firm_id"], unique=False)
    op.create_index("ix_purchase_order_project_id", "purchase_order", ["project_id"], unique=False)
    op.create_index(
        "ix_purchase_order_supplier_id", "purchase_order", ["supplier_id"], unique=False
    )

    op.create_table(
        "purchase_order_line",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("purchase_order_id", sa.BigInteger(), nullable=False),
        sa.Column("firm_id", sa.BigInteger(), nullable=False),
        sa.Column("resource_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("shipping_cost", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'ARS'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_purchase_order_line_quantity_positive")),
        sa.CheckConstraint(
            "unit_price >= 0", name=op.f("ck_purchase_order_line_unit_price_not_negative")
        ),
        sa.CheckConstraint(
            "shipping_cost >= 0", name=op.f("ck_purchase_order_line_shipping_cost_not_negative")
        ),
        sa.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'", name=op.f("ck_purchase_order_line_currency_iso_4217")
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"], ["resource.id"], name=op.f("fk_purchase_order_line_resource_id")
        ),
        sa.ForeignKeyConstraint(
            ["purchase_order_id", "firm_id"],
            ["purchase_order.id", "purchase_order.firm_id"],
            name=op.f("fk_purchase_order_line_purchase_order_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_order_line")),
    )
    op.create_index(
        "ix_purchase_order_line_purchase_order_id",
        "purchase_order_line",
        ["purchase_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_purchase_order_line_firm_id", "purchase_order_line", ["firm_id"], unique=False
    )
    # An order does not repeat a material. Partial, so a line removed from a draft
    # can be added again as a new one.
    op.create_index(
        "uq_purchase_order_line_resource_active",
        "purchase_order_line",
        ["purchase_order_id", "resource_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    # Hand-written: autogenerate does not know about triggers. set_updated_at()
    # already exists (4701f7919bbb created it).
    for table in TIMESTAMPED_TABLES:
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
            """)


def downgrade() -> None:
    """Downgrade schema. set_updated_at() stays: it belongs to 4701f7919bbb."""
    for table in reversed(TIMESTAMPED_TABLES):
        op.execute(f"DROP TRIGGER trg_{table}_updated_at ON {table};")

    op.drop_index("uq_purchase_order_line_resource_active", table_name="purchase_order_line")
    op.drop_index("ix_purchase_order_line_firm_id", table_name="purchase_order_line")
    op.drop_index("ix_purchase_order_line_purchase_order_id", table_name="purchase_order_line")
    op.drop_table("purchase_order_line")
    op.drop_index("ix_purchase_order_supplier_id", table_name="purchase_order")
    op.drop_index("ix_purchase_order_project_id", table_name="purchase_order")
    op.drop_index("ix_purchase_order_firm_id", table_name="purchase_order")
    op.drop_table("purchase_order")
