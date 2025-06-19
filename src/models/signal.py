from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Signal:
    """Represents a trading signal"""
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    strength: float  # Signal strength (0-1)
    source: str  # Signal source (e.g., 'sentiment', 'technical', 'momentum')
    sentiment_score: Optional[float] = None
    mentions: Optional[int] = None
    reason: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
            
    def is_actionable(self, min_strength: float = 0.3) -> bool:
        """Check if signal is strong enough to act on"""
        return self.strength >= min_strength and self.action in ['buy', 'sell']