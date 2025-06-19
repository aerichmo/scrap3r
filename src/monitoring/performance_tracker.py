from datetime import datetime
from typing import Dict, List
import json
import os
import logging


logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Track trading performance metrics"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.metrics_file = os.path.join(data_dir, "performance.json")
        self.trades_file = os.path.join(data_dir, "trades.json")
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Load existing data
        self.metrics = self._load_metrics()
        self.trades = self._load_trades()
        
    def _load_metrics(self) -> Dict:
        """Load performance metrics from file"""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading metrics: {e}")
                
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'win_rate': 0.0,
            'average_win': 0.0,
            'average_loss': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'start_date': datetime.now().isoformat(),
            'last_update': datetime.now().isoformat()
        }
        
    def _load_trades(self) -> List[Dict]:
        """Load trade history from file"""
        if os.path.exists(self.trades_file):
            try:
                with open(self.trades_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading trades: {e}")
                
        return []
        
    def _save_metrics(self):
        """Save metrics to file"""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
            
    def _save_trades(self):
        """Save trades to file"""
        try:
            with open(self.trades_file, 'w') as f:
                json.dump(self.trades, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving trades: {e}")
            
    def record_trade(self, symbol: str, side: str, quantity: int, 
                    entry_price: float, exit_price: float = None, 
                    profit_loss: float = None):
        """Record a completed trade"""
        trade = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'profit_loss': profit_loss,
            'timestamp': datetime.now().isoformat()
        }
        
        self.trades.append(trade)
        
        # Update metrics if trade is closed
        if exit_price and profit_loss is not None:
            self._update_metrics(profit_loss)
            
        self._save_trades()
        
    def _update_metrics(self, profit_loss: float):
        """Update performance metrics"""
        self.metrics['total_trades'] += 1
        
        if profit_loss > 0:
            self.metrics['winning_trades'] += 1
            self.metrics['total_profit'] += profit_loss
            if profit_loss > self.metrics['largest_win']:
                self.metrics['largest_win'] = profit_loss
        else:
            self.metrics['losing_trades'] += 1
            self.metrics['total_loss'] += abs(profit_loss)
            if profit_loss < self.metrics['largest_loss']:
                self.metrics['largest_loss'] = profit_loss
                
        # Calculate derived metrics
        total_trades = self.metrics['total_trades']
        if total_trades > 0:
            self.metrics['win_rate'] = self.metrics['winning_trades'] / total_trades
            
        if self.metrics['winning_trades'] > 0:
            self.metrics['average_win'] = (self.metrics['total_profit'] / 
                                          self.metrics['winning_trades'])
                                          
        if self.metrics['losing_trades'] > 0:
            self.metrics['average_loss'] = (self.metrics['total_loss'] / 
                                           self.metrics['losing_trades'])
                                           
        self.metrics['last_update'] = datetime.now().isoformat()
        self._save_metrics()
        
    def get_summary(self) -> Dict:
        """Get performance summary"""
        return self.metrics.copy()
        
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get recent trades"""
        return self.trades[-limit:] if self.trades else []