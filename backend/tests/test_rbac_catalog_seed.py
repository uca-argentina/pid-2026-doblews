"""The seeded catalogue, checked against ADR-002 section 7 and ADR-003 section 8.

The expected matrix is typed out here by hand rather than imported from the seed
migrations. That duplication is the test: a check that reads the same source as
the code under test only proves the source equals itself. Here, a wrong row in
the seed shows up as a diff against the documents the team agreed on.
"""

from sqlalchemy import Connection, text

# (role code, scope) -> permission codes it grants. The catalogue.* and
# project.recipe.*/project.cost.* rows come from ADR-003 section 8; everything
# else from ADR-002 section 7.
EXPECTED: dict[tuple[str, str], set[str]] = {
    ("support", "platform"): {
        "firm.create",
        "firm.view",
        "firm.edit",
        "firm.suspend",
        "account.create",
        "account.view",
        "account.edit",
        "account.deactivate",
        "account.reset_password",
    },
    ("owner", "firm"): {
        "firm.view",
        "firm.edit",
        "member.view",
        "member.add",
        "member.edit_role",
        "member.remove",
        "project.create",
        "project.view_all",
        "catalog.view",
    },
    ("architect", "firm"): {"firm.view", "member.view", "project.create", "catalog.view"},
    ("client", "firm"): {"firm.view", "catalog.view"},
    ("lead", "project"): {
        "project.view",
        "project.edit",
        "project.archive",
        "project.member.view",
        "project.member.manage",
        "project.recipe.view",
        "project.recipe.manage",
        "project.cost.view",
    },
    ("collaborator", "project"): {
        "project.view",
        "project.edit",
        "project.member.view",
        "project.recipe.view",
        "project.recipe.manage",
        "project.cost.view",
    },
    ("viewer", "project"): {
        "project.view",
        "project.member.view",
        "project.recipe.view",
        "project.cost.view",
    },
    # No project.cost.view: the client sees how much material their work takes,
    # never what it costs the studio (ADR-003 section 8).
    ("client", "project"): {"project.view", "project.recipe.view"},
}

GRANTS = text("""
    SELECT r.code AS role_code, r.scope AS scope, p.code AS permission_code
      FROM role r
      JOIN role_permission rp ON rp.role_id = r.id
      JOIN permission p ON p.id = rp.permission_id
    """)


def _granted(db: Connection) -> dict[tuple[str, str], set[str]]:
    granted: dict[tuple[str, str], set[str]] = {}
    for row in db.execute(GRANTS):
        granted.setdefault((row.role_code, row.scope), set()).add(row.permission_code)
    return granted


def test_every_role_grants_exactly_the_documented_permissions(db: Connection) -> None:
    assert _granted(db) == EXPECTED


def test_the_catalogue_holds_exactly_the_documented_roles(db: Connection) -> None:
    roles = {(row.code, row.scope) for row in db.execute(text("SELECT code, scope FROM role"))}
    assert roles == set(EXPECTED)


def test_no_permission_exists_that_no_role_grants(db: Connection) -> None:
    """An unreachable permission is either a typo or a capability nobody can use."""
    orphans = db.execute(
        text(
            "SELECT p.code, p.scope FROM permission p"
            " WHERE NOT EXISTS (SELECT 1 FROM role_permission rp WHERE rp.permission_id = p.id)"
        )
    ).all()
    assert orphans == []


def test_support_has_no_content_permissions(db: Connection) -> None:
    """ADR-002 section 7 is explicit: support administers accounts, not content.

    Stated as its own test because it is the rule most likely to be eroded by a
    well-meaning "support needs to see a project to debug this" pull request.
    The right answer to that request is logged impersonation, not a new row.
    """
    granted = _granted(db)[("support", "platform")]
    assert not any(code.startswith("project.") for code in granted)


def test_the_project_client_does_not_see_costs(db: Connection) -> None:
    """ADR-003 section 8, and the reason viewer and client exist as two roles.

    Back in ADR-002 they granted the same thing, and were seeded apart anyway on
    the bet that the difference would show up once money entered the model. This
    is that bet paying off: the client sees how much material their work takes
    and never what it costs the studio. "Un cliente no es 've menos': ve otra
    cosa."

    Its own test rather than a line in the matrix above, because it is the rule a
    well-meaning "the client asked why it is so expensive" pull request erodes.
    """
    granted = _granted(db)

    assert "project.recipe.view" in granted[("client", "project")]
    assert "project.cost.view" not in granted[("client", "project")]
    assert "project.cost.view" in granted[("viewer", "project")]
