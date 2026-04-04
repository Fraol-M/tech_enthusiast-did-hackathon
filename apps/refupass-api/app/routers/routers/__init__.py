from .admin import router as admin_router
from .auth import router as auth_router
from .platform import router as platform_router
from .system import router as system_router
from .worker import router as worker_router

routers = (
    system_router,
    platform_router,
    auth_router,
    admin_router,
    worker_router,
)
