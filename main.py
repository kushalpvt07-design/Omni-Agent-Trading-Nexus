"""
Omni-Agent Trading Nexus — Application Entry Point

This is the thin composition root. All business logic lives in:
  - src/api/routes/       → REST and WebSocket endpoints
  - src/api/middleware/    → Authentication
  - src/core/             → Config, security, logging
  - src/persistence/      → Checkpointer lifecycle
  - src/agents/           → LangGraph agent nodes
  - src/servers/          → MCP data servers

Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from src.core.config import settings, logger
from src.persistence.checkpointer import set_checkpointer

# ── Route Imports ───────────────────────────────────────────────
from src.api.routes import health, analyze, swarm_stream


# ── Application Lifespan ────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSqliteSaver.from_conn_string(settings.CHECKPOINT_DB) as checkpointer:
        await checkpointer.setup()
        set_checkpointer(checkpointer)
        logger.info("Omni-Agent Trading Nexus started — v%s", settings.APP_VERSION)
        yield


# ── FastAPI Application ─────────────────────────────────────────
app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routes ─────────────────────────────────────────────
app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(swarm_stream.router)
