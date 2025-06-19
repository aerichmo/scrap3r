#!/usr/bin/env python3
"""
Run the sentiment-based scraper (for scheduled execution)
"""

import sys
from datetime import datetime
import logging

from src.config import Settings
from src.utils import setup_logging, SafeShutdown, handle_critical_error
from src.utils.exceptions import ConfigError, TradingError
from src.trading import TradingClient, RiskManager
from src.sentiment import SentimentAnalyzer, RedditScraper
from src.models import Trade


logger = logging.getLogger(__name__)


def main():
    """Run the scraper and execute trades based on sentiment"""
    # Setup logging
    setup_logging()
    
    logger.info("=" * 80)
    logger.info("SCRAP3R Sentiment Scanner Starting")
    logger.info(f"Time: {datetime.now()}")
    logger.info("=" * 80)
    
    trading_client = None
    
    try:
        # Initialize components
        logger.info("Loading configuration...")
        settings = Settings()
        settings.validate()
        
        logger.info("Initializing trading client...")
        trading_client = TradingClient(settings)
        
        with SafeShutdown("Sentiment scanner", trading_client):
            risk_manager = RiskManager(settings, trading_client)
            sentiment_analyzer = SentimentAnalyzer()
            reddit_scraper = RedditScraper(settings)
            
            # Check market conditions
            market_open, reason = risk_manager.check_market_conditions()
            if not market_open:
                logger.warning(f"Market check: {reason}")
                logger.info("Exiting - market conditions not suitable")
                return
            
            # Get Reddit chatter
            logger.info("Scraping Reddit for market sentiment...")
            texts = reddit_scraper.get_market_chatter()
            
            if not texts:
                logger.warning("No Reddit data collected, exiting")
                return
                
            # Analyze sentiment
            logger.info("Analyzing sentiment...")
            sentiment_data = sentiment_analyzer.aggregate_sentiment(texts)
            
            # Filter for high-mention, positive sentiment stocks
            trade_candidates = []
            for ticker, data in sentiment_data.items():
                if (data['mentions'] >= settings.sentiment.min_mentions and 
                    data['sentiment'] >= settings.trading.min_sentiment):
                    trade_candidates.append({
                        'symbol': ticker,
                        'sentiment': data['sentiment'],
                        'mentions': data['mentions']
                    })
                    
            # Sort by sentiment score
            trade_candidates.sort(key=lambda x: x['sentiment'], reverse=True)
            
            logger.info(f"Found {len(trade_candidates)} trade candidates: "
                       f"{[c['symbol'] for c in trade_candidates[:5]]}")
            
            if not trade_candidates:
                logger.info("No stocks meet criteria, exiting")
                return
            
            # Check existing positions
            positions = trading_client.get_positions()
            current_symbols = {p.symbol for p in positions}
            logger.info(f"Current positions: {current_symbols or 'None'}")
            
            # Execute trades
            trades_executed = 0
            for candidate in trade_candidates:
                symbol = candidate['symbol']
                
                # Skip if we already have position
                if symbol in current_symbols:
                    logger.info(f"Already have position in {symbol}, skipping")
                    continue
                    
                # Check if we can open new position
                if len(positions) + trades_executed >= settings.trading.max_positions:
                    logger.info("Maximum positions reached")
                    break
                    
                # Execute trade
                try:
                    # Get quote (simplified - should get actual market price)
                    price = 100.0  # Placeholder
                    
                    # Calculate position size
                    quantity = risk_manager.calculate_position_size(symbol, price)
                    
                    # Create trade
                    trade = Trade(
                        symbol=symbol,
                        side='buy',
                        quantity=quantity,
                        price=price
                    )
                    
                    # Validate and execute
                    valid, reason = risk_manager.validate_trade(trade)
                    if valid:
                        order_id = trading_client.place_market_order(trade)
                        logger.info(f"SUCCESS: Bought {quantity} shares of {symbol} "
                                   f"(sentiment: {candidate['sentiment']:.2f}, "
                                   f"mentions: {candidate['mentions']}) "
                                   f"Order ID: {order_id}")
                        trades_executed += 1
                    else:
                        logger.warning(f"Trade validation failed for {symbol}: {reason}")
                        
                except Exception as e:
                    logger.error(f"Failed to execute trade for {symbol}: {e}")
                    # Continue with other candidates
                    
            logger.info(f"Sentiment scanner completed. Trades executed: {trades_executed}")
            
    except ConfigError as e:
        logger.critical(f"Configuration error: {e}")
        sys.exit(1)
        
    except TradingError as e:
        logger.critical(f"Trading error: {e}")
        if trading_client:
            trading_client.close_all_positions()
        sys.exit(1)
        
    except Exception as e:
        handle_critical_error(e, "Sentiment scanner")


if __name__ == "__main__":
    main()