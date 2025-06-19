#!/usr/bin/env python3
"""
Run the sentiment-based scraper (for scheduled execution)
"""

import sys
from datetime import datetime
import logging

from src.config import Settings
from src.utils import setup_logging
from src.trading import TradingClient, RiskManager
from src.sentiment import SentimentAnalyzer, RedditScraper
from src.models import Trade


logger = logging.getLogger(__name__)


def main():
    """Run the scraper and execute trades based on sentiment"""
    # Setup logging
    setup_logging()
    
    logger.info("Starting SCRAP3R sentiment scanner")
    
    try:
        # Initialize components
        settings = Settings()
        settings.validate()
        
        trading_client = TradingClient(settings)
        risk_manager = RiskManager(settings, trading_client)
        sentiment_analyzer = SentimentAnalyzer()
        reddit_scraper = RedditScraper(settings)
        
        # Get Reddit chatter
        logger.info("Scraping Reddit for market sentiment...")
        texts = reddit_scraper.get_market_chatter()
        
        if not texts:
            logger.warning("No Reddit data collected")
            return
            
        # Analyze sentiment
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
        
        logger.info(f"Found {len(trade_candidates)} trade candidates")
        
        # Check existing positions
        positions = trading_client.get_positions()
        current_symbols = {p.symbol for p in positions}
        
        # Execute trades
        for candidate in trade_candidates:
            symbol = candidate['symbol']
            
            # Skip if we already have position
            if symbol in current_symbols:
                logger.info(f"Already have position in {symbol}, skipping")
                continue
                
            # Check if we can open new position
            if len(positions) >= settings.trading.max_positions:
                logger.info("Maximum positions reached")
                break
                
            # Get quote
            try:
                account = trading_client.get_account()
                # This is simplified - in production, get actual quote
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
                    if order_id:
                        logger.info(f"Bought {quantity} shares of {symbol} "
                                   f"(sentiment: {candidate['sentiment']:.2f}, "
                                   f"mentions: {candidate['mentions']})")
                        positions.append(None)  # Track that we opened a position
                else:
                    logger.warning(f"Trade validation failed for {symbol}: {reason}")
                    
            except Exception as e:
                logger.error(f"Error trading {symbol}: {e}")
                
        logger.info("Sentiment scanner completed")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()