from app.api.auth import router as auth_router
from app.api.resolutions import router as resolutions_router
from app.api.sessions import router as sessions_router
from app.api.progress import router as progress_router

__all__ = [
    "auth_router",
    "resolutions_router",
    "sessions_router",
    "progress_router",
]
