"""
Error tracking and logging for SCRAP3R
"""

import os
import json
from datetime import datetime
from collections import deque
from typing import List, Dict, Optional
import logging


class ErrorTracker:
    """Tracks errors and maintains error history"""
    
    def __init__(self, max_errors: int = 100):
        self.max_errors = max_errors
        self.errors: deque = deque(maxlen=max_errors)
        self.log_file = "data/error_log.json"
        self.status = {
            "healthy": True,
            "last_error": None,
            "error_count": 0,
            "start_time": datetime.now().isoformat()
        }
        
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        # Load existing errors
        self._load_errors()
        
    def _load_errors(self):
        """Load existing errors from file"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    self.errors = deque(data.get('errors', []), maxlen=self.max_errors)
                    self.status = data.get('status', self.status)
            except:
                pass
                
    def _save_errors(self):
        """Save errors to file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump({
                    'errors': list(self.errors),
                    'status': self.status
                }, f, indent=2)
        except:
            pass
            
    def log_error(self, error_type: str, error_msg: str, context: str = "", 
                  critical: bool = False, traceback: str = ""):
        """Log an error"""
        error = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'message': error_msg,
            'context': context,
            'critical': critical,
            'traceback': traceback
        }
        
        self.errors.append(error)
        self.status['healthy'] = False
        self.status['last_error'] = error
        self.status['error_count'] += 1
        
        self._save_errors()
        
    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """Get recent errors"""
        return list(self.errors)[-limit:]
        
    def get_status(self) -> Dict:
        """Get current status"""
        return self.status.copy()
        
    def clear_errors(self):
        """Clear all errors and reset status"""
        self.errors.clear()
        self.status = {
            "healthy": True,
            "last_error": None,
            "error_count": 0,
            "start_time": datetime.now().isoformat()
        }
        self._save_errors()
        
    def mark_healthy(self):
        """Mark system as healthy"""
        self.status['healthy'] = True
        self._save_errors()


# Global error tracker instance
_error_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """Get or create the global error tracker"""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker


class ErrorLoggingHandler(logging.Handler):
    """Custom logging handler that tracks errors"""
    
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            error_tracker = get_error_tracker()
            
            # Extract traceback if available
            traceback = ""
            if record.exc_info:
                import traceback as tb
                traceback = ''.join(tb.format_exception(*record.exc_info))
                
            error_tracker.log_error(
                error_type=record.levelname,
                error_msg=record.getMessage(),
                context=f"{record.pathname}:{record.lineno}",
                critical=(record.levelno >= logging.CRITICAL),
                traceback=traceback
            )