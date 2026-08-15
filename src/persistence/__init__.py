"""
src.persistence — Database and file-backed state management.

Modules:
    checkpointer — LangGraph AsyncSqliteSaver lifecycle (get/set)

Public API:
    get_checkpointer  — Returns the active checkpointer (or None before startup)
    set_checkpointer  — Called during app lifespan to register the checkpointer

The portfolio ledger (portfolio_ledger.json) is managed by the risk_agent
and execution_agent modules directly via atomic file operations.
"""

from src.persistence.checkpointer import get_checkpointer, set_checkpointer

__all__ = [
    "get_checkpointer",
    "set_checkpointer",
]
