# Debug test script for verifying backtesting components and data loading functionality.
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime
from backtesting.core.historical_data_loader import HistoricalDataLoader
from backtesting.core.signal_generator import HistoricalSignalGenerator
from backtesting.config import BacktestConfig

def debug_test():
    print("=== DEBUG TEST ===")
    
    # Create config
    config = BacktestConfig()
    
    # Load data
    print("Loading historical data...")
    data_loader = HistoricalDataLoader(config)
    start_date = datetime(2024, 10, 1)
    end_date = datetime(2024, 10, 5)  # Just a few days for testing
    
    try:
        historical_data = data_loader.load_all_historical_data(start_date, end_date)
        print(f"✓ Data loaded successfully")
        print(f"Data keys: {list(historical_data.keys())}")
        
        # Check data types
        for key, data in historical_data.items():
            print(f"  {key}: {type(data)} (length: {len(data) if hasattr(data, '__len__') else 'N/A'})")
            if hasattr(data, 'columns'):
                print(f"    Columns: {list(data.columns)}")
        
        # Test signal generation
        print("\nTesting signal generation...")
        signal_generator = HistoricalSignalGenerator(config)
        
        # Test individual signal calculations
        test_date = datetime(2024, 10, 2)
        
        print(f"Testing temperature signal for {test_date.date()}...")
        temp_signal = signal_generator.calculate_temperature_signal(historical_data['temperature'], test_date)
        print(f"✓ Temperature signal: {temp_signal}")
        
        print(f"Testing inventory signal for {test_date.date()}...")
        inventory_signal = signal_generator.calculate_inventory_signal(historical_data['eia'], test_date)
        print(f"✓ Inventory signal: {inventory_signal}")
        
        print(f"Testing storm signal for {test_date.date()}...")
        storm_signal = signal_generator.calculate_storm_signal(historical_data['storm'], test_date)
        print(f"✓ Storm signal: {storm_signal}")
        
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_test()
