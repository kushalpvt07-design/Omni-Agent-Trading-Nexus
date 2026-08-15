"""
src.api — FastAPI routes and middleware.

Subpackages:
    middleware  — Authentication (API key header + WebSocket token)
    routes     — Endpoint handlers (health, analyze, swarm_stream)

Usage:
    Routers are registered in main.py via app.include_router().
"""

from src.api.routes import health, analyze, swarm_stream

__all__ = [
    "health",
    "analyze",
    "swarm_stream",
]
