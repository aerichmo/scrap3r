#!/usr/bin/env python3
"""
Health check script for SCRAP3R
Returns 0 if healthy, 1 if unhealthy
"""

import sys
import os
from datetime import datetime

from src.config import Settings
from src.trading import TradingClient
from src.utils import setup_logging


def main():
    """Run health checks"""
    setup_logging('WARNING')  # Only show warnings and errors
    
    try:
        # Check 1: Configuration
        print("Checking configuration...")
        settings = Settings()
        settings.validate()
        print("✓ Configuration valid")
        
        # Check 2: Alpaca connection
        print("Checking Alpaca connection...")
        trading_client = TradingClient(settings)
        account = trading_client.get_account()
        print(f"✓ Connected to Alpaca (Account: {account.account_number})")
        
        # Check 3: Account status
        print("Checking account status...")
        if account.trading_blocked:
            print("✗ Trading is blocked")
            return 1
        print("✓ Trading enabled")
        
        # Check 4: Buying power
        buying_power = float(account.buying_power)
        if buying_power < 100:
            print(f"✗ Low buying power: ${buying_power:.2f}")
            return 1
        print(f"✓ Buying power: ${buying_power:,.2f}")
        
        # Check 5: Positions
        positions = trading_client.get_positions()
        print(f"✓ Positions: {len(positions)}")
        
        # All checks passed
        print("\n✓ All health checks passed")
        return 0
        
    except Exception as e:
        print(f"\n✗ Health check failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())