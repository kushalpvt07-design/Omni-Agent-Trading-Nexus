import json
import random
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP named "SentimentServer"
mcp = FastMCP("SentimentServer")

def generate_mock_news(ticker: str) -> list:
    """Helper to generate contextual mock news headlines."""
    # Seed ensures consistent mock data per ticker for testing
    random.seed(ticker + "_news") 
    
    positive_headlines = [
        f"{ticker} smashes earnings expectations, raises forward guidance.",
        f"Analysts upgrade {ticker} following breakthrough product announcement.",
        f"Institutional buying surges for {ticker} as sector outlook improves."
    ]
    
    negative_headlines = [
        f"{ticker} faces new regulatory scrutiny in key markets.",
        f"Supply chain delays threaten {ticker}'s Q4 delivery targets.",
        f"Macro headwinds cause {ticker} to miss revenue estimates."
    ]
    
    neutral_headlines = [
        f"{ticker} announces routine leadership transition.",
        f"{ticker} holds annual shareholder meeting; no major surprises.",
        f"Market sideways on {ticker} pending upcoming CPI data."
    ]
    
    # Randomly select a mix of headlines to simulate a real news feed
    all_news = random.choices(positive_headlines, k=2) + \
               random.choices(negative_headlines, k=1) + \
               random.choices(neutral_headlines, k=1)
    
    random.shuffle(all_news)
    return all_news

@mcp.tool()
def analyze_market_sentiment(ticker: str) -> str:
    """
    Scrapes recent financial news and social media sentiment for a ticker,
    returning a structured sentiment score and narrative summary.
    """
    ticker_upper = ticker.upper().strip()
    
    if not ticker_upper or len(ticker_upper) > 5:
        return json.dumps({"status": "error", "message": "Invalid ticker symbol format."})
    
    # -----------------------------------------------------------------
    # PRODUCTION NOTE: To connect Grok (xAI) or a News API (like Finnhub/AlphaVantage),
    # you would replace this block with an actual API call to fetch headlines
    # and run them through a lightweight NLP model to get a real score.
    # -----------------------------------------------------------------
    
    try:
        headlines = generate_mock_news(ticker_upper)
        
        # Calculate a mock sentiment score between -1.0 (Bearish) and 1.0 (Bullish)
        random.seed(ticker_upper + "_score")
        score = round(random.uniform(-0.8, 0.9), 2)
        
        # Determine the label
        if score > 0.4:
            label = "BULLISH"
        elif score < -0.4:
            label = "BEARISH"
        else:
            label = "NEUTRAL"
            
        payload = {
            "status": "success",
            "ticker": ticker_upper,
            "sentiment_score": score,
            "sentiment_label": label,
            "top_headlines": headlines,
            "summary": f"Current market narrative for {ticker_upper} is {label} based on recent news volume."
        }
        
        return json.dumps(payload, indent=2)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to analyze sentiment: {str(e)}"})

if __name__ == "__main__":
    # Launch the MCP server via standard I/O
    mcp.run()
