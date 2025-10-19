#!/usr/bin/env python3
"""
Test script for the Hot or Cold Trading Bot

This script tests individual components without making actual trades.
"""

import sys
import os

# Add src and config directories to Python path
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'config'))

from config import TradingConfig
from data_sources.weather_data import WeatherDataFetcher
from data_sources.eia_data import EIADataFetcher
from data_sources.noaa_data import NOAADataFetcher
from signals.signal_processor import SignalProcessor

def test_weather_data():
    """Test weather data fetching"""
    print("Testing Weather Data Fetching...")
    config = TradingConfig()
    weather_fetcher = WeatherDataFetcher(config)
    
    signal = weather_fetcher.get_regional_hdd_signal()
    print(f"Weather signal: {signal:.3f}")
    return signal

def test_eia_data():
    """Test EIA data fetching"""
    print("\nTesting EIA Data Fetching...")
    config = TradingConfig()
    eia_fetcher = EIADataFetcher(config)
    
    signal = eia_fetcher.calculate_inventory_signal()
    print(f"Inventory signal: {signal:.3f}")
    return signal

def test_noaa_data():
    """Test NOAA data fetching"""
    print("\nTesting NOAA Data Fetching...")
    config = TradingConfig()
    noaa_fetcher = NOAADataFetcher(config)
    
    signal = noaa_fetcher.calculate_storm_signal()
    print(f"Storm signal: {signal:.3f}")
    return signal

def test_signal_processing():
    """Test signal processing"""
    print("\nTesting Signal Processing...")
    config = TradingConfig()
    processor = SignalProcessor(config)
    
    # Test with sample signals
    temp_signal = 0.2
    inventory_signal = -0.1
    storm_signal = 0.05
    
    trading_signal = processor.create_trading_signal(
        temp_signal, inventory_signal, storm_signal
    )
    
    print(f"Temperature signal: {trading_signal.temperature_signal:.3f}")
    print(f"Inventory signal: {trading_signal.inventory_signal:.3f}")
    print(f"Storm signal: {trading_signal.storm_signal:.3f}")
    print(f"Total signal: {trading_signal.total_signal:.3f}")
    print(f"Action: {trading_signal.action}")
    print(f"Confidence: {trading_signal.confidence:.3f}")
    
    return trading_signal

def main():
    """Run all tests"""
    print("Hot or Cold Trading Bot - Component Tests")
    print("=" * 50)
    
    try:
        # Test individual components
        weather_signal = test_weather_data()
        inventory_signal = test_eia_data()
        storm_signal = test_noaa_data()
        
        # Test signal processing with real data
        print("\nTesting Signal Processing with Real Data...")
        config = TradingConfig()
        processor = SignalProcessor(config)
        
        trading_signal = processor.create_trading_signal(
            weather_signal, inventory_signal, storm_signal
        )
        
        print(f"\nFinal Trading Signal:")
        print(f"  Temperature: {trading_signal.temperature_signal:.3f}")
        print(f"  Inventory: {trading_signal.inventory_signal:.3f}")
        print(f"  Storm: {trading_signal.storm_signal:.3f}")
        print(f"  Total: {trading_signal.total_signal:.3f}")
        print(f"  Action: {trading_signal.action}")
        print(f"  Confidence: {trading_signal.confidence:.3f}")
        
        print("\nAll tests completed successfully!")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
