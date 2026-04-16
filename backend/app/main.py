import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, redis_client
from app.routers import auth, credentials, mfa, sessions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up...")
    yield
    logger.info("Shutting down...")
    await engine.dispose()
    await redis_client.close()


app = FastAPI(
    title="Multi-Subject Auth System",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(credentials.router)
app.include_router(mfa.router)
app.include_router(sessions.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
