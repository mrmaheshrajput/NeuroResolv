from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import create_tables
from app.observability import init_opik
from app.api import auth_router, resolutions_router, sessions_router, progress_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_opik()
    await create_tables()
    yield


app = FastAPI(
    title="NeuroResolv API",
    description="Adaptive AI Tutor & Accountability Partner for New Year Resolutions",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(resolutions_router)
app.include_router(sessions_router)
app.include_router(progress_router)


@app.get("/")
async def root():
    return {
        "name": "NeuroResolv API",
        "version": "1.0.0",
        "description": "Adaptive AI Tutor for New Year Resolutions",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )
