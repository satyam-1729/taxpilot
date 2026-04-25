from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.core.config import get_settings
from app.services.firebase import init_firebase
from app.services.redis_client import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    await init_redis()
    yield
    await close_redis()


settings = get_settings()
app = FastAPI(title="TaxPilot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
