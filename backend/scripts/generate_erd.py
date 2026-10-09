"""Generate docs/der.md, the entity-relationship diagram, from the models.

The diagram is derived and never written by hand: the previous hand-drawn one
(docs/diagrams/der.mmd) was deleted for describing a schema that no longer
existed. This reads Base.metadata, which `alembic check` already keeps equal to
the migrations, so the diagram cannot drift from the database either.

    uv run python -m scripts.generate_erd            # rewrite docs/der.md
    uv run python -m scripts.generate_erd --check    # fail if it is out of date

It needs no database: the metadata is enough. The output is deterministic (no
timestamp, everything sorted) because CI compares it byte for byte.
"""

import argparse
import difflib
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKeyConstraint,
    Index,
    Numeric,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.db.base import Base

ERD_PATH = Path(__file__).resolve().parents[2] / "docs" / "der.md"

DIALECT = postgresql.dialect()

REGENERATE_COMMAND = "cd backend && uv run python -m scripts.generate_erd"


@dataclass(frozen=True)
class Area:
    """A group of tables drawn together, and the ADRs that explain them."""

    title: str
    # Model modules under app.models: a table belongs to the area of the module
    # that declares it, so a new table in an existing module needs no change here.
    modules: tuple[str, ...]
    defined_in: str


AREAS = (
    Area(
        "Identidad y autorización",
        ("account", "firm", "membership", "role"),
        "[ADR-002](adr/0002-authorization-model.md), [ADR-004](adr/0004-authentication.md)",
    ),
    Area(
        "Catálogo",
        ("unit_of_measure", "catalog"),
        "[ADR-003](adr/0003-recipe-catalog.md), [ADR-005](adr/0005-catalog-administration.md), "
        "[ADR-006](adr/0006-firm-recipes.md)",
    ),
    Area(
        "Obra y cómputo",
        ("project", "project_recipe"),
        "[ADR-002](adr/0002-authorization-model.md) §3-§5, [ADR-003](adr/0003-recipe-catalog.md)",
    ),
    Area(
        "Planificación",
        ("project_task",),
        "[ADR-009](adr/0009-project-planning.md)",
    ),
    Area(
        "Versiones del presupuesto",
        ("budget_version",),
        "[ADR-007](adr/0007-budget-versions.md)",
    ),
)


def tables_by_module() -> dict[str, list[Table]]:
    """Every table, keyed by the app.models module that declares it."""
    grouped: dict[str, list[Table]] = {}
    for mapper in Base.registry.mappers:
        module = mapper.class_.__module__.rsplit(".", 1)[-1]
        grouped.setdefault(module, []).append(mapper.local_table)
    for tables in grouped.values():
        tables.sort(key=lambda table: table.name)
    return grouped


def resolve_areas() -> list[tuple[Area, list[Table]]]:
    """Pair each area with its tables.

    A module no area claims gets an area of its own, named after it, rather than
    being dropped: a table missing from the diagram is the failure this script
    exists to prevent.
    """
    grouped = tables_by_module()
    resolved = []
    for area in AREAS:
        tables = [table for module in area.modules for table in grouped.pop(module, [])]
        resolved.append((area, sorted(tables, key=lambda table: table.name)))
    for module in sorted(grouped):
        resolved.append((Area(module, (module,), "sin ADR asignada"), grouped[module]))
    return resolved


def unique_column_sets(table: Table) -> list[frozenset[str]]:
    """Column sets the table guarantees unique as a whole, the primary key included.

    Partial and functional unique indexes are left out: they do not make the
    plain columns unique across every row.
    """
    sets = [frozenset(column.name for column in table.primary_key.columns)]
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint):
            sets.append(frozenset(column.name for column in constraint.columns))
    for index in table.indexes:
        if index.unique and not index_where(index) and len(index.columns) == len(index.expressions):
            sets.append(frozenset(column.name for column in index.columns))
    return sets


def index_where(index: Index) -> str:
    where = index.dialect_options["postgresql"]["where"]
    return str(where) if where is not None else ""


def column_type(column: Column) -> tuple[str, str]:
    """The Mermaid type token, and whatever of the type the token cannot hold.

    Mermaid rejects a comma inside an attribute type, so NUMERIC's precision and
    scale move to the comment.
    """
    if isinstance(column.type, Numeric):
        return "numeric", f"{column.type.precision},{column.type.scale}"
    compiled = column.type.compile(dialect=DIALECT).lower()
    return compiled.replace("timestamp with time zone", "timestamptz"), ""


def column_line(table: Table, column: Column) -> str:
    type_token, comment = column_type(column)
    keys = []
    if column.primary_key:
        keys.append("PK")
    if column.foreign_keys:
        keys.append("FK")
    if not column.primary_key and frozenset({column.name}) in unique_column_sets(table):
        keys.append("UK")
    notes = [note for note in (comment, "" if not column.nullable else "NULL") if note]
    parts = [type_token, column.name]
    if keys:
        parts.append(", ".join(keys))
    if notes:
        parts.append(f'"{" · ".join(notes)}"')
    return "        " + " ".join(parts)


def entity_block(table: Table) -> list[str]:
    lines = [f"    {table.name} {{"]
    lines += [column_line(table, column) for column in table.columns]
    lines.append("    }")
    return lines


def foreign_keys(table: Table) -> list[ForeignKeyConstraint]:
    return sorted(
        table.foreign_key_constraints, key=lambda fk: (fk.referred_table.name, fk.column_keys)
    )


