"""
Custom exceptions for SCRAP3R with fail-safe shutdown
"""

import sys
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Base exception for all SCRAP3R errors"""
    
    def __init__(self, message: str, critical: bool = True):
        super().__init__(message)
        self.message = message
        self.critical = critical
        
        if critical:
            logger.critical(f"CRITICAL ERROR: {message}")
            logger.critical("Initiating emergency shutdown to protect capital")
        else:
            logger.error(f"ERROR: {message}")


class TradingError(ScraperError):
    """Trading-specific errors - always critical"""
    
    def __init__(self, message: str):
        super().__init__(message, critical=True)


class APIError(ScraperError):
    """API communication errors"""
    pass


class ConfigError(ScraperError):
    """Configuration errors - always critical"""
    
    def __init__(self, message: str):
        super().__init__(message, critical=True)


class DataError(ScraperError):
    """Data processing errors"""
    pass


class PositionError(ScraperError):
    """Position management errors - always critical"""
    
    def __init__(self, message: str):
        super().__init__(message, critical=True)


class RiskError(ScraperError):
    """Risk management errors - always critical"""
    
    def __init__(self, message: str):
        super().__init__(message, critical=True)


def handle_critical_error(error: Exception, context: str = ""):
    """
    Handle critical errors by logging and shutting down safely
    """
    logger.critical("=" * 80)
    logger.critical("CRITICAL ERROR - EMERGENCY SHUTDOWN")
    logger.critical("=" * 80)
    logger.critical(f"Context: {context}")
    logger.critical(f"Error Type: {type(error).__name__}")
    logger.critical(f"Error Message: {str(error)}")
    logger.critical("=" * 80)
    
    # Log full traceback
    import traceback
    logger.critical("Full traceback:")
    logger.critical(traceback.format_exc())
    
    logger.critical("Shutting down to protect capital...")
    
    # Exit with error code
    sys.exit(1)


class SafeShutdown:
    """
    Context manager for safe shutdown on errors
    """
    
    def __init__(self, context: str, trading_client=None):
        self.context = context
        self.trading_client = trading_client
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Try to close all positions before shutdown
            if self.trading_client:
                try:
                    logger.warning("Attempting to close all positions before shutdown...")
                    self.trading_client.close_all_positions()
                    logger.warning("All positions closed successfully")
                except Exception as e:
                    logger.error(f"Failed to close positions: {e}")
                    
            # Handle the error and shutdown
            handle_critical_error(exc_val, self.context)
            
        return False  # Don't suppress the exception