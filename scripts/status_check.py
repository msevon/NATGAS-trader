#!/usr/bin/env python3
"""
Quick status check for the Hot or Cold Trading Bot

This script shows the current portfolio status and recent signals.
"""

import sys
import os

# Add src and config directories to Python path
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'config'))

from config import TradingConfig
from trading.alpaca_trader import AlpacaTrader
from utils.trading_logger import TradingLogger

def main():
    """Check current status"""
    try:
        config = TradingConfig()
        logger = TradingLogger(config)
        trader = AlpacaTrader(config)
        
        print("Hot or Cold Trading Bot - Status Check")
        print("=" * 40)
        
        # Get account info
        account_info = trader.get_account_info()
        print(f"Account Equity: ${account_info.get('equity', 0):,.2f}")
        print(f"Cash: ${account_info.get('cash', 0):,.2f}")
        print(f"Buying Power: ${account_info.get('buying_power', 0):,.2f}")
        
        # Get current position
        position = trader.get_current_position()
        if position:
            print(f"\nCurrent Position:")
            print(f"  Symbol: {position['symbol']}")
            print(f"  Quantity: {position['qty']}")
            print(f"  Market Value: ${position['market_value']:,.2f}")
            print(f"  Avg Entry Price: ${position['avg_entry_price']:.2f}")
            print(f"  Unrealized P&L: ${position['unrealized_pl']:,.2f} ({position['unrealized_plpc']:.2%})")
        else:
            print(f"\nNo current position in {config.symbol}")
        
        # Get portfolio summary
        portfolio = trader.get_portfolio_summary()
        print(f"\nPortfolio Summary:")
        print(f"  Total Value: ${portfolio.get('total_value', 0):,.2f}")
        print(f"  Number of Positions: {len(portfolio.get('positions', []))}")
        
        print("\nStatus check completed successfully!")
        
    except Exception as e:
        print(f"Error checking status: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
