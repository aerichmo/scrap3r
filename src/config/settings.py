import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TradingConfig:
    """Trading-specific configuration parameters"""
    profit_target: float = 0.05
    stop_loss: float = 0.02
    max_position_size: float = 100.0
    min_sentiment: float = 0.3
    max_positions: int = 5
    paper_trading: bool = True


@dataclass
class SentimentConfig:
    """Sentiment analysis configuration"""
    min_mentions: int = 3
    reddit_url: str = 'https://www.reddit.com/r/wallstreetbets/hot.json'
    reddit_limit: int = 100
    analysis_window_hours: int = 2


@dataclass
class AlpacaConfig:
    """Alpaca API configuration"""
    api_key: str
    api_secret: str
    base_url: str = "https://paper-api.alpaca.markets"
    data_url: str = "https://data.alpaca.markets"


class Settings:
    """Main application settings"""
    
    def __init__(self):
        # Load from environment
        self.alpaca = AlpacaConfig(
            api_key=os.environ.get('ALPACA_KEY', ''),
            api_secret=os.environ.get('ALPACA_SECRET', '')
        )
        
        self.trading = TradingConfig()
        self.sentiment = SentimentConfig()
        
        # Application settings
        self.debug = os.environ.get('DEBUG', 'False').lower() == 'true'
        self.log_level = os.environ.get('LOG_LEVEL', 'INFO')
        
    def validate(self):
        """Validate configuration settings"""
        if not self.alpaca.api_key or not self.alpaca.api_secret:
            raise ValueError("Alpaca API credentials not set")
            
        if self.trading.profit_target <= 0 or self.trading.profit_target >= 1:
            raise ValueError("Profit target must be between 0 and 1")
            
        if self.trading.stop_loss <= 0 or self.trading.stop_loss >= 1:
            raise ValueError("Stop loss must be between 0 and 1")
            
        return True