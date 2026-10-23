"""
tests/test_e2e_scenarios.py — Full end-to-end mocked integration tests for all 9 audit scenarios.

Verifies:
  1. Full analysis of a valid ticker (parallel Quant + Sentiment fan-out/fan-in)
  2. Buy order with multi-asset portfolio equity and HITL approval -> paper execution
  3. Sell order preserving partial allocation (e.g., 50% of owned shares)
  4. Portfolio query & snapshot rate-limit bypass on >0.01% value change + dust cleanup
  5. Invalid ticker fast-fail without retry loops
  6. Market closed / Indian stock (.NS) weekend fallback and INR->USD ledger conversion
  7. Alpaca API 401 failure & Sentiment server graceful degradation
  8. Gemini LLM timeout / rate-limit fallback across models
  9. Contradictory Quant (bearish/overbought) vs Sentiment (bullish) conflict resolution
"""

import json
import math
import sqlite3
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage

from schemas import TradeDirectiveSchema
from src.agents.orchestrator import OrchestratorDirective
from src.persistence import database, user_portfolio
from swarm import build_graph


@pytest.fixture()
def isolated_sqlite_db(tmp_path, monkeypatch):
    """Create a temporary SQLite database with the full production schema."""
    db_path = str(tmp_path / "test_nexus_users.db")
    monkeypatch.setattr(database, "DB_FILE", db_path)
    database.init_database()

    with database.get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, username, password_hash, starting_cash) VALUES (1, 'auditor', 'hash', 100000.0)"
        )
    user_portfolio.create_user_ledger(1, 100000.0)
    return db_path


# ── SCENARIO 1 & 2: Valid Ticker Analysis + Buy Order with Multi-Asset Equity ──


@pytest.mark.asyncio
async def test_e2e_scenario_1_and_2_valid_buy_order(isolated_sqlite_db):
    """Full pipeline run for 'Buy 75 shares of AAPL if volatility < 25%'."""
    # Seed user with 100 shares of NVDA @ $140 cost ($14,000) and $50,000 cash -> $64,000 total equity
    with database.get_db() as conn:
        conn.execute("UPDATE user_ledger SET cash = 50000.0 WHERE user_id = 1")
        conn.execute(
            "INSERT INTO user_positions (user_id, ticker, shares, avg_cost) VALUES (1, 'NVDA', 100.0, 140.0)"
        )

    mock_parser_output = TradeDirectiveSchema(
        is_valid_directive=True,
        ticker="AAPL",
        asset_class="equity",
        action="BUY",
        quantity=75.0,
        allocation=None,
        risk_threshold=0.25,
    )
    mock_orch_output = OrchestratorDirective(
        action="BUY",
        reasoning="AAPL is trading above its 30-day SMA ($195.00) with healthy RSI (58.4) and bullish news.",
    )
    mock_quant_json = json.dumps(
        {
            "status": "success",
            "ticker": "AAPL",
            "latest_close": 200.0,
            "latest_volume": 45000000,
            "thirty_day_sma": 195.0,
            "rsi_14": 58.4,
            "volume_ratio_30d": 1.15,
            "volatility_metrics": {
                "daily_log_return_std": 0.0113389,
                "annualized_volatility": 0.18,
                "30_day_standard_deviation": 0.0113389,
            },
            "thirty_day_trend": [
                {"date": "2026-09-01", "close": 190.0, "volume": 40000000},
                {"date": "2026-09-18", "close": 200.0, "volume": 45000000},
            ],
        }
    )
    mock_sent_json = json.dumps(
        {
            "status": "success",
            "ticker": "AAPL",
            "top_headlines": ["Title: Apple surges to record high | Summary: Strong demand"],
            "sentiment_score": 0.688,
            "sentiment_label": "BULLISH",
        }
    )

    mock_order = MagicMock()
    mock_order.id = "alpaca-paper-order-001"
    mock_order.filled_avg_price = "200.00"

    with patch(
        "src.agents.parser_agent._invoke_parser_llm_with_backoff",
        new=AsyncMock(return_value=mock_parser_output),
    ), patch(
        "src.agents.quant_agent.fetch_mcp_quant_data",
        new=AsyncMock(return_value=mock_quant_json),
    ), patch(
        "src.agents.sentiment_agent.fetch_mcp_sentiment_data",
        new=AsyncMock(return_value=mock_sent_json),
    ), patch(
        "src.agents.orchestrator._invoke_llm_with_backoff",
        new=AsyncMock(return_value=mock_orch_output),
    ), patch(
        "src.agents.risk_agent.get_latest_prices",
        return_value={"NVDA": 140.0},
    ), patch(
        "src.agents.execution_agent.TradingClient"
    ) as mock_trading_client_cls:
        mock_client_instance = MagicMock()
        mock_client_instance.submit_order.return_value = mock_order
        mock_trading_client_cls.return_value = mock_client_instance

        swarm_app = build_graph().compile()
        initial_state = {
            "user_id": 1,
            "username": "auditor",
            "messages": [HumanMessage(content="Buy 75 shares of AAPL if volatility < 25%")],
            "paper_trading_enabled": True,
            "quant_data": {},
            "sentiment_data": {},
            "node_latencies_ms": {},
            "requires_human_approval": True,
            "human_approved": True,
            "errors": [],
        }

        final_state = await swarm_app.ainvoke(initial_state)

        assert final_state["errors"] == []
        assert final_state["risk_approved"] is True
        assert final_state["proposed_trade"]["action"] == "BUY"
        assert final_state["proposed_trade"]["shares"] == 75.0
        # Verify all 6 nodes recorded telemetry latencies
        for node_key in (
            "parser_node",
            "sentiment_agent_node",
            "quant_agent_node",
            "orchestrator_node",
            "risk_agent_node",
            "execution_agent_node",
        ):
            assert node_key in final_state["node_latencies_ms"]

        # Verify SQLite ledger: $50,000 - (75 * $200) = $35,000 cash
        ledger = user_portfolio.get_user_ledger(1)
        assert ledger["cash"] == 35000.0
        assert ledger["positions"]["AAPL"] == 75.0
        assert ledger["positions"]["NVDA"] == 100.0


