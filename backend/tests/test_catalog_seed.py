"""The seeded system catalogue, and the take-off query it exists to make possible.

The expected content is typed out here by hand rather than imported from the seed
migration, for the same reason as test_rbac_catalog_seed.py: a check that reads
the same source as the code under test only proves the source equals itself.

The last test is the one that matters most. T-04 is not done because four tables
exist — it is done when HU-5 has something to compute, so the take-off query of
ADR-003 section 2 is run here against the real seed and asked for the number that
ADR's Consequences section promises out loud.
"""

from decimal import Decimal

from sqlalchemy import Connection, text

# resource name -> (type, unit code). The seven materials are T-04's; labour and
# equipment are T-06's, always in hours (ADR-003 section 3, precised by T-05).
EXPECTED_RESOURCES: dict[str, tuple[str, str]] = {
    "Ladrillo común": ("material", "u"),
    "Cemento portland (bolsa 50 kg)": ("material", "bolsa"),
    "Cal hidratada (bolsa 25 kg)": ("material", "bolsa"),
    "Arena gruesa": ("material", "m3"),
    "Arena fina": ("material", "m3"),
    "Cascote": ("material", "m3"),
    "Hidrófugo": ("material", "kg"),
    "Oficial": ("labor", "h"),
    "Ayudante": ("labor", "h"),
    "Hormigonera": ("equipment", "h"),
}

# recipe name -> unit code. Three curated recipes, as T-04 asks: better few done
# properly than many done halfway.
EXPECTED_RECIPES: dict[str, str] = {
    "Pared de ladrillo común 15cm": "m2",
    "Contrapiso de cascote": "m2",
    "Carpeta de cemento": "m2",
}

WALL = "Pared de ladrillo común 15cm"

# The worked example of ADR-003: what 120 m2 of that wall takes. Section 2 states
# the yields it comes from, and the Consequences section states the result —
# "esta obra necesita 7.200 ladrillos y 30 bolsas de cemento". T-06 adds the
# hours: 1 h/m2 of each trade, and no mixer, since the wall's mortar is hand-mixed.
WALL_OF_120_M2: dict[str, Decimal] = {
    "Ladrillo común": Decimal("7200.0000"),
    "Cemento portland (bolsa 50 kg)": Decimal("30.0000"),
    "Cal hidratada (bolsa 25 kg)": Decimal("24.0000"),
    "Arena gruesa": Decimal("5.6400"),
    "Oficial": Decimal("120.0000"),
    "Ayudante": Decimal("120.0000"),
}

# ADR-003 section 2, verbatim. Run here against seeded data rather than
# paraphrased, so that the thing being proved is the query the product will use.
TAKE_OFF = """
    SELECT r.name,
           SUM(pr.quantity * rr.quantity_per_unit)                     AS quantity,
           SUM(pr.quantity * rr.quantity_per_unit * r.reference_price) AS cost
      FROM project_recipe pr
      JOIN recipe_resource rr ON rr.recipe_id = pr.recipe_id
      JOIN resource r         ON r.id = rr.resource_id
     WHERE pr.project_id = :project AND pr.is_active
     GROUP BY r.id, r.name
"""


def test_the_catalogue_holds_exactly_the_seeded_resources(db: Connection) -> None:
    rows = db.execute(
        text(
            "SELECT r.name, u.code, r.type FROM resource r"
            " JOIN unit_of_measure u ON u.id = r.unit_of_measure_id"
        )
    ).all()

    assert {row.name: (row.type, row.code) for row in rows} == EXPECTED_RESOURCES


def test_every_seeded_recipe_takes_hours_of_both_trades(db: Connection) -> None:
    """T-06: the three recipes carry labour, so HU-11 has a labour section to show
    for whatever a work is made of, not only for walls."""
    rows = db.execute(
        text(
            "SELECT rc.name, count(*) AS trades FROM recipe rc"
            " JOIN recipe_resource rr ON rr.recipe_id = rc.id"
            " JOIN resource rs ON rs.id = rr.resource_id"
            " WHERE rs.type = 'labor' GROUP BY rc.name"
        )
    ).all()

    assert {row.name: row.trades for row in rows} == {name: 2 for name in EXPECTED_RECIPES}


