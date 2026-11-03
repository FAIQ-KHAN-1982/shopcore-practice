from fastapi import APIRouter
from App.Routers.auth_routers import router as auth_router
from App.Routers.user_routers import router as user_router
from App.Routers.admin_routers import router as admin_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(user_router)
router.include_router(admin_router)
