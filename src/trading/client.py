from alpaca.trading.client import TradingClient as AlpacaTradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.live import StockDataStream
from typing import Optional, List, Dict
import logging

from ..config import Settings
from ..models.trade import Trade


logger = logging.getLogger(__name__)


class TradingClient:
    """Wrapper for Alpaca trading functionality"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AlpacaTradingClient(
            settings.alpaca.api_key,
            settings.alpaca.api_secret,
            paper=settings.trading.paper_trading
        )
        self.data_stream = StockDataStream(
            settings.alpaca.api_key,
            settings.alpaca.api_secret
        )
        
    def get_account(self):
        """Get account information"""
        return self.client.get_account()
        
    def get_positions(self):
        """Get all positions"""
        return self.client.get_all_positions()
        
    def get_position(self, symbol: str):
        """Get position for specific symbol"""
        try:
            return self.client.get_position(symbol)
        except:
            return None
            
    def place_market_order(self, trade: Trade) -> Optional[str]:
        """Place a market order"""
        try:
            order_request = MarketOrderRequest(
                symbol=trade.symbol,
                qty=trade.quantity,
                side=OrderSide.BUY if trade.side == 'buy' else OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            
            order = self.client.submit_order(order_request)
            logger.info(f"Market order placed: {trade.symbol} {trade.side} {trade.quantity}")
            return order.id
            
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None
            
    def place_limit_order(self, trade: Trade, limit_price: float) -> Optional[str]:
        """Place a limit order"""
        try:
            order_request = LimitOrderRequest(
                symbol=trade.symbol,
                qty=trade.quantity,
                side=OrderSide.BUY if trade.side == 'buy' else OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price
            )
            
            order = self.client.submit_order(order_request)
            logger.info(f"Limit order placed: {trade.symbol} {trade.side} {trade.quantity} @ {limit_price}")
            return order.id
            
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            return None
            
    def close_position(self, symbol: str) -> bool:
        """Close a position"""
        try:
            self.client.close_position(symbol)
            logger.info(f"Position closed: {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")
            return False
            
    def close_all_positions(self) -> bool:
        """Close all positions"""
        try:
            self.client.close_all_positions()
            logger.info("All positions closed")
            return True
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            return False