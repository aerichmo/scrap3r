import os
from dataclasses import dataclass
from typing import List, Optional

from ..utils.exceptions import ConfigError


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
        try:
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
            
        except Exception as e:
            raise ConfigError(f"Failed to initialize settings: {str(e)}")
        
    def validate(self):
        """Validate configuration settings"""
        errors = []
        
        # Validate Alpaca credentials
        if not self.alpaca.api_key:
            errors.append("ALPACA_KEY environment variable not set")
        if not self.alpaca.api_secret:
            errors.append("ALPACA_SECRET environment variable not set")
            
        # Validate trading parameters
        if not 0 < self.trading.profit_target < 1:
            errors.append(f"Invalid profit_target: {self.trading.profit_target} (must be between 0 and 1)")
            
        if not 0 < self.trading.stop_loss < 1:
            errors.append(f"Invalid stop_loss: {self.trading.stop_loss} (must be between 0 and 1)")
            
        if self.trading.max_position_size <= 0:
            errors.append(f"Invalid max_position_size: {self.trading.max_position_size} (must be positive)")
            
        if self.trading.max_positions <= 0:
            errors.append(f"Invalid max_positions: {self.trading.max_positions} (must be positive)")
            
        if not 0 <= self.trading.min_sentiment <= 1:
            errors.append(f"Invalid min_sentiment: {self.trading.min_sentiment} (must be between 0 and 1)")
            
        # Validate sentiment parameters
        if self.sentiment.min_mentions <= 0:
            errors.append(f"Invalid min_mentions: {self.sentiment.min_mentions} (must be positive)")
            
        if self.sentiment.analysis_window_hours <= 0:
            errors.append(f"Invalid analysis_window_hours: {self.sentiment.analysis_window_hours} (must be positive)")
            
        # Raise all errors at once
        if errors:
            raise ConfigError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
            
        return True