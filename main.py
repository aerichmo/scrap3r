#!/usr/bin/env python3
"""
SCRAP3R - Main entry point for the trading bot
"""

import asyncio
import sys
from datetime import datetime
import logging

from src.config import Settings
from src.utils import setup_logging
from src.trading import TradingClient, PositionManager, RiskManager
from src.sentiment import SentimentAnalyzer, RedditScraper
from src.data import StreamHandler
from src.models import Signal, Trade
from src.config import DEFAULT_SYMBOLS


logger = logging.getLogger(__name__)


class Scrap3rBot:
    """Main trading bot application"""
    
    def __init__(self):
        # Load and validate settings
        self.settings = Settings()
        self.settings.validate()
        
        # Initialize components
        self.trading_client = TradingClient(self.settings)
        self.position_manager = PositionManager(self.settings, self.trading_client)
        self.risk_manager = RiskManager(self.settings, self.trading_client)
        self.sentiment_analyzer = SentimentAnalyzer()
        self.reddit_scraper = RedditScraper(self.settings)
        
        # Data tracking
        self.symbol_data = {}
        self.watched_symbols = set(DEFAULT_SYMBOLS)
        
        # Stream handler
        self.stream_handler = StreamHandler(
            self.trading_client.data_stream,
            self.symbol_data
        )
        self.stream_handler.add_signal_callback(self.handle_signal)
        
    async def start(self):
        """Start the trading bot"""
        logger.info("Starting SCRAP3R Trading Bot")
        
        # Get market sentiment
        await self.update_market_sentiment()
        
        # Initialize symbol data
        for symbol in self.watched_symbols:
            self.symbol_data[symbol] = {
                'sentiment': 0.5,
                'mentions': 1,
                'last_update': datetime.now()
            }
            
        # Subscribe to real-time data
        await self.stream_handler.subscribe_symbols(self.watched_symbols)
        
        # Start monitoring tasks
        asyncio.create_task(self.monitor_positions())
        asyncio.create_task(self.periodic_sentiment_update())
        
        # Keep running
        logger.info(f"Bot started. Watching {len(self.watched_symbols)} symbols")
        while True:
            await asyncio.sleep(60)
            self.log_status()
            
    async def update_market_sentiment(self):
        """Update sentiment from Reddit"""
        logger.info("Updating market sentiment from Reddit")
        
        try:
            # Get Reddit chatter
            texts = self.reddit_scraper.get_market_chatter()
            
            if texts:
                # Analyze sentiment
                sentiment_data = self.sentiment_analyzer.aggregate_sentiment(texts)
                
                # Update watched symbols
                new_symbols = set()
                for ticker, data in sentiment_data.items():
                    if data['mentions'] >= self.settings.sentiment.min_mentions:
                        new_symbols.add(ticker)
                        
                        # Update symbol data
                        if ticker not in self.symbol_data:
                            self.symbol_data[ticker] = {}
                            
                        self.symbol_data[ticker].update({
                            'sentiment': data['sentiment'],
                            'mentions': data['mentions'],
                            'last_update': datetime.now()
                        })
                        
                # Add new symbols (up to limit)
                if new_symbols:
                    current_count = len(self.watched_symbols)
                    available_slots = 30 - current_count  # WebSocket limit
                    
                    if available_slots > 0:
                        # Sort by mentions and add top symbols
                        sorted_symbols = sorted(
                            new_symbols - self.watched_symbols,
                            key=lambda s: sentiment_data[s]['mentions'],
                            reverse=True
                        )[:available_slots]
                        
                        self.watched_symbols.update(sorted_symbols)
                        logger.info(f"Added {len(sorted_symbols)} new symbols to watchlist")
                        
            else:
                logger.warning("No Reddit data available, using default symbols")
                
        except Exception as e:
            logger.error(f"Error updating sentiment: {e}")
            
    async def periodic_sentiment_update(self):
        """Periodically update sentiment"""
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            await self.update_market_sentiment()
            
    async def monitor_positions(self):
        """Monitor positions for exit conditions"""
        while True:
            try:
                # Update positions from broker
                self.position_manager.update_positions()
                
                # Check exit conditions
                exits = self.position_manager.check_exit_conditions()
                
                for exit_signal in exits:
                    await self.close_position(exit_signal['symbol'], exit_signal['reason'])
                    
            except Exception as e:
                logger.error(f"Error monitoring positions: {e}")
                
            await asyncio.sleep(30)
            
    async def handle_signal(self, signal: Signal):
        """Handle trading signals"""
        logger.info(f"Processing signal: {signal}")
        
        # Check if we can open new position
        if signal.action == 'buy':
            if not self.position_manager.can_open_new_position():
                logger.warning("Maximum positions reached, skipping signal")
                return
                
            if self.position_manager.has_position(signal.symbol):
                logger.info(f"Already have position in {signal.symbol}, skipping")
                return
                
        # Execute trade
        await self.execute_trade(signal)
        
    async def execute_trade(self, signal: Signal):
        """Execute a trade based on signal"""
        try:
            # Get current price
            position = self.trading_client.get_position(signal.symbol)
            if signal.action == 'buy':
                # Calculate position size
                account = self.trading_client.get_account()
                current_price = float(account.last_equity)  # Rough estimate
                quantity = self.risk_manager.calculate_position_size(
                    signal.symbol, 
                    current_price
                )
                
                # Create trade
                trade = Trade(
                    symbol=signal.symbol,
                    side='buy',
                    quantity=quantity,
                    price=current_price
                )
                
            else:  # sell
                if not position:
                    logger.warning(f"No position to sell for {signal.symbol}")
                    return
                    
                trade = Trade(
                    symbol=signal.symbol,
                    side='sell',
                    quantity=position.qty,
                    price=float(position.current_price)
                )
                
            # Validate trade
            valid, reason = self.risk_manager.validate_trade(trade)
            if not valid:
                logger.warning(f"Trade validation failed: {reason}")
                return
                
            # Execute trade
            order_id = self.trading_client.place_market_order(trade)
            if order_id:
                logger.info(f"Trade executed: {trade}")
            else:
                logger.error(f"Failed to execute trade: {trade}")
                
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            
    async def close_position(self, symbol: str, reason: str):
        """Close a position"""
        logger.info(f"Closing position {symbol} due to {reason}")
        
        success = self.trading_client.close_position(symbol)
        if success:
            logger.info(f"Position {symbol} closed successfully")
        else:
            logger.error(f"Failed to close position {symbol}")
            
    def log_status(self):
        """Log current bot status"""
        positions = self.position_manager.get_total_positions()
        portfolio_value = self.position_manager.get_portfolio_value()
        portfolio_pnl = self.position_manager.get_portfolio_pnl()
        
        logger.info(f"Status - Positions: {positions}, "
                   f"Value: ${portfolio_value:.2f}, "
                   f"P&L: ${portfolio_pnl:.2f}")


async def main():
    """Main entry point"""
    # Setup logging
    setup_logging()
    
    try:
        # Create and start bot
        bot = Scrap3rBot()
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())