"""docs/der.md: the diagram is generated from the models and cannot go stale.

The hand-drawn diagram this replaces was deleted for describing a schema that
no longer existed. The first test is what stops that from happening again: a
model changed without regenerating the diagram fails here, and in CI. The second
guards the generator itself, since a table it silently skipped would leave the
first test comparing two files that agree on being incomplete.
"""

from app.db.base import Base
from scripts.generate_erd import ERD_PATH, REGENERATE_COMMAND, render, resolve_areas


def test_the_diagram_matches_the_models() -> None:
    assert (
        ERD_PATH.read_text(encoding="utf-8") == render()
    ), f"docs/der.md is out of date. Regenerate it: {REGENERATE_COMMAND}"


def test_every_table_is_drawn_in_exactly_one_area() -> None:
    drawn = [table.name for _, tables in resolve_areas() for table in tables]

    assert sorted(drawn) == sorted(Base.metadata.tables)