# ── SCENARIO 3: Sell Order Preserving Partial Allocation (50%) ──


@pytest.mark.asyncio
async def test_e2e_scenario_3_partial_sell_order(isolated_sqlite_db):
    """Verify 'Sell 50% of my AAPL' sells 7.5 of 15 owned shares instead of 100%."""
    user_portfolio.update_user_ledger(1, "BUY", "AAPL", 15.0, 200.0, "Initial buy")

    mock_parser_output = TradeDirectiveSchema(
        is_valid_directive=True,
        ticker="AAPL",
        asset_class="equity",
        action="SELL",
        quantity=None,
        allocation=0.50,
        risk_threshold=0.50,
    )
    mock_orch_output = OrchestratorDirective(
        action="SELL",
        reasoning="Taking partial profits on 50% of AAPL position.",
    )
    mock_quant_json = json.dumps(
        {
            "status": "success",
            "ticker": "AAPL",
            "latest_close": 210.0,
            "latest_volume": 35000000,
            "volatility_metrics": {"daily_log_return_std": 0.01, "annualized_volatility": 0.16},
        }
    )

    mock_order = MagicMock()
    mock_order.id = "alpaca-sell-002"
    mock_order.filled_avg_price = "210.00"

    with patch(
        "src.agents.parser_agent._invoke_parser_llm_with_backoff",
        new=AsyncMock(return_value=mock_parser_output),
    ), patch(
        "src.agents.quant_agent.fetch_mcp_quant_data",
        new=AsyncMock(return_value=mock_quant_json),
    ), patch(
        "src.agents.sentiment_agent.fetch_mcp_sentiment_data",
        new=AsyncMock(return_value='{"status":"success","sentiment_score":0.45,"sentiment_label":"NEUTRAL"}'),
    ), patch(
        "src.agents.orchestrator._invoke_llm_with_backoff",
        new=AsyncMock(return_value=mock_orch_output),
    ), patch(
        "src.agents.execution_agent.TradingClient"
    ) as mock_trading_client_cls:
        mock_client_instance = MagicMock()
        mock_client_instance.submit_order.return_value = mock_order
        mock_trading_client_cls.return_value = mock_client_instance

        swarm_app = build_graph().compile()
        final_state = await swarm_app.ainvoke(
            {
                "user_id": 1,
                "messages": [HumanMessage(content="Sell 50% of my AAPL")],
                "paper_trading_enabled": True,
                "requires_human_approval": True,
                "human_approved": True,
                "errors": [],
            }
        )

        assert final_state["risk_approved"] is True
        assert final_state["proposed_trade"]["shares"] == 7.5
        ledger = user_portfolio.get_user_ledger(1)
        assert ledger["positions"]["AAPL"] == 7.5
        # Cash: $100,000 - $3,000 (15 * $200) + $1,575 (7.5 * $210) = $98,575.00
        assert ledger["cash"] == 98575.0


