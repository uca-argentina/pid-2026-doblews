"""create supplier schema

The two tables of ADR-010 section 2, which HU-17 loads a firm's suppliers and
their price lists into: supplier (a supplier of one firm) and supplier_price (one
row of its list: this material, this price, this shipping cost).

Three things here are deliberate rather than forgotten:

- Both tables get a trg_*_updated_at trigger, unlike the three of ADR-007: they
  are edited one row at a time and carry is_active and updated_at like any other
  entity (modelo-datos 3.11).
- supplier_price.firm_id is redundant with its supplier's, on purpose. The
  composite FK (supplier_id, firm_id) -> supplier (id, firm_id) is what stops the
  two from ever diverging, and having the column is what lets the base repository
  filter it by firm like any other table (modelo-datos 3.2).
- supplier_price.resource_id is a plain FK to resource. That the resource is a
  material and not labour or equipment is NOT in the schema: ADR-010 section 7
  puts it in the service, with its test, and its alternatives explain why the
  (resource_id, resource_type) pattern of modelo-datos 3.8 was not worth it here.

Revision ID: d6a1f4b82e57
Revises: f5b2d8c41a96
Create Date: 2026-10-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6a1f4b82e57"
down_revision: str | Sequence[str] | None = "f5b2d8c41a96"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMPED_TABLES = ("supplier", "supplier_price")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "supplier",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("firm_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("contact_name", sa.String(length=120), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
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
        sa.ForeignKeyConstraint(["firm_id"], ["firm.id"], name=op.f("fk_supplier_firm_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier")),
        sa.UniqueConstraint("id", "firm_id", name=op.f("uq_supplier_id_firm_id")),
    )
    op.create_index("ix_supplier_firm_id", "supplier", ["firm_id"], unique=False)
    # Autogenerate does not emit functional or partial indexes faithfully, so this
    # one is written by hand. Unique on lower(name) among the firm's active
    # suppliers (modelo-datos 3.4).
    op.create_index(
        "uq_supplier_name_active",
        "supplier",
        ["firm_id", sa.literal_column("lower(name)")],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "supplier_price",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("supplier_id", sa.BigInteger(), nullable=False),
        sa.Column("firm_id", sa.BigInteger(), nullable=False),
        sa.Column("resource_id", sa.BigInteger(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("shipping_cost", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'ARS'"), nullable=False),
        sa.Column(
            "price_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "unit_price >= 0", name=op.f("ck_supplier_price_unit_price_not_negative")
        ),
        sa.CheckConstraint(
            "shipping_cost >= 0", name=op.f("ck_supplier_price_shipping_cost_not_negative")
        ),
        sa.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'", name=op.f("ck_supplier_price_currency_iso_4217")
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"], ["resource.id"], name=op.f("fk_supplier_price_resource_id")
        ),
        # Composite, against supplier (id, firm_id): a price of another firm's
        # supplier cannot be written, not merely refused.
        sa.ForeignKeyConstraint(
            ["supplier_id", "firm_id"],
            ["supplier.id", "supplier.firm_id"],
            name=op.f("fk_supplier_price_supplier_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier_price")),
    )
    op.create_index("ix_supplier_price_firm_id", "supplier_price", ["firm_id"], unique=False)
    op.create_index(
        "ix_supplier_price_resource_id", "supplier_price", ["resource_id"], unique=False
    )
    # A supplier does not repeat a material in its list. Partial, so a row removed
    # by mistake is loaded again as a new one.
    op.create_index(
        "uq_supplier_price_resource_active",
        "supplier_price",
        ["supplier_id", "resource_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    # Hand-written: autogenerate compares tables and columns, it does not know
    # about triggers. set_updated_at() already exists (4701f7919bbb created it),
    # so only the triggers are new here.
    for table in TIMESTAMPED_TABLES:
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
            """)


def downgrade() -> None:
    """Downgrade schema.

    The function itself is not dropped: it belongs to 4701f7919bbb, and every
    other timestamped table still depends on it.
    """
    for table in reversed(TIMESTAMPED_TABLES):
        op.execute(f"DROP TRIGGER trg_{table}_updated_at ON {table};")

    op.drop_index("uq_supplier_price_resource_active", table_name="supplier_price")
    op.drop_index("ix_supplier_price_resource_id", table_name="supplier_price")
    op.drop_index("ix_supplier_price_firm_id", table_name="supplier_price")
    op.drop_table("supplier_price")
    op.drop_index("uq_supplier_name_active", table_name="supplier")
    op.drop_index("ix_supplier_firm_id", table_name="supplier")
    op.drop_table("supplier")