def relationship_line(table: Table, fk: ForeignKeyConstraint) -> str:
    """One line per constraint, so a composite foreign key reads as one relation."""
    columns = list(fk.column_keys)
    optional = any(table.columns[name].nullable for name in columns)
    one_to_one = frozenset(columns) in unique_column_sets(table)
    parent_side = "|o" if optional else "||"
    child_side = "o|" if one_to_one else "o{"
    label = ", ".join(columns)
    return f'    {fk.referred_table.name} {parent_side}--{child_side} {table.name} : "{label}"'


def diagram(tables: list[Table]) -> list[str]:
    """A Mermaid erDiagram of these tables and the foreign keys they declare.

    A table they point at but that is not in the list shows up as an empty box,
    which is how an area diagram marks where it touches another area.
    """
    lines = ["```mermaid", "erDiagram"]
    for table in tables:
        lines += entity_block(table)
    lines.append("")
    for table in tables:
        lines += [relationship_line(table, fk) for fk in foreign_keys(table)]
    lines.append("```")
    return lines


def code(sql: str) -> str:
    """Inline code safe inside a Markdown table cell."""
    return "`" + " ".join(sql.split()).replace("|", "\\|") + "`"


def index_definition(index: Index) -> str:
    expressions = [
        expression.name if isinstance(expression, Column) else str(expression)
        for expression in index.expressions
    ]
    definition = f"({', '.join(expressions)})"
    where = index_where(index)
    return f"{definition} WHERE {where}" if where else definition


def rule_rows(table: Table) -> list[tuple[str, str]]:
    """What the schema enforces and a diagram cannot draw: (kind, definition)."""
    rows = []
    for constraint in table.constraints:
        if isinstance(constraint, CheckConstraint):
            rows.append(("CHECK", str(constraint.sqltext)))
        elif isinstance(constraint, UniqueConstraint):
            rows.append(("UNIQUE", f"({', '.join(column.name for column in constraint.columns)})"))
    for index in table.indexes:
        if index.unique:
            kind = "UNIQUE parcial" if index_where(index) else "UNIQUE"
            rows.append((kind, index_definition(index)))
    for fk in foreign_keys(table):
        referred = ", ".join(element.column.name for element in fk.elements)
        target = f"{fk.referred_table.name} ({referred})"
        if len(fk.column_keys) > 1:
            rows.append(("FK compuesta", f"({', '.join(fk.column_keys)}) → {target}"))
        if fk.ondelete:
            rows.append((f"ON DELETE {fk.ondelete}", f"({', '.join(fk.column_keys)}) → {target}"))
    return sorted(rows)


def rules_table(tables: list[Table]) -> list[str]:
    lines = ["| Tabla | Regla | Definición |", "|---|---|---|"]
    for table in tables:
        lines += [f"| `{table.name}` | {kind} | {code(sql)} |" for kind, sql in rule_rows(table)]
    return lines


def render() -> str:
    areas = resolve_areas()
    every_table = sorted((table for _, tables in areas for table in tables), key=lambda t: t.name)

    lines = [
        "# Diagrama entidad-relación",
        "",
        "> **Archivo generado: no editar a mano.** Sale de los modelos de SQLAlchemy",
        "> (`backend/app/models/`). Al cambiar un modelo se regenera con:",
        ">",
        "> ```bash",
        f"> {REGENERATE_COMMAND}",
        "> ```",
        ">",
        "> El CI falla si este archivo no coincide con los modelos.",
        "",
        f"Es el estado **actual** del esquema: {len(every_table)} tablas. Lo que todavía se está",
        "diseñando no aparece acá sino en la ADR que lo propone. El porqué de cada tabla está en",
        "las ADR que cita cada área, y las convenciones en",
        "[modelo-datos-sprint-1.md](modelo-datos-sprint-1.md).",
        "",
        "## Cómo leerlo",
        "",
        "- `PK`, `FK`, `UK`: clave primaria, clave foránea, columna única por sí sola.",
        '- `"NULL"`: la columna admite nulos. Sin esa marca es `NOT NULL`.',
        '- `numeric "14,2"`: precisión y escala (Mermaid no admite la coma dentro del tipo).',
        "- Cada línea es una clave foránea, etiquetada con las columnas que la forman en la",
        "  tabla hija. Una clave foránea compuesta es una sola línea.",
        "- `||--o{` uno a muchos · `|o--o{` la clave foránea admite nulos · `||--o|` uno a uno.",
        "- Las tablas de reglas listan lo que el esquema garantiza y el dibujo no muestra:",
        "  `CHECK`, unicidad compuesta o parcial, claves foráneas compuestas y `ON DELETE`.",
        "",
        "## Modelo completo",
        "",
        *diagram(every_table),
    ]
    for area, tables in areas:
        lines += [
            "",
            f"## {area.title}",
            "",
            f"Definida en: {area.defined_in}.",
            "",
            *diagram(tables),
            "",
            *rules_table(tables),
        ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if docs/der.md differs from the models",
    )
    args = parser.parse_args()

    expected = render()
    if not args.check:
        ERD_PATH.write_text(expected, encoding="utf-8")
        print(f"Wrote {ERD_PATH}")
        return 0

    current = ERD_PATH.read_text(encoding="utf-8") if ERD_PATH.exists() else ""
    if current == expected:
        return 0
    sys.stderr.writelines(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            expected.splitlines(keepends=True),
            "docs/der.md",
            "generated from the models",
        )
    )
    sys.stderr.write(f"\ndocs/der.md is out of date. Regenerate it: {REGENERATE_COMMAND}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
