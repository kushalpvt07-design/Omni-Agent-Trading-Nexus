"""
src.persistence.checkpointer — LangGraph checkpoint store lifecycle.

Manages the global AsyncSqliteSaver instance. The checkpointer is initialized
during app startup (lifespan) and accessed by route handlers via get_checkpointer().
"""

import logging
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

logger = logging.getLogger("omni-nexus.persistence")

_checkpointer: AsyncSqliteSaver | None = None


def get_checkpointer() -> AsyncSqliteSaver | None:
    """Returns the global checkpointer instance, or None if not yet initialized."""
    return _checkpointer


def set_checkpointer(checkpointer: AsyncSqliteSaver) -> None:
    """Called by the app lifespan to set the global checkpointer."""
    global _checkpointer
    _checkpointer = checkpointer
    logger.info("Checkpoint store initialized")
