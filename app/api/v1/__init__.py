from fastapi import APIRouter
from app.api.v1 import auth, calendars, events, tasks, dashboard, projects, search, collaboration, automations, integrations, security

api_router = APIRouter(prefix="/api/v1")

# Include routers
api_router.include_router(auth.router)
api_router.include_router(calendars.router)
api_router.include_router(events.router)
api_router.include_router(tasks.router)
api_router.include_router(dashboard.router)
api_router.include_router(projects.router)
api_router.include_router(search.router)
api_router.include_router(collaboration.router)
api_router.include_router(automations.router)
api_router.include_router(integrations.router)
api_router.include_router(security.router)

