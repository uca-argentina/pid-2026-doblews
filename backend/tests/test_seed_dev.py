"""Pins the demo seed (T-09): that the demo work opens every sprint 3 screen with
something to show, and that running the seed again writes nothing.

The numbers are read through the endpoints the screens read, so what is pinned
is what the defence will see. Today is frozen on Thursday 15/10/2026; the seed
dates the work around it.
"""

from datetime import date

import pytest
from sqlalchemy import func, select

from app.db.seed_dev import seed
from app.models import Account, BudgetVersion, Firm, Project, ProjectTask, Supplier

TODAY = date(2026, 10, 15)


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch) -> None:
    monkeypatch.setattr("app.db.seed_dev.today", lambda: TODAY)
    monkeypatch.setattr("app.services.tasks.today", lambda: TODAY)
    monkeypatch.setattr("app.api.routes.dashboard.today", lambda: TODAY)


@pytest.fixture
def seeded(db_session):
    seed(db_session, "demo-password")
    db_session.flush()
    firm = db_session.scalar(select(Firm.id).where(Firm.name == "Estudio Norte"))
    work = db_session.scalar(select(Project.id).where(Project.name == "Casa Rodríguez"))
    lead = db_session.scalar(select(Account.id).where(Account.email == "alba@estudionorte.test"))
    return f"/firms/{firm}/projects/{work}", lead


def test_the_planning_shows_every_status_and_a_late_task(seeded, client, auth_header):
    base, lead = seeded
    planning = client.get(f"{base}/tasks", headers=auth_header(lead)).json()

    statuses = {task["name"]: task["status"] for task in planning["tasks"]}
    assert len(statuses) == 6
    assert set(statuses.values()) == {"pending", "in_progress", "paused", "finished"}
    assert planning["baseline_set_on"] == planning["project_start_date"]

    late = [
        task["name"]
        for task in planning["tasks"]
        if task["status"] != "finished" and task["baseline_end_date"] < TODAY.isoformat()
    ]
    assert late == ["Mampostería planta baja"]
    assert planning["progress"]["actual_percent"] < planning["progress"]["planned_percent"]


def test_the_dashboard_has_all_three_blocks(seeded, client, auth_header):
    base, lead = seeded
    dashboard = client.get(f"{base}/dashboard", headers=auth_header(lead)).json()

    assert dashboard["budget"]["direction"] == "above"
    assert dashboard["progress"]["overdue_tasks"] == 1
    assert dashboard["progress"]["end_delay_days"] > 0
    assert len(dashboard["projection"]["months"]) >= 3


def test_seeding_again_writes_nothing(seeded, db_session):
    def counts() -> tuple[int, ...]:
        return tuple(
            db_session.scalar(select(func.count()).select_from(model))
            for model in (Project, ProjectTask, BudgetVersion, Supplier, Account)
        )

    before = counts()
    seed(db_session, "demo-password")
    db_session.flush()
    assert counts() == before
