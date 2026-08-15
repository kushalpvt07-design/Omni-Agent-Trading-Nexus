"""
src.api.routes.health — Infrastructure health probe.

This endpoint is intentionally unauthenticated so that load balancers,
Kubernetes liveness probes, and monitoring tools can reach it.
"""

from fastapi import APIRouter

from src.core.config import settings

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
