import os
import requests
from datetime import datetime
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

ALPACA_KEY = os.environ.get('ALPACA_KEY')
ALPACA_SECRET = os.environ.get('ALPACA_SECRET')

trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)

def scrape_market_chatter():
    tickers = []
    
    # Simple Reddit WSB scraper
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get('https://www.reddit.com/r/wallstreetbets/hot.json', headers=headers)
        data = response.json()
        
        for post in data['data']['children'][:10]:
            title = post['data']['title'].upper()
            # Extract potential tickers (3-5 letter words in caps)
            words = title.split()
            for word in words:
                if 3 <= len(word) <= 5 and word.isalpha() and word.isupper():
                    tickers.append(word)
    except Exception as e:
        print(f"Error scraping: {e}")
    
    # Count mentions
    ticker_counts = {}
    for ticker in tickers:
        ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
    
    # Get top mentioned
    sorted_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_tickers[:5]

def analyze_and_trade():
    top_tickers = scrape_market_chatter()
    print(f"[{datetime.now()}] Top mentioned tickers: {top_tickers}")
    
    if top_tickers and top_tickers[0][1] >= 3:  # At least 3 mentions
        symbol = top_tickers[0][0]
        
        # Simple momentum trade
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=1,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY
        )
        
        try:
            order = trading_client.submit_order(order_data)
            print(f"Placed order for {symbol}: {order}")
        except Exception as e:
            print(f"Error placing order: {e}")

if __name__ == "__main__":
    analyze_and_trade()