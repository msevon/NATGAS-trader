# Starts the web dashboard server for monitoring trading bot performance and portfolio status.
import os
import time

# Add src and config directories to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'config'))

from config import TradingConfig
from trading.alpaca_trader import AlpacaTrader
from signals.signal_processor import SignalProcessor
from dashboard.dashboard import TradingDashboard

    # Start dashboard only
    def main(self):
    try:
        print("Starting NATGAS TRADER Dashboard...")
        print("Dashboard will be available at: http://127.0.0.1:5000")
        
        # Load configuration
        config = TradingConfig()
        
        # Initialize components
        trader = AlpacaTrader(config)
        signal_processor = SignalProcessor(config)
        
        # Initialize dashboard
        dashboard = TradingDashboard(config, trader, signal_processor)
        
        # Start dashboard
        dashboard.start_dashboard_thread()
        
        print("Dashboard started successfully!")
        print("Open your browser and go to: http://127.0.0.1:5000")
        print("The dashboard will show real-time trading data")
        print("Press Ctrl+C to stop the dashboard")
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nDashboard stopped")
            
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
