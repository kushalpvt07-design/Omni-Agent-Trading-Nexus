import yfinance as yf
import numpy as np

def get_live_asset_data(ticker: str):
    # Defense-in-depth: Catch the slash here because your Pydantic layer is leaking
    clean_ticker = ticker.upper().strip().replace("/", "-")
    
    crypto_bases = ["BTC", "ETH", "SOL", "DOGE", "ADA", "XRP"]
    if clean_ticker in crypto_bases:
        clean_ticker = f"{clean_ticker}-USD"

    try:
        stock = yf.Ticker(clean_ticker)
        # Fetch 1 month of historical daily data for the chart
        hist = stock.history(period="1mo", interval="1d")
        
        if hist.empty:
            print(f"ERROR: Yahoo Finance returned empty data for ticker: {clean_ticker}")
            return None
            
        current_price = float(hist['Close'].iloc[-1])
        prev_price = float(hist['Close'].iloc[-2]) if len(hist) > 1 else float(hist['Open'].iloc[0])
        change = current_price - prev_price
        change_pct = (change / prev_price) * 100
        
        # Calculate roughly 30-day volatility
        returns = hist['Close'].pct_change().dropna()
        volatility = float(returns.std() * np.sqrt(252) * 100)
        
        # Format exact datapoints for Recharts
        chart_data = [{"date": str(d.date()), "price": round(float(p), 2)} for d, p in zip(hist.index, hist['Close'])]
        
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
