import yfinance as yf
import pandas as pd
import numpy as np

def get_live_asset_data(ticker: str):
    clean_ticker = ticker.upper().strip().replace("/", "-")
    
    crypto_bases = ["BTC", "ETH", "SOL", "DOGE", "ADA", "XRP"]
    if clean_ticker in crypto_bases:
        clean_ticker = f"{clean_ticker}-USD"

    try:
        stock = yf.Ticker(clean_ticker)
        # FIX: Purge NaN records immediately. This prevents NaN floats from infecting JSON serialization.
        hist = stock.history(period="1mo", interval="1d").dropna(subset=['close'])
        
        if hist.empty:
            print(f"ERROR: Yahoo Finance returned empty data for ticker: {clean_ticker}")
            return None
            
        hist.columns = [c.lower() for c in hist.columns]
            
        current_price = float(hist['close'].iloc[-1])
        prev_price = float(hist['close'].iloc[-2]) if len(hist) > 1 else float(hist['close'].iloc[0])
        
        change = current_price - prev_price
        change_pct = (change / prev_price) * 100 if prev_price > 0 else 0.0
        
        returns = hist['close'].pct_change().dropna()
        vol_val = returns.std()
        
        volatility = float(vol_val * np.sqrt(252) * 100) if pd.notna(vol_val) else 0.0
        
        chart_data = [{"date": str(d.date()), "price": round(float(p), 2)} for d, p in zip(hist.index, hist['close'])]
        
        return {
            "ticker": clean_ticker,
            "current_price": round(current_price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volatility": round(volatility, 1),
            "is_positive": change >= 0,
            "chart_data": chart_data
        }
    except Exception as e:
        print(f"Error fetching asset data for {clean_ticker}: {e}")
        return None
