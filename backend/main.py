from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import create_tables
from app.api import auth_router, resolutions_router, progress_router
from app.observability import init_opik


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_opik()
    await create_tables()
    yield


app = FastAPI(
    title="NeuroResolv API",
    description="Adaptive AI Tutor & Accountability Partner for New Year Resolutions",
    version="1.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(resolutions_router)
app.include_router(progress_router)


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


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred"},
    )
