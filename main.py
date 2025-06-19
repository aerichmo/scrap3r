#!/usr/bin/env python3
"""
SCRAP3R - Main entry point for the trading bot
"""

import asyncio
import sys
import signal
from datetime import datetime
import logging

from src.config import Settings
from src.utils import setup_logging, SafeShutdown, handle_critical_error
from src.utils.exceptions import ScraperError, TradingError, ConfigError
from src.trading import TradingClient, PositionManager, RiskManager
from src.sentiment import SentimentAnalyzer, RedditScraper
from src.data import StreamHandler
from src.models import Signal, Trade
from src.config import DEFAULT_SYMBOLS


logger = logging.getLogger(__name__)


class Scrap3rBot:
    """Main trading bot application"""
    
    def __init__(self):
        self.trading_client = None
        self.running = False
        
        try:
            # Load and validate settings
            logger.info("Loading configuration...")
            self.settings = Settings()
            self.settings.validate()
            
            # Initialize trading client first (for emergency shutdown)
            logger.info("Initializing trading client...")
            self.trading_client = TradingClient(self.settings)
            
            # Initialize other components
            logger.info("Initializing components...")
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
            
            logger.info("Bot initialization complete")
            
        except Exception as e:
            if self.trading_client:
                logger.error("Initialization failed, attempting to close positions...")
                try:
                    self.trading_client.close_all_positions()
                except:
                    pass
            raise
        
    async def start(self):
        """Start the trading bot"""
        self.running = True
        
        with SafeShutdown("Bot startup", self.trading_client):
            logger.info("=" * 80)
            logger.info("SCRAP3R Trading Bot Starting")
            logger.info(f"Paper Trading: {self.settings.trading.paper_trading}")
            logger.info(f"Profit Target: {self.settings.trading.profit_target:.1%}")
            logger.info(f"Stop Loss: {self.settings.trading.stop_loss:.1%}")
            logger.info(f"Max Positions: {self.settings.trading.max_positions}")
            logger.info("=" * 80)
            
            # Check market conditions
            market_open, reason = self.risk_manager.check_market_conditions()
            if not market_open:
                logger.warning(f"Market check: {reason}")
            
            # Get initial market sentiment
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
            self.position_monitor_task = asyncio.create_task(self.monitor_positions())
            self.sentiment_update_task = asyncio.create_task(self.periodic_sentiment_update())
            
            # Main loop
            logger.info(f"Bot started. Watching {len(self.watched_symbols)} symbols: {sorted(self.watched_symbols)}")
            
            while self.running:
                await asyncio.sleep(60)
                self.log_status()
                
    async def stop(self):
        """Gracefully stop the bot"""
        logger.info("Shutting down bot...")
        self.running = False
        
        # Cancel tasks
        if hasattr(self, 'position_monitor_task'):
            self.position_monitor_task.cancel()
        if hasattr(self, 'sentiment_update_task'):
            self.sentiment_update_task.cancel()
            
        # Close all positions
        if self.trading_client:
            logger.warning("Closing all positions before shutdown...")
            self.trading_client.close_all_positions()
            
        logger.info("Bot shutdown complete")
            
    async def update_market_sentiment(self):
        """Update sentiment from Reddit"""
        logger.info("Updating market sentiment from Reddit...")
        
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
                        
                logger.info(f"Sentiment update complete. Top picks: "
                          f"{sorted(sentiment_data.items(), key=lambda x: x[1]['sentiment'], reverse=True)[:3]}")
            else:
                logger.warning("No Reddit data available, continuing with default symbols")
                
        except Exception as e:
            # Don't crash on sentiment errors - we can still trade with defaults
            logger.error(f"Error updating sentiment (non-critical): {e}")
            
    async def periodic_sentiment_update(self):
        """Periodically update sentiment"""
        while self.running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await self.update_market_sentiment()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic sentiment update: {e}")
                # Continue running - sentiment updates are not critical
            
    async def monitor_positions(self):
        """Monitor positions for exit conditions"""
        while self.running:
            try:
                with SafeShutdown("Position monitoring", self.trading_client):
                    # Update positions from broker
                    self.position_manager.update_positions()
                    
                    # Check exit conditions
                    exits = self.position_manager.check_exit_conditions()
                    
                    for exit_signal in exits:
                        await self.close_position(
                            exit_signal['symbol'], 
                            exit_signal['reason'],
                            exit_signal.get('profit_pct', 0)
                        )
                        
            except asyncio.CancelledError:
                break
            except ScraperError:
                # Re-raise critical errors
                raise
            except Exception as e:
                logger.error(f"Non-critical error in position monitoring: {e}")
                
            await asyncio.sleep(30)
            
    async def handle_signal(self, signal: Signal):
        """Handle trading signals"""
        with SafeShutdown(f"Signal handling for {signal.symbol}", self.trading_client):
            logger.info(f"Processing signal: {signal.symbol} {signal.action} "
                      f"(strength: {signal.strength:.2f}, sentiment: {signal.sentiment_score:.2f})")
            
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
        with SafeShutdown(f"Trade execution for {signal.symbol}", self.trading_client):
            # Get current price (this is simplified - in production, get actual quote)
            if signal.action == 'buy':
                # For now, use a placeholder price
                current_price = 100.0  # This should be fetched from market data
                
                # Calculate position size
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
                position = self.position_manager.get_position(signal.symbol)
                if not position:
                    logger.warning(f"No position to sell for {signal.symbol}")
                    return
                    
                trade = Trade(
                    symbol=signal.symbol,
                    side='sell',
                    quantity=position.quantity,
                    price=position.current_price
                )
                
            # Validate trade
            valid, reason = self.risk_manager.validate_trade(trade)
            if not valid:
                logger.warning(f"Trade validation failed: {reason}")
                return
                
            # Execute trade
            order_id = self.trading_client.place_market_order(trade)
            logger.info(f"Order placed successfully: {order_id}")
            
    async def close_position(self, symbol: str, reason: str, profit_pct: float = 0):
        """Close a position"""
        logger.info(f"Closing position {symbol} due to {reason} (P&L: {profit_pct:.2%})")
        
        success = self.trading_client.close_position(symbol)
        if success:
            logger.info(f"Position {symbol} closed successfully")
        else:
            # This is critical - we failed to close a position that hit stop/target
            raise TradingError(f"Failed to close position {symbol} on {reason}")
            
    def log_status(self):
        """Log current bot status"""
        try:
            positions = self.position_manager.get_total_positions()
            portfolio_value = self.position_manager.get_portfolio_value()
            portfolio_pnl = self.position_manager.get_portfolio_pnl()
            
            if positions > 0:
                logger.info(f"Portfolio Status - Positions: {positions}, "
                          f"Value: ${portfolio_value:,.2f}, "
                          f"Unrealized P&L: ${portfolio_pnl:+,.2f}")
            else:
                logger.info("No open positions")
                
        except Exception as e:
            logger.error(f"Error logging status: {e}")


async def main():
    """Main entry point"""
    bot = None
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.warning(f"Received signal {signum}, initiating shutdown...")
        if bot:
            asyncio.create_task(bot.stop())
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Setup logging
        setup_logging()
        
        logger.info("Starting SCRAP3R Trading Bot...")
        
        # Create and start bot
        bot = Scrap3rBot()
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        if bot:
            await bot.stop()
            
    except ConfigError as e:
        logger.critical(f"Configuration error: {e}")
        sys.exit(1)
        
    except TradingError as e:
        logger.critical(f"Trading error: {e}")
        if bot and bot.trading_client:
            bot.trading_client.close_all_positions()
        sys.exit(1)
        
    except Exception as e:
        handle_critical_error(e, "Main application")


if __name__ == "__main__":
    asyncio.run(main())