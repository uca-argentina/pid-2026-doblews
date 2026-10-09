"""Pins what a work's planning reads back: which tasks, in what order, and who
answers for each. What a task costs is the take-off repository's and is tested
there; the rules for changing one are the service's.
"""

from datetime import date

from app.repositories.project_task import ProjectTaskRepository


def repo(db_session, firm_id: int) -> ProjectTaskRepository:
    return ProjectTaskRepository(db_session, firm_id=firm_id)


class TestTasks:
    def test_a_task_comes_back_as_it_was_loaded(self, db_session, world, add_task):
        task_id = add_task(
            world.project_a,
            world.firm_a,
            "Mampostería",
            duration=10,
            status="finished",
            actual_start="2026-10-01",
            actual_end="2026-10-14",
        )

        (task,) = repo(db_session, world.firm_a).tasks(world.project_a)

        assert (task.id, task.name, task.estimated_duration_days) == (task_id, "Mampostería", 10)
        assert task.status == "finished"
        assert (task.actual_start_date, task.actual_end_date) == (
            date(2026, 10, 1),
            date(2026, 10, 14),
        )
        assert task.description is None
        assert task.not_before_date is None

    def test_a_task_carries_its_assignee_by_name(self, db_session, world, add_task):
        add_task(world.project_a, world.firm_a, assignee=world.account_a2)

        (task,) = repo(db_session, world.firm_a).tasks(world.project_a)

        assert (task.assignee.account_id, task.assignee.name) == (world.account_a2, "alba")

    def test_a_task_without_assignee_is_still_listed(self, db_session, world, add_task):
        add_task(world.project_a, world.firm_a)

        (task,) = repo(db_session, world.firm_a).tasks(world.project_a)

        assert task.assignee is None

    def test_tasks_come_in_the_order_they_were_loaded(self, db_session, world, add_task):
        """By id and not by name, so renaming one does not move it."""
        add_task(world.project_a, world.firm_a, "Techos")
        add_task(world.project_a, world.firm_a, "Cimientos")

        tasks = repo(db_session, world.firm_a).tasks(world.project_a)

        assert [task.name for task in tasks] == ["Techos", "Cimientos"]

    def test_a_removed_task_is_not_listed(self, db_session, world, add_task):
        add_task(world.project_a, world.firm_a, is_active=False)

        assert repo(db_session, world.firm_a).tasks(world.project_a) == []

    def test_a_work_with_no_tasks_is_an_empty_list(self, db_session, world):
        assert repo(db_session, world.firm_a).tasks(world.project_a) == []


class TestOneTask:
    def test_a_task_of_this_work_is_found(self, db_session, world, add_task):
        task_id = add_task(world.project_a, world.firm_a, "Mampostería")

        repository = repo(db_session, world.firm_a)

        assert repository.task(world.project_a, task_id).id == task_id
        assert repository.entry(world.project_a, task_id).name == "Mampostería"

    def test_a_removed_task_is_not_found(self, db_session, world, add_task):
        task_id = add_task(world.project_a, world.firm_a, is_active=False)

        repository = repo(db_session, world.firm_a)

        assert repository.task(world.project_a, task_id) is None
        assert repository.entry(world.project_a, task_id) is None

    def test_a_task_of_another_work_of_the_same_firm_is_not_found(
        self, db_session, world, add_task, new_project
    ):
        """The firm filter alone would let this through: the URL names work A,
        the task belongs to work B, and both are firm A's."""
        other = new_project(world.firm_a, world.account_a, "Casa Otra")
        task_id = add_task(other, world.firm_a)

        repository = repo(db_session, world.firm_a)

        assert repository.task(world.project_a, task_id) is None
        assert repository.entry(world.project_a, task_id) is None


class TestNameTaken:
    def test_a_live_task_takes_its_name_whatever_the_case(self, db_session, world, add_task):
        add_task(world.project_a, world.firm_a, "Mampostería")

        repository = repo(db_session, world.firm_a)

        assert repository.name_taken(world.project_a, "MAMPOSTERÍA") is True
        assert repository.name_taken(world.project_a, "Pintura") is False

    def test_a_removed_task_does_not_take_its_name(self, db_session, world, add_task):
        add_task(world.project_a, world.firm_a, "Mampostería", is_active=False)

        assert repo(db_session, world.firm_a).name_taken(world.project_a, "Mampostería") is False

    def test_a_task_does_not_collide_with_itself(self, db_session, world, add_task):
        """Saving the edit form without touching the name must not be refused."""
        task_id = add_task(world.project_a, world.firm_a, "Mampostería")

        repository = repo(db_session, world.firm_a)

        assert repository.name_taken(world.project_a, "Mampostería", exclude_id=task_id) is False

    def test_the_name_is_taken_per_work(self, db_session, world, add_task, new_project):
        other = new_project(world.firm_a, world.account_a, "Casa Otra")
        add_task(other, world.firm_a, "Mampostería")

        assert repo(db_session, world.firm_a).name_taken(world.project_a, "Mampostería") is False


class TestIsolation:
    def test_another_firm_reads_no_tasks(self, db_session, world, add_task):
        """Even naming firm B's project and task outright, firm A's repository
        finds nothing: the tenant filter is on every read, not on the URL."""
        task_of_b = add_task(world.project_b, world.firm_b, "Mampostería")

        repository = repo(db_session, world.firm_a)

        assert repository.tasks(world.project_b) == []
        assert repository.task(world.project_b, task_of_b) is None
        assert repository.entry(world.project_b, task_of_b) is None
        assert repository.name_taken(world.project_b, "Mampostería") is False
