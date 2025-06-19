import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import aiohttp
from alpaca.trading.client import TradingClient
from alpaca.data.live import StockDataStream
from alpaca.data.models import Bar, Trade, Quote
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Import our sentiment analysis
from scraper import scrape_market_chatter, calculate_sentiment

ALPACA_KEY = os.environ.get('ALPACA_KEY')
ALPACA_SECRET = os.environ.get('ALPACA_SECRET')

# Trading parameters
PROFIT_TARGET = 0.05
STOP_LOSS = 0.02
MAX_POSITION_SIZE = 100
MIN_SENTIMENT = 0.3

class MCPTrader:
    def __init__(self):
        self.trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)
        self.data_stream = StockDataStream(ALPACA_KEY, ALPACA_SECRET)
        self.watched_symbols = set()
        self.symbol_data = {}
        
    async def start(self):
        """Initialize the MCP trading system"""
        print(f"[{datetime.now()}] Starting MCP Trader...")
        
        # Get initial sentiment data
        await self.update_sentiment()
        
        # Subscribe to real-time data for high-sentiment stocks
        await self.setup_data_streams()
        
        # Start the data stream
        await self.data_stream.run()
    
    async def update_sentiment(self):
        """Update sentiment scores from Reddit"""
        top_tickers = scrape_market_chatter()
        
        for ticker_data in top_tickers:
            symbol = ticker_data['ticker']
            sentiment = ticker_data['sentiment']
            
            if sentiment >= MIN_SENTIMENT:
                self.symbol_data[symbol] = {
                    'sentiment': sentiment,
                    'mentions': ticker_data['mentions'],
                    'last_update': datetime.now()
                }
                self.watched_symbols.add(symbol)
                
        print(f"[{datetime.now()}] Watching {len(self.watched_symbols)} symbols: {self.watched_symbols}")
    
    async def setup_data_streams(self):
        """Subscribe to real-time data streams"""
        if not self.watched_symbols:
            return
            
        # Subscribe to quotes for sentiment-positive stocks
        self.data_stream.subscribe_quotes(self.on_quote, *self.watched_symbols)
        self.data_stream.subscribe_trades(self.on_trade, *self.watched_symbols)
        self.data_stream.subscribe_bars(self.on_bar, *self.watched_symbols)
    
    async def on_quote(self, quote: Quote):
        """Handle real-time quote updates"""
        symbol = quote.symbol
        
        # Check for tight bid-ask spread (liquidity)
        spread = quote.ask_price - quote.bid_price
        spread_pct = spread / quote.bid_price if quote.bid_price > 0 else 1
        
        if symbol in self.symbol_data:
            self.symbol_data[symbol]['spread'] = spread_pct
            self.symbol_data[symbol]['last_quote'] = quote
    
    async def on_trade(self, trade: Trade):
        """Handle real-time trade data"""
        symbol = trade.symbol
        
        if symbol not in self.symbol_data:
            return
            
        # Track volume spikes
        if 'trades' not in self.symbol_data[symbol]:
            self.symbol_data[symbol]['trades'] = []
            
        self.symbol_data[symbol]['trades'].append({
            'price': trade.price,
            'size': trade.size,
            'time': trade.timestamp
        })
        
        # Keep only last 100 trades
        if len(self.symbol_data[symbol]['trades']) > 100:
            self.symbol_data[symbol]['trades'].pop(0)
        
        # Check for unusual volume
        await self.check_volume_spike(symbol)
    
    async def on_bar(self, bar: Bar):
        """Handle real-time bar data"""
        symbol = bar.symbol
        
        if symbol not in self.symbol_data:
            return
            
        # Store the bar data
        self.symbol_data[symbol]['last_bar'] = bar
        
        # Check entry conditions
        await self.check_entry_conditions(symbol)
    
    async def check_volume_spike(self, symbol: str):
        """Check for unusual volume patterns"""
        if 'trades' not in self.symbol_data[symbol]:
            return
            
        recent_trades = self.symbol_data[symbol]['trades'][-20:]
        if len(recent_trades) < 20:
            return
            
        # Calculate average trade size
        avg_size = sum(t['size'] for t in recent_trades) / len(recent_trades)
        
        # Check if latest trades are significantly larger
        latest_sizes = [t['size'] for t in recent_trades[-5:]]
        if any(size > avg_size * 3 for size in latest_sizes):
            self.symbol_data[symbol]['volume_spike'] = True
            print(f"[{datetime.now()}] Volume spike detected for {symbol}")
    
    async def check_entry_conditions(self, symbol: str):
        """Check if we should enter a position"""
        data = self.symbol_data.get(symbol, {})
        
        # Required conditions
        if not all(k in data for k in ['sentiment', 'last_bar', 'spread']):
            return
            
        # Skip if we already have a position
        positions = self.trading_client.get_all_positions()
        if any(p.symbol == symbol for p in positions):
            return
            
        # Entry conditions
        sentiment_good = data['sentiment'] >= MIN_SENTIMENT
        spread_tight = data.get('spread', 1) < 0.002  # 0.2% spread
        volume_spike = data.get('volume_spike', False)
        
        # Price momentum (current close > previous close)
        bar = data['last_bar']
        momentum = bar.close > bar.open
        
        # Execute trade if conditions are met
        if sentiment_good and spread_tight and (volume_spike or momentum):
            await self.execute_trade(symbol, bar.close)
    
    async def execute_trade(self, symbol: str, price: float):
        """Execute a trade with MCP-style smart routing"""
        try:
            # Calculate position size
            qty = int(MAX_POSITION_SIZE / price)
            if qty < 1:
                qty = 1
            
            # Use limit order for better fill
            limit_price = price * 1.001  # 0.1% above current
            
            order_data = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.IOC,  # Immediate or cancel
                limit_price=limit_price
            )
            
            order = self.trading_client.submit_order(order_data)
            print(f"[{datetime.now()}] MCP Trade: Bought {qty} shares of {symbol} at limit ${limit_price:.2f}")
            
            # Set up exit orders
            await self.setup_exit_orders(symbol, price, qty)
            
        except Exception as e:
            print(f"Error executing trade for {symbol}: {e}")
    
    async def setup_exit_orders(self, symbol: str, entry_price: float, qty: int):
        """Set up take-profit and stop-loss orders"""
        try:
            # Take profit order
            tp_price = entry_price * (1 + PROFIT_TARGET)
            tp_order = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.GTC,
                limit_price=tp_price
            )
            self.trading_client.submit_order(tp_order)
            
            # Stop loss order
            sl_price = entry_price * (1 - STOP_LOSS)
            sl_order = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.GTC,
                limit_price=sl_price
            )
            self.trading_client.submit_order(sl_order)
            
            print(f"[{datetime.now()}] Exit orders set - TP: ${tp_price:.2f}, SL: ${sl_price:.2f}")
            
        except Exception as e:
            print(f"Error setting exit orders: {e}")

async def main():
    """Main entry point for MCP trader"""
    trader = MCPTrader()
    
    # Update sentiment every 30 minutes
    async def sentiment_updater():
        while True:
            await trader.update_sentiment()
            await trader.setup_data_streams()
            await asyncio.sleep(1800)  # 30 minutes
    
    # Run both the trader and sentiment updater
    await asyncio.gather(
        trader.start(),
        sentiment_updater()
    )

if __name__ == "__main__":
    asyncio.run(main())