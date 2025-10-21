# Main entry point for the natural gas trading bot that executes trades based on weather, inventory, and storm signals.

import sys
import os
import logging
import time
from datetime import datetime
from typing import Optional

# Add src and config directories to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'config'))

# Import our modules from the new structure
from config import TradingConfig
from data_sources.weather_data import WeatherDataFetcher
from data_sources.eia_data import EIADataFetcher
from data_sources.noaa_data import NOAADataFetcher
from signals.signal_processor import SignalProcessor
from trading.alpaca_trader import AlpacaTrader
from utils.trading_logger import TradingLogger
from dashboard.dashboard import TradingDashboard

class NatGasTraderBot:
    # Main trading bot class
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = TradingLogger(config)
        
        # Initialize data fetchers
        self.weather_fetcher = WeatherDataFetcher(config)
        self.eia_fetcher = EIADataFetcher(config)
        self.noaa_fetcher = NOAADataFetcher(config)
        
        # Initialize signal processor and trader
        self.signal_processor = SignalProcessor(config)
        self.trader = AlpacaTrader(config)
        
        # Initialize dashboard
        self.dashboard = TradingDashboard(config, self.trader, self.signal_processor)
        
        self.logger.logger.info("NATGAS TRADER Bot initialized")
    
    def fetch_all_signals(self) -> tuple[float, float, float]:
        # Fetch all trading signals
        self.logger.logger.info("Fetching trading signals...")
        
        # Fetch temperature signal
        temp_signal = self.weather_fetcher.get_regional_hdd_signal()
        
        # Fetch inventory signal
        inventory_signal = self.eia_fetcher.calculate_inventory_signal()
        
        # Fetch storm signal
        storm_signal = self.noaa_fetcher.calculate_storm_signal()
        
        return temp_signal, inventory_signal, storm_signal
    
    def run_trading_cycle(self) -> bool:
        """Run one complete trading cycle"""
        try:
            self.logger.logger.info("=" * 50)
            self.logger.logger.info(f"Starting trading cycle at {datetime.now()}")
            
            # Fetch all signals
            temp_signal, inventory_signal, storm_signal = self.fetch_all_signals()
            
            # Process signals
            trading_signal = self.signal_processor.create_trading_signal(
                temp_signal, inventory_signal, storm_signal
            )
            
            # Log the signal
            self.logger.log_signal(trading_signal)
            
            # Update dashboard with signal data
            signal_data = {
                'timestamp': trading_signal.timestamp.isoformat(),
                'temperature_signal': trading_signal.temperature_signal,
                'inventory_signal': trading_signal.inventory_signal,
                'storm_signal': trading_signal.storm_signal,
                'total_signal': trading_signal.total_signal,
                'action': trading_signal.action,
                'confidence': trading_signal.confidence
            }
            self.dashboard.update_data(signal_data=signal_data)
            
            # Execute trade if signal is strong enough
            trade_result = self.trader.execute_trade(trading_signal)
            
            # Log trade result
            self.logger.log_trade(trade_result)
            
            # Update dashboard with trade data
            if trade_result:
                self.dashboard.update_data(trade_data=trade_result)
            
            # Log portfolio status
            portfolio = self.trader.get_portfolio_summary()
            self.logger.log_portfolio(portfolio)
            
            # Update dashboard with portfolio data
            self.dashboard.update_data(portfolio_data=portfolio)
            
            self.logger.logger.info("Trading cycle completed successfully")
            return True
            
        except Exception as e:
            self.logger.log_error(e, "Trading cycle")
            return False
    
    def run_continuous(self, interval_hours: int = 24):
        """Run the bot continuously with specified interval (once per day by default)"""
        self.logger.logger.info(f"Starting continuous trading with {interval_hours}h intervals")
        
        while True:
            try:
                success = self.run_trading_cycle()
                
                if not success:
                    self.logger.logger.warning("Trading cycle failed, waiting before retry")
                    time.sleep(300)  # Wait 5 minutes before retry
                    continue
                
                # Wait for next cycle
                sleep_seconds = interval_hours * 3600
                self.logger.logger.info(f"Waiting {interval_hours} hours until next cycle")
                time.sleep(sleep_seconds)
                
            except KeyboardInterrupt:
                self.logger.logger.info("Bot stopped by user")
                break
            except Exception as e:
                self.logger.log_error(e, "Continuous trading loop")
                time.sleep(300)  # Wait 5 minutes before retry

def main():
    """Main entry point"""
    try:
        # Load configuration
        config = TradingConfig()
        
        # Validate configuration
        if not config.alpaca_api_key or not config.alpaca_secret_key:
            print("ERROR: Alpaca API credentials not found!")
            print("Please set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables")
            print("Or check your config/config.env file")
            sys.exit(1)
        
        # Create and run bot
        bot = NatGasTraderBot(config)
        
        # Start dashboard
        print("Starting NATGAS TRADER Bot Dashboard...")
        print("Dashboard will be available at: http://127.0.0.1:5000")
        bot.dashboard.start_dashboard_thread()
        
        # Check command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] == "once":
                # Run once
                bot.run_trading_cycle()
            elif sys.argv[1] == "continuous":
                # Run continuously
                interval = int(sys.argv[2]) if len(sys.argv) > 2 else 6
                bot.run_continuous(interval)
            elif sys.argv[1] == "dashboard":
                # Run dashboard only
                print("Dashboard mode - Trading bot will not execute trades")
                print("Dashboard running at: http://127.0.0.1:5000")
                print("Press Ctrl+C to stop")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\nDashboard stopped")
            else:
                print("Usage: python main.py [once|continuous|dashboard] [interval_hours]")
                print("Default: Continuous trading once per day with dashboard")
                sys.exit(1)
        else:
            # Default: run continuously with dashboard (once per day)
            print("Starting continuous trading mode (once per day)")
            print("Dashboard available at: http://127.0.0.1:5000")
            print("Press Ctrl+C to stop the bot")
            bot.run_continuous(24)
            
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()