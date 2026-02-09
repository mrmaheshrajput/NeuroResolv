from contextlib import asynccontextmanager

from app.api import (
    auth_router,
    email_router,
    progress_router,
    prompt_optimization_router,
    resolutions_router,
    streak_groups_router,
)
from app.mcp import mcp
from app.config import get_settings
from app.db import create_tables
from app.observability import init_opik
from app.core import decode_token
from app.core.context import current_user_id
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_opik()
    await create_tables()
    yield


app_configs = {
    "title": "NeuroResolv API",
    "description": "Adaptive AI Tutor & Accountability Partner for New Year Resolutions",
    "version": "1.1.0",
    "lifespan": lifespan,
}

if settings.environment != "development":
    app_configs.update(
        {
            "docs_url": None,
            "redoc_url": None,
            "openapi_url": None,
        }
    )

app = FastAPI(**app_configs)


async def verify_api_key(request: Request):
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")


app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        ["*"] if settings.environment != "development" else settings.cors_origins
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MCPAuthMiddleware:
    """Simple ASGI middleware to extract user from token for MCP tools."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("utf-8")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                payload = decode_token(token)
                if payload and "sub" in payload:
                    current_user_id.set(int(payload["sub"]))

        await self.app(scope, receive, send)


app.include_router(auth_router, dependencies=[Depends(verify_api_key)])
app.include_router(resolutions_router, dependencies=[Depends(verify_api_key)])
app.include_router(progress_router, dependencies=[Depends(verify_api_key)])
app.include_router(email_router, dependencies=[Depends(verify_api_key)])
app.include_router(streak_groups_router, dependencies=[Depends(verify_api_key)])
app.include_router(prompt_optimization_router, dependencies=[Depends(verify_api_key)])

# Mount MCP server with authentication middleware
app.mount("/mcp", MCPAuthMiddleware(mcp.sse_app()))


@app.get("/")
async def root():
    return {
        "name": "NeuroResolv API",
        "version": "1.1.0",
        "status": "running",
        "features": [
            "Milestone-based roadmaps",
            "Daily accountability check-ins",
            "Context-aware verification quizzes",
            "Adaptive failure recovery",
        ],
    }


@app.get("/health", dependencies=[Depends(verify_api_key)])
async def health_check():
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred"},
    )
