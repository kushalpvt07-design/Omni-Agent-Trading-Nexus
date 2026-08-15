"""
src.servers — MCP (Model Context Protocol) data servers.

These are standalone server processes spawned by agents via stdio transport.
Each server exposes tools that agents call to fetch live market data.

Servers:
    quant_server      — Alpaca historical bars, volatility metrics, price data
    sentiment_server  — yfinance news headlines for sentiment analysis

Usage:
    Agents spawn these as subprocesses via MCP's StdioServerParameters.
    They are NOT imported directly — they run as separate processes:

        python -m src.servers.quant_server
        python -m src.servers.sentiment_server
"""
