"""One router to mount, so main.py does not grow a line per feature."""

from fastapi import APIRouter

from app.api.routes import auth, firms, members, projects, units_of_measure

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(firms.router)
api_router.include_router(members.router)
api_router.include_router(projects.router)
api_router.include_router(units_of_measure.router)
