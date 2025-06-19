import os
import json
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List
import aiohttp
from alpaca.trading.client import TradingClient
from alpaca.data.live import StockDataStream
from alpaca.data.models import Bar, Trade, Quote
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

ALPACA_KEY = os.environ.get('ALPACA_KEY')
ALPACA_SECRET = os.environ.get('ALPACA_SECRET')

# Trading parameters
PROFIT_TARGET = 0.05
STOP_LOSS = 0.02
MAX_POSITION_SIZE = 100
MIN_SENTIMENT = 0.3

# Default watchlist if Reddit scraping fails
DEFAULT_SYMBOLS = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA']

class MCPTrader:
    def __init__(self):
        self.trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)
        self.data_stream = StockDataStream(ALPACA_KEY, ALPACA_SECRET)
        self.watched_symbols = set(DEFAULT_SYMBOLS)
        self.symbol_data = {}
        self._websocket_started = False
        
    async def start(self):
        """Initialize the MCP trading system"""
        print(f"[{datetime.now()}] Starting MCP Trader...")
        print(f"[{datetime.now()}] Using default symbols: {self.watched_symbols}")
        
        # Initialize symbol data
        for symbol in self.watched_symbols:
            self.symbol_data[symbol] = {
                'sentiment': 0.5,  # Neutral default
                'mentions': 1,
                'last_update': datetime.now()
            }
        
        # Subscribe to real-time data
        await self.setup_data_streams()
        
        # Start monitoring positions
        asyncio.create_task(self.monitor_positions())
        
        # Keep the connection alive
        while True:
            await asyncio.sleep(60)
            print(f"[{datetime.now()}] MCP Trader running... Watching: {self.watched_symbols}")
    
    async def setup_data_streams(self):
        """Subscribe to real-time data streams"""
        if not self.watched_symbols or self._websocket_started:
            return
            
        print(f"[{datetime.now()}] Setting up data streams for: {self.watched_symbols}")
        
        # Subscribe handlers
        async def handle_quote(data):
            await self.on_quote(data)
            
        async def handle_trade(data):
            await self.on_trade(data)
            
        async def handle_bar(data):
            await self.on_bar(data)
        
        # Subscribe to data
        self.data_stream.subscribe_quotes(handle_quote, *self.watched_symbols)
        self.data_stream.subscribe_trades(handle_trade, *self.watched_symbols)
        self.data_stream.subscribe_bars(handle_bar, *self.watched_symbols)
        
        # Start the websocket in background
        if not self._websocket_started:
            self._websocket_started = True
            asyncio.create_task(self._run_websocket())
    
    async def _run_websocket(self):
        """Run websocket in background"""
        try:
            await self.data_stream._run_forever()
        except Exception as e:
            print(f"[{datetime.now()}] Websocket error: {e}")
            self._websocket_started = False
    
    async def monitor_positions(self):
        """Monitor existing positions for exit conditions"""
        while True:
            try:
                positions = self.trading_client.get_all_positions()
                
                for position in positions:
                    current_price = float(position.current_price)
                    avg_price = float(position.avg_entry_price)
                    profit_pct = (current_price - avg_price) / avg_price
                    
                    # Check exit conditions
                    if profit_pct >= PROFIT_TARGET:
                        print(f"[{datetime.now()}] Taking profit on {position.symbol} at {profit_pct:.2%}")
                        await self.close_position(position)
                    elif profit_pct <= -STOP_LOSS:
                        print(f"[{datetime.now()}] Stop loss on {position.symbol} at {profit_pct:.2%}")
                        await self.close_position(position)
                        
            except Exception as e:
                print(f"[{datetime.now()}] Error monitoring positions: {e}")
                
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def close_position(self, position):
        """Close a position"""
        try:
            order = MarketOrderRequest(
                symbol=position.symbol,
                qty=position.qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            self.trading_client.submit_order(order)
        except Exception as e:
            print(f"Error closing position: {e}")
    
    async def on_quote(self, quote: Quote):
        """Handle real-time quote updates"""
        symbol = quote.symbol
        
        if symbol not in self.symbol_data:
            return
            
        # Update spread data
        spread = quote.ask_price - quote.bid_price
        spread_pct = spread / quote.bid_price if quote.bid_price > 0 else 1
        
        self.symbol_data[symbol]['spread'] = spread_pct
        self.symbol_data[symbol]['last_quote'] = quote
    
    async def on_trade(self, trade: Trade):
        """Handle real-time trade data"""
        symbol = trade.symbol
        
        if symbol not in self.symbol_data:
            return
            
        # Track recent trades
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
    
    async def on_bar(self, bar: Bar):
        """Handle real-time bar data"""
        symbol = bar.symbol
        
        if symbol not in self.symbol_data:
            return
            
        print(f"[{datetime.now()}] Bar for {symbol}: ${bar.close:.2f} Vol:{bar.volume}")
        
        # Store the bar
        self.symbol_data[symbol]['last_bar'] = bar
        
        # Check if we should enter
        await self.check_entry_conditions(symbol)
    
    async def check_entry_conditions(self, symbol: str):
        """Simple entry logic for testing"""
        # Skip if we already have a position
        try:
            positions = self.trading_client.get_all_positions()
            if any(p.symbol == symbol for p in positions):
                return
        except:
            return
            
        data = self.symbol_data.get(symbol, {})
        bar = data.get('last_bar')
        
        if not bar:
            return
            
        # Simple momentum check
        if bar.close > bar.open and bar.volume > 1000000:
            print(f"[{datetime.now()}] Momentum detected for {symbol}")
            await self.execute_trade(symbol, bar.close)
    
    async def execute_trade(self, symbol: str, price: float):
        """Execute a trade"""
        try:
            qty = int(MAX_POSITION_SIZE / price)
            if qty < 1:
                qty = 1
            
            order = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            
            result = self.trading_client.submit_order(order)
            print(f"[{datetime.now()}] Bought {qty} shares of {symbol} at ~${price:.2f}")
            
        except Exception as e:
            print(f"Error executing trade for {symbol}: {e}")

async def main():
    """Main entry point"""
    trader = MCPTrader()
    await trader.start()

if __name__ == "__main__":
    # Run the trader
    asyncio.run(main())