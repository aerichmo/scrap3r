from alpaca.trading.client import TradingClient as AlpacaTradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.live import StockDataStream
from typing import Optional, List, Dict
import logging

from ..config import Settings
from ..models.trade import Trade
from ..utils.exceptions import TradingError, APIError


logger = logging.getLogger(__name__)


class TradingClient:
    """Wrapper for Alpaca trading functionality"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        try:
            self.client = AlpacaTradingClient(
                settings.alpaca.api_key,
                settings.alpaca.api_secret,
                paper=settings.trading.paper_trading
            )
            self.data_stream = StockDataStream(
                settings.alpaca.api_key,
                settings.alpaca.api_secret
            )
            
            # Test connection
            account = self.client.get_account()
            logger.info(f"Connected to Alpaca - Account: {account.account_number}, "
                       f"Buying Power: ${float(account.buying_power):,.2f}")
                       
        except Exception as e:
            raise TradingError(f"Failed to initialize Alpaca client: {str(e)}")
        
    def get_account(self):
        """Get account information"""
        try:
            return self.client.get_account()
        except Exception as e:
            raise APIError(f"Failed to get account info: {str(e)}")
        
    def get_positions(self):
        """Get all positions"""
        try:
            return self.client.get_all_positions()
        except Exception as e:
            raise APIError(f"Failed to get positions: {str(e)}")
        
    def get_position(self, symbol: str):
        """Get position for specific symbol"""
        try:
            return self.client.get_position(symbol)
        except Exception as e:
            # Position not found is not critical
            logger.debug(f"No position found for {symbol}: {e}")
            return None
            
    def place_market_order(self, trade: Trade) -> str:
        """Place a market order"""
        try:
            order_request = MarketOrderRequest(
                symbol=trade.symbol,
                qty=trade.quantity,
                side=OrderSide.BUY if trade.side == 'buy' else OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            
            order = self.client.submit_order(order_request)
            logger.info(f"Market order placed: {trade.symbol} {trade.side} {trade.quantity} - Order ID: {order.id}")
            return order.id
            
        except Exception as e:
            raise TradingError(f"Failed to place market order for {trade.symbol}: {str(e)}")
            
    def place_limit_order(self, trade: Trade, limit_price: float) -> str:
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
            logger.info(f"Limit order placed: {trade.symbol} {trade.side} {trade.quantity} @ ${limit_price} - Order ID: {order.id}")
            return order.id
            
        except Exception as e:
            raise TradingError(f"Failed to place limit order for {trade.symbol}: {str(e)}")
            
    def close_position(self, symbol: str) -> bool:
        """Close a position"""
        try:
            self.client.close_position(symbol)
            logger.info(f"Position closed: {symbol}")
            return True
        except Exception as e:
            # Log but don't crash - position might already be closed
            logger.error(f"Failed to close position {symbol}: {e}")
            return False
            
    def close_all_positions(self) -> bool:
        """Close all positions - used in emergency shutdown"""
        try:
            positions = self.get_positions()
            if not positions:
                logger.info("No positions to close")
                return True
                
            logger.warning(f"Closing {len(positions)} positions...")
            self.client.close_all_positions()
            logger.info("All positions closed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close all positions: {e}")
            # Try to close individually
            try:
                positions = self.get_positions()
                for position in positions:
                    try:
                        self.close_position(position.symbol)
                    except Exception as pe:
                        logger.error(f"Failed to close {position.symbol}: {pe}")
            except:
                pass
            return False