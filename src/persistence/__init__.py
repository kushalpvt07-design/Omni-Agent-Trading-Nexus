"""
src.persistence — Database and file-backed state management.

Modules:
    checkpointer    — LangGraph AsyncSqliteSaver lifecycle (get/set)
    database        — SQLite connection factory and schema migrations
    user_portfolio  — Per-user portfolio ledger, snapshots, and trade history

Public API:
    get_checkpointer  — Returns the active checkpointer (or None before startup)
    set_checkpointer  — Called during app lifespan to register the checkpointer

All portfolio state is persisted in nexus_users.db via user_portfolio.py.
"""

from src.persistence.checkpointer import get_checkpointer, set_checkpointer

__all__ = [
    "get_checkpointer",
    "set_checkpointer",
]
