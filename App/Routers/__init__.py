from App.Routers.routers import router
from App.Routers.auth_routers import router as auth_router
from App.Routers.user_routers import router as user_router
from App.Routers.admin_routers import router as admin_router
from App.Routers.Product_routers import router as product_router

__all__ = [
    "router",
    "auth_router",
    "user_router",
    "admin_router",
    "product_router",
]
