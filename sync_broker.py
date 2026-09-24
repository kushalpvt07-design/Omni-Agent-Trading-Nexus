"""
sync_broker.py — Pull live portfolio state from Alpaca and write to the local ledger.

Usage (standalone):
    python sync_broker.py

Can also be imported:
    from sync_broker import sync_alpaca_to_ledger
    ledger = sync_alpaca_to_ledger()
"""

import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

from alpaca.trading.client import TradingClient

logger = logging.getLogger("omni-nexus.sync")

LEDGER_FILE = os.getenv("LEDGER_FILE", "portfolio_ledger.json")


def sync_alpaca_to_ledger() -> dict:
    """Fetch account + positions from Alpaca and overwrite the local ledger.

    Returns the new ledger dict on success.
    Raises on auth or network failures.
    """
    api_key = os.getenv("ALPACA_API_KEY")
    sec_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not sec_key:
        raise RuntimeError(
            "Missing ALPACA_API_KEY / ALPACA_SECRET_KEY in environment. "
            "Set them in your .env file."
        )

    # paper=True because these are paper-trading keys
    client = TradingClient(api_key, sec_key, paper=True)

    # ── Fetch account cash balance ──────────────────────────────
    account = client.get_account()
    cash = float(account.cash)

    logger.info("Alpaca account synced — Cash: $%.2f", cash)

    # ── Fetch all open positions ────────────────────────────────
    positions_raw = client.get_all_positions()
    positions: dict[str, float] = {}

    for pos in positions_raw:
        symbol = pos.symbol
        qty = float(pos.qty)
        if qty > 0:
            positions[symbol] = qty
            logger.info(
                "  Position: %s — %s shares @ $%s (market value: $%s)",
                symbol,
                pos.qty,
                pos.current_price,
                pos.market_value,
            )

    # ── Write to ledger ─────────────────────────────────────────
    ledger = {"cash": cash, "positions": positions}

    import tempfile
    dir_name = os.path.dirname(os.path.abspath(LEDGER_FILE))
    fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=dir_name)
    try:
        with os.fdopen(fd, "w") as tmp_f:
            json.dump(ledger, tmp_f, indent=4)
        os.replace(tmp_path, LEDGER_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    logger.info(
        "Ledger synced: $%.2f cash, %d positions written to %s",
        cash,
        len(positions),
        LEDGER_FILE,
    )

    return ledger


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        ledger = sync_alpaca_to_ledger()
        print("\n[OK] Broker sync complete!")
        print(f"   Cash:      ${ledger['cash']:,.2f}")
        print(f"   Positions: {len(ledger['positions'])}")
        for ticker, shares in ledger["positions"].items():
            print(f"     - {ticker}: {shares} shares")
    except Exception as e:
        print(f"\n[FAIL] Sync failed: {e}")
        raise SystemExit(1)
