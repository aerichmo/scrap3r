from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Position:
    """Represents a trading position"""
    symbol: str
    quantity: int
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float = 0.0
    opened_at: datetime = None
    
    def __post_init__(self):
        if self.opened_at is None:
            self.opened_at = datetime.now()
            
    @classmethod
    def from_broker_position(cls, broker_position):
        """Create Position from Alpaca position object"""
        return cls(
            symbol=broker_position.symbol,
            quantity=int(broker_position.qty),
            avg_entry_price=float(broker_position.avg_entry_price),
            current_price=float(broker_position.current_price or 0),
            market_value=float(broker_position.market_value or 0),
            unrealized_pnl=float(broker_position.unrealized_pl or 0)
        )
        
    def update_from_broker(self, broker_position):
        """Update position from broker data"""
        self.quantity = int(broker_position.qty)
        self.current_price = float(broker_position.current_price or 0)
        self.market_value = float(broker_position.market_value or 0)
        self.unrealized_pnl = float(broker_position.unrealized_pl or 0)
        
    def get_profit_percentage(self) -> float:
        """Calculate profit percentage"""
        if self.avg_entry_price == 0:
            return 0.0
        return (self.current_price - self.avg_entry_price) / self.avg_entry_price