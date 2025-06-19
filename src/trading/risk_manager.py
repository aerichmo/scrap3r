from typing import Optional
import logging

from ..config import Settings
from ..models.trade import Trade


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
            
            # Maximum position size as percentage of account
            max_position_value = min(
                self.settings.trading.max_position_size,
                account_value * 0.1  # Max 10% per position
            )
            
            # Calculate shares
            shares = int(max_position_value / price)
            
            # Ensure at least 1 share
            return max(1, shares)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 1
            
    def validate_trade(self, trade: Trade) -> tuple[bool, Optional[str]]:
        """Validate a trade against risk rules"""
        try:
            account = self.trading_client.get_account()
            
            # Check if account is restricted
            if account.trading_blocked:
                return False, "Account trading is blocked"
                
            # Check if we have sufficient buying power
            if trade.side == 'buy':
                required_capital = trade.quantity * trade.price
                buying_power = float(account.buying_power)
                
                if required_capital > buying_power:
                    return False, f"Insufficient buying power: ${buying_power:.2f}"
                    
            # Check if we already have a position (for buys)
            if trade.side == 'buy':
                position = self.trading_client.get_position(trade.symbol)
                if position:
                    return False, f"Already have position in {trade.symbol}"
                    
            # Check position limits
            positions = self.trading_client.get_positions()
            if trade.side == 'buy' and len(positions) >= self.settings.trading.max_positions:
                return False, f"Maximum positions reached ({self.settings.trading.max_positions})"
                
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating trade: {e}")
            return False, str(e)
            
    def check_market_conditions(self) -> tuple[bool, Optional[str]]:
        """Check if market conditions are suitable for trading"""
        # This could be expanded to check:
        # - Market volatility
        # - Trading halts
        # - Circuit breakers
        # - Time of day restrictions
        
        # For now, just return True
        return True, None