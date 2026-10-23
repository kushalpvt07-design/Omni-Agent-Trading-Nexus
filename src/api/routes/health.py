"""
src.api.routes.health — Infrastructure health probe and telemetry metrics endpoint.
"""

from fastapi import APIRouter
from src.core.config import settings
from src.core.telemetry import telemetry

router = APIRouter(tags=["Infrastructure"])


@router.get("/health")
async def health_check():
    """Infrastructure health probe for load balancers and monitoring."""
    from src.persistence.checkpointer import get_checkpointer

    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "checkpointer": "ready" if get_checkpointer() else "initializing",
    }


@router.get("/api/v1/metrics")
async def get_metrics():
    """Return real-time swarm latency (T_avg) and execution success rate (E_s) telemetry."""
    return telemetry.get_snapshot()
