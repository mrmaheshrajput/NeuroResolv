from app.api.auth import router as auth_router
from app.api.email import router as email_router
from app.api.progress import router as progress_router
from app.api.resolutions import router as resolutions_router
from app.api.streak_groups import router as streak_groups_router

__all__ = [
    "auth_router",
    "email_router",
    "resolutions_router",
    "progress_router",
    "streak_groups_router",
]
