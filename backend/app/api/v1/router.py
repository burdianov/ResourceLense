from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.departments import router as departments_router
from app.api.v1.endpoints.designations import router as designations_router
from app.api.v1.endpoints.employees import router as employees_router
from app.api.v1.endpoints.misc_master import (
    categories_router,
    providers_router,
    trades_router,
)
from app.api.v1.endpoints.permissions import router as permissions_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.rates import router as rates_router
from app.api.v1.endpoints.roles import router as roles_router
from app.api.v1.endpoints.users import router as users_router


api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(permissions_router)
api_router.include_router(projects_router)
api_router.include_router(departments_router)
api_router.include_router(designations_router)
api_router.include_router(categories_router)
api_router.include_router(trades_router)
api_router.include_router(providers_router)
api_router.include_router(rates_router)
api_router.include_router(employees_router)