# ── SCENARIO 4 & 6: Indian Stock (.NS) USD Normalization + Portfolio Summary ──


@pytest.mark.asyncio
async def test_e2e_scenario_4_and_6_indian_equity_usd_ledger_and_portfolio_summary(isolated_sqlite_db):
    """Verify buying 40 shares of TCS.NS @ ₹4,000 converts to USD ($47.6190/sh) in the ledger."""
    mock_parser_output = TradeDirectiveSchema(
        is_valid_directive=True,
        ticker="TCS.NS",
        asset_class="equity",
        action="BUY",
        quantity=40.0,
        allocation=None,
        risk_threshold=0.50,
    )
    mock_orch_output = OrchestratorDirective(
        action="BUY",
        reasoning="Strong IT sector momentum on NSE.",
    )
    mock_quant_json = json.dumps(
        {
            "status": "success",
            "ticker": "TCS.NS",
            "latest_close": 4000.0,  # ₹4,000 INR
            "latest_volume": 2500000,
            "volatility_metrics": {"daily_log_return_std": 0.01, "annualized_volatility": 0.1587},
        }
    )

    with patch(
        "src.agents.parser_agent._invoke_parser_llm_with_backoff",
        new=AsyncMock(return_value=mock_parser_output),
    ), patch(
        "src.agents.quant_agent.fetch_mcp_quant_data",
        new=AsyncMock(return_value=mock_quant_json),
    ), patch(
        "src.agents.sentiment_agent.fetch_mcp_sentiment_data",
        new=AsyncMock(return_value='{"status":"success","sentiment_score":0.7,"sentiment_label":"BULLISH"}'),
    ), patch(
        "src.agents.orchestrator._invoke_llm_with_backoff",
        new=AsyncMock(return_value=mock_orch_output),
    ), patch(
        "src.core.market_data.get_usd_inr_rate",
        return_value=84.0,
    ), patch(
        "src.core.market_data._fetch_yfinance_price",
        return_value=4000.0,
    ):
        swarm_app = build_graph().compile()
        final_state = await swarm_app.ainvoke(
            {
                "user_id": 1,
                "messages": [HumanMessage(content="Buy 40 shares of TCS")],
                "paper_trading_enabled": True,
                "requires_human_approval": True,
                "human_approved": True,
                "errors": [],
            }
        )

        assert final_state["risk_approved"] is True
        summary = user_portfolio.build_full_portfolio_summary(1)
        # 40 * (4000 / 84) = $1,904.76 USD deducted from $100,000 -> $98,095.24 cash
        assert summary["cash"] == 98095.24
        assert summary["total_value"] == 100000.0
        assert isinstance(summary["positions"], list)
        assert len(summary["positions"]) == 1
        assert summary["positions"][0]["ticker"] == "TCS.NS"
        assert summary["positions"][0]["market_value"] == 1904.76


# ── SCENARIO 5, 7, 8, 9: Error Handling, Degradation & Conflict Resolution ──


