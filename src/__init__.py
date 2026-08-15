"""
src — Root package for the Omni-Agent Trading Nexus backend.

Subpackages:
    agents      — LangGraph agent node functions (parser, sentiment, quant, orchestrator, risk, execution)
    api         — FastAPI routes and middleware (REST + WebSocket)
    core        — Centralized configuration, logging, and input security
    persistence — Database and file-backed state management
    servers     — MCP (Model Context Protocol) data servers
"""
