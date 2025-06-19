import asyncio
from typing import Set, Callable
from alpaca.data.models import Bar, Trade, Quote
import logging

from ..models import Signal


logger = logging.getLogger(__name__)


class StreamHandler:
    """Handles real-time data streams"""
    
    def __init__(self, data_stream, symbol_data: dict):
        self.data_stream = data_stream
        self.symbol_data = symbol_data
        self.signal_callbacks: list[Callable] = []
        self._websocket_started = False
        
    def add_signal_callback(self, callback: Callable):
        """Add callback for trading signals"""
        self.signal_callbacks.append(callback)
        
    async def subscribe_symbols(self, symbols: Set[str]):
        """Subscribe to real-time data for symbols"""
        if not symbols or self._websocket_started:
            return
            
        logger.info(f"Subscribing to data streams for: {symbols}")
        
        # Subscribe handlers
        async def handle_quote(data):
            await self.on_quote(data)
            
        async def handle_trade(data):
            await self.on_trade(data)
            
        async def handle_bar(data):
            await self.on_bar(data)
        
        # Subscribe to data
        self.data_stream.subscribe_quotes(handle_quote, *symbols)
        self.data_stream.subscribe_trades(handle_trade, *symbols)
        self.data_stream.subscribe_bars(handle_bar, *symbols)
        
        # Start websocket if not already running
        if not self._websocket_started:
            self._websocket_started = True
            asyncio.create_task(self._run_websocket())
            
    async def _run_websocket(self):
        """Run websocket in background"""
        try:
            await self.data_stream._run_forever()
        except Exception as e:
            logger.error(f"Websocket error: {e}")
            self._websocket_started = False
            
    async def on_quote(self, quote: Quote):
        """Handle quote updates"""
        symbol = quote.symbol
        
        if symbol not in self.symbol_data:
            return
            
        # Update spread data
        spread = quote.ask_price - quote.bid_price
        spread_pct = spread / quote.bid_price if quote.bid_price > 0 else 1
        
        self.symbol_data[symbol]['spread'] = spread_pct
        self.symbol_data[symbol]['last_quote'] = quote
        
    async def on_trade(self, trade: Trade):
        """Handle trade updates"""
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
        """Handle bar updates"""
        symbol = bar.symbol
        
        if symbol not in self.symbol_data:
            return
            
        logger.info(f"Bar for {symbol}: ${bar.close:.2f} Vol:{bar.volume}")
        
        # Store the bar
        self.symbol_data[symbol]['last_bar'] = bar
        
        # Check for signals
        signal = self.check_for_signal(symbol, bar)
        if signal and signal.is_actionable():
            await self.emit_signal(signal)
            
    def check_for_signal(self, symbol: str, bar: Bar) -> Signal:
        """Check if bar data generates a trading signal"""
        data = self.symbol_data.get(symbol, {})
        
        # Simple momentum check
        momentum_signal = bar.close > bar.open and bar.volume > 1000000
        
        # Get sentiment score
        sentiment = data.get('sentiment', 0.5)
        mentions = data.get('mentions', 0)
        
        # Combine signals
        if momentum_signal and sentiment > 0.3:
            strength = min(1.0, sentiment + 0.2)  # Boost strength for momentum
            return Signal(
                symbol=symbol,
                action='buy',
                strength=strength,
                source='momentum',
                sentiment_score=sentiment,
                mentions=mentions,
                reason=f"Positive momentum with {bar.volume:,} volume"
            )
            
        return None
        
    async def emit_signal(self, signal: Signal):
        """Emit trading signal to callbacks"""
        logger.info(f"Signal generated: {signal.symbol} {signal.action} "
                   f"(strength: {signal.strength:.2f})")
        
        for callback in self.signal_callbacks:
            try:
                await callback(signal)
            except Exception as e:
                logger.error(f"Error in signal callback: {e}")