from typing import Dict, List, Optional
from datetime import datetime
import logging

from ..config import Settings
from ..models.position import Position
from ..utils.exceptions import PositionError, APIError


logger = logging.getLogger(__name__)


class PositionManager:
    """Manages trading positions and tracks P&L"""
    
    def __init__(self, settings: Settings, trading_client):
        self.settings = settings
        self.trading_client = trading_client
        self.positions: Dict[str, Position] = {}
        
    def update_positions(self):
        """Update positions from broker"""
        try:
            broker_positions = self.trading_client.get_positions()
            
            # Update existing positions
            current_symbols = set()
            for pos in broker_positions:
                symbol = pos.symbol
                current_symbols.add(symbol)
                
                if symbol in self.positions:
                    self.positions[symbol].update_from_broker(pos)
                else:
                    self.positions[symbol] = Position.from_broker_position(pos)
                    
            # Remove closed positions
            closed_symbols = set(self.positions.keys()) - current_symbols
            for symbol in closed_symbols:
                logger.info(f"Position closed: {symbol}")
                del self.positions[symbol]
                
        except APIError:
            # Re-raise API errors as they're critical
            raise
        except Exception as e:
            raise PositionError(f"Failed to update positions: {str(e)}")
            
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        return self.positions.get(symbol)
        
    def has_position(self, symbol: str) -> bool:
        """Check if we have a position in symbol"""
        return symbol in self.positions
        
    def get_total_positions(self) -> int:
        """Get total number of positions"""
        return len(self.positions)
        
    def can_open_new_position(self) -> bool:
        """Check if we can open a new position"""
        return self.get_total_positions() < self.settings.trading.max_positions
        
    def check_exit_conditions(self) -> List[Dict]:
        """Check all positions for exit conditions"""
        exits = []
        
        try:
            for symbol, position in self.positions.items():
                # Validate position data
                if position.avg_entry_price <= 0:
                    logger.error(f"Invalid entry price for {symbol}: {position.avg_entry_price}")
                    continue
                    
                profit_pct = position.get_profit_percentage()
                
                # Check profit target
                if profit_pct >= self.settings.trading.profit_target:
                    exits.append({
                        'symbol': symbol,
                        'reason': 'profit_target',
                        'profit_pct': profit_pct,
                        'current_price': position.current_price,
                        'entry_price': position.avg_entry_price
                    })
                    logger.info(f"Profit target reached for {symbol}: {profit_pct:.2%} "
                              f"(Entry: ${position.avg_entry_price:.2f}, Current: ${position.current_price:.2f})")
                    
                # Check stop loss
                elif profit_pct <= -self.settings.trading.stop_loss:
                    exits.append({
                        'symbol': symbol,
                        'reason': 'stop_loss',
                        'profit_pct': profit_pct,
                        'current_price': position.current_price,
                        'entry_price': position.avg_entry_price
                    })
                    logger.warning(f"Stop loss triggered for {symbol}: {profit_pct:.2%} "
                                 f"(Entry: ${position.avg_entry_price:.2f}, Current: ${position.current_price:.2f})")
                    
        except Exception as e:
            # Don't crash on exit check errors - log and continue
            logger.error(f"Error checking exit conditions: {e}")
            
        return exits
        
    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        try:
            total = 0.0
            for position in self.positions.values():
                if position.market_value > 0:
                    total += position.market_value
            return total
        except Exception as e:
            logger.error(f"Error calculating portfolio value: {e}")
            return 0.0
        
    def get_portfolio_pnl(self) -> float:
        """Get total unrealized P&L"""
        try:
            total = 0.0
            for position in self.positions.values():
                total += position.unrealized_pnl
            return total
        except Exception as e:
            logger.error(f"Error calculating portfolio P&L: {e}")
            return 0.0