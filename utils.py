import yfinance as yf
import math

def get_live_asset_data(ticker_symbol: str):
    if not ticker_symbol or ticker_symbol == "UNKNOWN":
        return None
        
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1mo")
        
        if hist.empty:
            return None
            
        current_price = float(hist["Close"].iloc[-1])
        prev_price = float(hist["Close"].iloc[0])
        change_pct = ((current_price - prev_price) / prev_price) * 100
        
        returns = hist["Close"].pct_change().dropna()
        volatility = float(returns.std() * (252 ** 0.5) * 100) if not returns.empty else 0.0
        
        if math.isnan(volatility):
            volatility = 0.0

        chart_data = []
        for date, row in hist.iterrows():
            val = float(row["Close"])
            chart_data.append({
                "time": date.strftime("%b %d"),
                "price": round(val, 2) if not math.isnan(val) else 0.0
            })

        return {
            "ticker": ticker_symbol.upper(),
            "current_price": round(current_price, 2),
            "change_pct": round(change_pct, 2),
            "volatility": round(volatility, 2),
            "is_positive": change_pct >= 0,
            "chart_data": chart_data
        }
    except Exception as e:
        print(f"Error fetching asset data for {ticker_symbol}: {e}")
        return None
