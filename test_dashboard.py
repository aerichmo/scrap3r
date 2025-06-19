#!/usr/bin/env python3
"""
Test the error dashboard locally
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.monitoring.error_tracker import get_error_tracker
import logging

# Setup logging
from src.utils import setup_logging
setup_logging()

logger = logging.getLogger(__name__)

# Generate some test errors
error_tracker = get_error_tracker()

# Log some test errors
logger.error("Test error 1: Failed to connect to Reddit")
logger.warning("This is just a warning")
logger.critical("Test critical error: Trading system failure!")

try:
    1 / 0
except Exception as e:
    logger.error("Test error with exception", exc_info=True)

print("\n✅ Test errors logged!")
print("\n📊 To view the dashboard:")
print("   1. Run: python web_dashboard.py")
print("   2. Open: http://localhost:5000")
print("\n📁 Error log saved to: data/error_log.json")