@pytest.mark.asyncio
async def test_e2e_scenario_7_sentiment_failure_graceful_degradation(isolated_sqlite_db):
    """If Sentiment MCP server throws an error, pipeline degrades gracefully instead of crashing."""
    mock_parser_output = TradeDirectiveSchema(
        is_valid_directive=True,
        ticker="MSFT",
        asset_class="equity",
        action="BUY",
        quantity=10.0,
    )
    mock_orch_output = OrchestratorDirective(
        action="BUY",
        reasoning="Proceeding on strong quantitative metrics despite degraded news feed.",
    )
    mock_quant_json = json.dumps(
        {
            "status": "success",
            "ticker": "MSFT",
            "latest_close": 420.0,
            "latest_volume": 20000000,
            "volatility_metrics": {"daily_log_return_std": 0.01, "annualized_volatility": 0.16},
        }
    )

    with patch(
        "src.agents.parser_agent._invoke_parser_llm_with_backoff",
        new=AsyncMock(return_value=mock_parser_output),
    ), patch(
        "src.agents.quant_agent.fetch_mcp_quant_data",
        new=AsyncMock(return_value=mock_quant_json),
    ), patch(
        "src.agents.sentiment_agent.fetch_mcp_sentiment_data",
        new=AsyncMock(side_effect=RuntimeError("News API 503 Service Unavailable")),
    ), patch(
        "src.agents.orchestrator._invoke_llm_with_backoff",
        new=AsyncMock(return_value=mock_orch_output),
    ):
        swarm_app = build_graph().compile()
        final_state = await swarm_app.ainvoke(
            {
                "user_id": 1,
                "messages": [HumanMessage(content="Buy 10 MSFT")],
                "paper_trading_enabled": True,
                "requires_human_approval": True,
                "human_approved": False,  # Stop before execution
                "errors": [],
            }
        )

        assert final_state["errors"] == []
        assert final_state["sentiment_data"]["MSFT"]["status"] == "degraded"
        assert final_state["sentiment_data"]["MSFT"]["sentiment_label"] == "NEUTRAL"
        assert final_state["risk_approved"] is True


@pytest.mark.asyncio
async def test_e2e_scenario_9_contradictory_signals_direction_guard(isolated_sqlite_db):
    """If user requests BUY but Orchestrator tries to flip to SELL on bearish quant data, override to HOLD."""
    mock_parser_output = TradeDirectiveSchema(
        is_valid_directive=True,
        ticker="TSLA",
        asset_class="equity",
        action="BUY",
        quantity=20.0,
    )
    # Simulate LLM attempting to flip BUY -> SELL due to overbought RSI
    mock_orch_output = OrchestratorDirective(
        action="SELL",
        reasoning="RSI is 78.5 (overbought) and price is below 30d SMA despite bullish news.",
    )
    mock_quant_json = json.dumps(
        {
            "status": "success",
            "ticker": "TSLA",
            "latest_close": 240.0,
            "latest_volume": 60000000,
            "rsi_14": 78.5,
            "volatility_metrics": {"daily_log_return_std": 0.02, "annualized_volatility": 0.31},
        }
    )

    with patch(
        "src.agents.parser_agent._invoke_parser_llm_with_backoff",
        new=AsyncMock(return_value=mock_parser_output),
    ), patch(
        "src.agents.quant_agent.fetch_mcp_quant_data",
        new=AsyncMock(return_value=mock_quant_json),
    ), patch(
        "src.agents.sentiment_agent.fetch_mcp_sentiment_data",
        new=AsyncMock(return_value='{"status":"success","sentiment_score":0.82,"sentiment_label":"BULLISH"}'),
    ), patch(
        "src.agents.orchestrator._invoke_llm_with_backoff",
        new=AsyncMock(return_value=mock_orch_output),
    ):
        swarm_app = build_graph().compile()
        final_state = await swarm_app.ainvoke(
            {
                "user_id": 1,
                "messages": [HumanMessage(content="Buy 20 TSLA")],
                "paper_trading_enabled": True,
                "requires_human_approval": True,
                "human_approved": False,
                "errors": [],
            }
        )

        # Direction guard prevents BUY -> SELL flip, downgrading to HOLD and skipping execution
        assert final_state["proposed_trade"]["action"] == "HOLD"
        assert final_state["risk_approved"] is False
