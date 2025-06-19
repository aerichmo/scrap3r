import os
import re
import json
import requests
from datetime import datetime
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.requests import StockLatestQuoteRequest

ALPACA_KEY = os.environ.get('ALPACA_KEY')
ALPACA_SECRET = os.environ.get('ALPACA_SECRET')

trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)
data_client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)

# Sentiment keywords
BULLISH_WORDS = ['moon', 'rocket', 'buy', 'calls', 'squeeze', 'gamma', 'pump', 'bull', 'long', 'yolo', 'diamond hands', 'hold', 'hodl']
BEARISH_WORDS = ['puts', 'short', 'sell', 'dump', 'crash', 'bear', 'red', 'drop', 'tank', 'drill']

# Trading parameters
PROFIT_TARGET = 0.05  # 5% profit target
STOP_LOSS = 0.02      # 2% stop loss
MAX_POSITION_SIZE = 100  # Max $100 per position

def calculate_sentiment(text):
    text_lower = text.lower()
    bullish_score = sum(1 for word in BULLISH_WORDS if word in text_lower)
    bearish_score = sum(1 for word in BEARISH_WORDS if word in text_lower)
    
    if bullish_score + bearish_score == 0:
        return 0
    
    sentiment = (bullish_score - bearish_score) / (bullish_score + bearish_score)
    return sentiment

def scrape_market_chatter():
    ticker_data = {}
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get('https://www.reddit.com/r/wallstreetbets/hot.json', headers=headers)
        data = response.json()
        
        for post in data['data']['children'][:20]:  # Check more posts
            title = post['data']['title']
            selftext = post['data']['selftext']
            full_text = f"{title} {selftext}"
            
            # Calculate sentiment for the post
            sentiment = calculate_sentiment(full_text)
            
            # Extract tickers with $ prefix or common patterns
            ticker_pattern = r'\$([A-Z]{1,5})|(?:^|\s)([A-Z]{2,5})(?:\s|$)'
            matches = re.findall(ticker_pattern, full_text)
            
            for match in matches:
                ticker = match[0] or match[1]
                if ticker and len(ticker) >= 2:
                    if ticker not in ticker_data:
                        ticker_data[ticker] = {
                            'mentions': 0,
                            'sentiment_sum': 0,
                            'sentiment_count': 0
                        }
                    ticker_data[ticker]['mentions'] += 1
                    ticker_data[ticker]['sentiment_sum'] += sentiment
                    ticker_data[ticker]['sentiment_count'] += 1
    
    except Exception as e:
        print(f"Error scraping: {e}")
    
    # Calculate average sentiment and filter
    results = []
    for ticker, data in ticker_data.items():
        if data['mentions'] >= 3:  # Minimum mentions
            avg_sentiment = data['sentiment_sum'] / data['sentiment_count'] if data['sentiment_count'] > 0 else 0
            results.append({
                'ticker': ticker,
                'mentions': data['mentions'],
                'sentiment': avg_sentiment
            })
    
    # Sort by sentiment score * mentions (weighted score)
    results.sort(key=lambda x: x['sentiment'] * x['mentions'], reverse=True)
    return results[:5]

def get_current_price(symbol):
    try:
        request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        quote = data_client.get_stock_latest_quote(request)
        return float(quote[symbol].ask_price)
    except:
        return None

def check_existing_positions():
    try:
        positions = trading_client.get_all_positions()
        position_data = {}
        
        for position in positions:
            current_price = float(position.current_price)
            avg_price = float(position.avg_entry_price)
            profit_pct = (current_price - avg_price) / avg_price
            
            position_data[position.symbol] = {
                'qty': int(position.qty),
                'avg_price': avg_price,
                'current_price': current_price,
                'profit_pct': profit_pct
            }
            
            # Check if we should sell
            if profit_pct >= PROFIT_TARGET:
                print(f"[{datetime.now()}] Taking profit on {position.symbol} at {profit_pct:.2%}")
                sell_order = MarketOrderRequest(
                    symbol=position.symbol,
                    qty=position.qty,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                )
                trading_client.submit_order(sell_order)
            
            elif profit_pct <= -STOP_LOSS:
                print(f"[{datetime.now()}] Stop loss triggered for {position.symbol} at {profit_pct:.2%}")
                sell_order = MarketOrderRequest(
                    symbol=position.symbol,
                    qty=position.qty,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                )
                trading_client.submit_order(sell_order)
        
        return position_data
    except Exception as e:
        print(f"Error checking positions: {e}")
        return {}

def analyze_and_trade():
    # First check existing positions
    existing_positions = check_existing_positions()
    print(f"[{datetime.now()}] Current positions: {existing_positions}")
    
    # Get market sentiment
    top_tickers = scrape_market_chatter()
    print(f"[{datetime.now()}] Top tickers by sentiment: {json.dumps(top_tickers, indent=2)}")
    
    if not top_tickers:
        return
    
    # Only trade the highest sentiment ticker that we don't already own
    for ticker_data in top_tickers:
        symbol = ticker_data['ticker']
        sentiment = ticker_data['sentiment']
        
        # Skip if we already have a position
        if symbol in existing_positions:
            continue
        
        # Only buy if sentiment is strongly positive
        if sentiment >= 0.3:  # 30% positive sentiment threshold
            price = get_current_price(symbol)
            if not price:
                continue
            
            # Calculate position size
            qty = int(MAX_POSITION_SIZE / price)
            if qty < 1:
                qty = 1
            
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            
            try:
                order = trading_client.submit_order(order_data)
                print(f"[{datetime.now()}] Bought {qty} shares of {symbol} at ~${price:.2f} (sentiment: {sentiment:.2f})")
                break  # Only buy one stock per run
            except Exception as e:
                print(f"Error placing order for {symbol}: {e}")

if __name__ == "__main__":
    analyze_and_trade()