def test_every_seeded_resource_has_a_price_and_a_date_for_it(db: Connection) -> None:
    """price_updated_at is what HU-5 shows as "precios de referencia al <fecha>".

    A seeded price with no date would make that label impossible to render on the
    very first screen anyone opens.
    """
    unpriced = db.execute(
        text("SELECT count(*) FROM resource WHERE reference_price <= 0 OR price_updated_at IS NULL")
    ).scalar_one()
    assert unpriced == 0


def test_the_catalogue_holds_exactly_the_seeded_recipes(db: Connection) -> None:
    rows = db.execute(
        text(
            "SELECT r.name, u.code FROM recipe r"
            " JOIN unit_of_measure u ON u.id = r.unit_of_measure_id"
        )
    ).all()

    assert {row.name: row.code for row in rows} == EXPECTED_RECIPES


def test_no_seeded_recipe_is_empty(db: Connection) -> None:
    """An active recipe with no lines computes zero materials silently.

    HU-8 states it as an acceptance criterion for what the screen must refuse to
    save; nothing in the schema enforces it, so the seed has to be checked.
    """
    empty = db.execute(
        text(
            "SELECT r.name FROM recipe r"
            " LEFT JOIN recipe_resource rr ON rr.recipe_id = r.id"
            " WHERE r.is_active GROUP BY r.id, r.name HAVING count(rr.resource_id) = 0"
        )
    ).all()

    assert [row.name for row in empty] == []


def test_a_seeded_recipe_states_the_assumption_behind_its_numbers(db: Connection) -> None:
    """Every per-m2 recipe declares its thickness somewhere a reader can find it.

    "0,3 bolsas de cemento por m2 de contrapiso" is unusable without knowing the
    contrapiso is 10cm thick, and the description is where that lives.
    """
    described = db.execute(
        text("SELECT count(*) FROM recipe WHERE description IS NOT NULL AND description <> ''")
    ).scalar_one()
    assert described == len(EXPECTED_RECIPES)


def test_the_take_off_of_a_seeded_recipe_gives_the_number_adr_003_promises(
    db: Connection, world
) -> None:
    """The whole point of T-04, end to end: catalogue in, take-off out.

    Nothing in this test is specific to a firm — the catalogue is global — but the
    take-off line is, so it is inserted against firm A's own project.
    """
    db.execute(
        text(
            "INSERT INTO project_recipe (project_id, firm_id, recipe_id, quantity)"
            " VALUES (:project, :firm, (SELECT id FROM recipe WHERE name = :recipe), 120)"
        ),
        {"project": world.project_a, "firm": world.firm_a, "recipe": WALL},
    )

    rows = db.execute(text(TAKE_OFF), {"project": world.project_a}).all()

    assert {row.name: row.quantity for row in rows} == WALL_OF_120_M2


def test_two_lines_of_the_same_recipe_add_up(db: Connection, world) -> None:
    """Measuring by sector is normal, which is why there is no UNIQUE on the pair.

    ADR-003 section 5 rejects UNIQUE (project_id, recipe_id) precisely so that a
    wall can be measured per storey; the take-off has to aggregate them back.
    """
    for note, quantity in (("Planta baja", 70), ("Planta alta", 50)):
        db.execute(
            text(
                "INSERT INTO project_recipe (project_id, firm_id, recipe_id, quantity, note)"
                " VALUES (:project, :firm, (SELECT id FROM recipe WHERE name = :recipe),"
                "         :quantity, :note)"
            ),
            {
                "project": world.project_a,
                "firm": world.firm_a,
                "recipe": WALL,
                "quantity": quantity,
                "note": note,
            },
        )

    rows = db.execute(text(TAKE_OFF), {"project": world.project_a}).all()

    # 70 + 50 is the same 120 m2 as the test above, so it owes the same materials.
    assert {row.name: row.quantity for row in rows} == WALL_OF_120_M2


def test_a_deactivated_take_off_line_stops_counting(db: Connection, world) -> None:
    """Logical deletion has to reach the take-off, or a removed line keeps costing."""
    db.execute(
        text(
            "INSERT INTO project_recipe (project_id, firm_id, recipe_id, quantity, is_active)"
            " VALUES (:project, :firm, (SELECT id FROM recipe WHERE name = :recipe), 120, false)"
        ),
        {"project": world.project_a, "firm": world.firm_a, "recipe": WALL},
    )

    rows = db.execute(text(TAKE_OFF), {"project": world.project_a}).all()

    assert rows == []
