"""One router to mount, so main.py does not grow a line per feature."""

from fastapi import APIRouter

from app.api.routes import (
    auth,
    budget,
    budget_versions,
    catalog,
    catalog_admin,
    firms,
    members,
    platform,
    project_members,
    projects,
    takeoff,
    tasks,
    units_of_measure,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(budget.router)
api_router.include_router(budget_versions.router)
api_router.include_router(catalog.router)
api_router.include_router(catalog_admin.router)
api_router.include_router(firms.router)
api_router.include_router(members.router)
api_router.include_router(platform.router)
api_router.include_router(project_members.router)
api_router.include_router(projects.router)
api_router.include_router(takeoff.router)
api_router.include_router(tasks.router)
api_router.include_router(units_of_measure.router)
