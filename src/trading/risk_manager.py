from typing import Optional, Tuple
import logging

from ..config import Settings
from ..models.trade import Trade
from ..utils.exceptions import RiskError, APIError


logger = logging.getLogger(__name__)


class RiskManager:
    """Manages trading risk and position sizing"""
    
    def __init__(self, settings: Settings, trading_client):
        self.settings = settings
        self.trading_client = trading_client
        
    def calculate_position_size(self, symbol: str, price: float) -> int:
        """Calculate position size based on account value and risk parameters"""
        try:
            account = self.trading_client.get_account()
            account_value = float(account.portfolio_value)
            buying_power = float(account.buying_power)
            
            # Validate account state
            if account_value <= 0:
                raise RiskError("Account value is zero or negative")
                
            if buying_power <= 0:
                raise RiskError("No buying power available")
                
            # Maximum position size as percentage of account
            max_position_value = min(
                self.settings.trading.max_position_size,
                account_value * 0.1,  # Max 10% per position
                buying_power * 0.9  # Leave 10% buffer
            )
            
            # Validate price
            if price <= 0:
                raise RiskError(f"Invalid price for {symbol}: ${price}")
                
            # Calculate shares
            shares = int(max_position_value / price)
            
            # Ensure at least 1 share but respect limits
            if shares < 1:
                logger.warning(f"Position size too small for {symbol} at ${price:.2f}")
                return 1
                
            logger.info(f"Position size for {symbol}: {shares} shares at ${price:.2f} = ${shares * price:.2f}")
            return shares
            
        except APIError:
            raise
        except RiskError:
            raise
        except Exception as e:
            raise RiskError(f"Failed to calculate position size: {str(e)}")
            
    def validate_trade(self, trade: Trade) -> Tuple[bool, Optional[str]]:
        """Validate a trade against risk rules"""
        try:
            # Validate trade object
            if trade.quantity <= 0:
                return False, f"Invalid quantity: {trade.quantity}"
                
            if trade.price <= 0:
                return False, f"Invalid price: ${trade.price}"
                
            if trade.side not in ['buy', 'sell']:
                return False, f"Invalid side: {trade.side}"
                
            account = self.trading_client.get_account()
            
            # Check if account is restricted
            if account.trading_blocked:
                raise RiskError("Account trading is blocked by broker")
                
            # Check day trading status
            if account.pattern_day_trader and int(account.daytrade_count) >= 3:
                logger.warning("Approaching day trade limit")
                
            # Check if we have sufficient buying power
            if trade.side == 'buy':
                required_capital = trade.quantity * trade.price
                buying_power = float(account.buying_power)
                
                if required_capital > buying_power:
                    return False, f"Insufficient buying power: ${buying_power:.2f} < ${required_capital:.2f}"
                    
                # Check margin requirements
                if required_capital > buying_power * 0.9:
                    return False, "Trade would use >90% of buying power"
                    
            # Check if we already have a position (for buys)
            if trade.side == 'buy':
                position = self.trading_client.get_position(trade.symbol)
                if position:
                    return False, f"Already have position in {trade.symbol}"
                    
            # Check position limits
            if trade.side == 'buy':
                positions = self.trading_client.get_positions()
                if len(positions) >= self.settings.trading.max_positions:
                    return False, f"Maximum positions reached ({self.settings.trading.max_positions})"
                
            # All checks passed
            logger.info(f"Trade validated: {trade.symbol} {trade.side} {trade.quantity} @ ${trade.price:.2f}")
            return True, None
            
        except (APIError, RiskError):
            raise
        except Exception as e:
            raise RiskError(f"Trade validation failed: {str(e)}")
            
    def check_market_conditions(self) -> Tuple[bool, Optional[str]]:
        """Check if market conditions are suitable for trading"""
        try:
            account = self.trading_client.get_account()
            
            # Check if market is open
            if not account.trading_blocked:  # This is a proxy check
                return True, None
            else:
                return False, "Market appears to be closed or trading is blocked"
                
        except Exception as e:
            logger.error(f"Failed to check market conditions: {e}")
            return False, "Unable to verify market conditions"