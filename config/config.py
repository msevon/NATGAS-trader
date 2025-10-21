# Configuration management for the trading bot including API keys and trading parameters.
import os
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config/config.env')

@dataclass
class TradingConfig:
    # Configuration for the NATGAS TRADER
    
    # Alpaca API Configuration
    alpaca_api_key: str = os.getenv('ALPACA_API_KEY', '')
    alpaca_secret_key: str = os.getenv('ALPACA_SECRET_KEY', '')
    alpaca_base_url: str = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    
    # Trading Parameters
    symbol: str = 'BOIL'  # 2x leveraged natural gas ETF
    inverse_symbol: str = 'KOLD'  # 2x inverse natural gas ETF
    position_size: float = 1000.0  # Dollar amount per trade
    buy_threshold: float = 0.3  # Signal threshold to buy
    sell_threshold: float = -0.3  # Signal threshold to sell
    
    # Backtesting Parameters
    initial_capital: float = 100000.0  # Initial capital for backtesting
    base_position_size: float = 1000.0  # Base position size
    max_position_size: float = 5000.0  # Maximum position size
    min_position_size: float = 100.0   # Minimum position size
    commission_per_trade: float = 1.0  # Commission per trade
    slippage_pct: float = 0.001       # Slippage percentage
    
    # Risk Management Parameters
    default_stop_loss_pct: float = 0.05  # Default stop loss percentage
    trailing_stop_pct: float = 0.03       # Trailing stop percentage
    take_profit_pct: float = 0.15        # Take profit percentage
    
    # Signal Weights
    temperature_weight: float = 0.5
    inventory_weight: float = 0.4
    storm_weight: float = 0.1
    
    # Weather API Configuration
    weather_api_url: str = 'https://api.open-meteo.com/v1/forecast'
    weather_regions: List[str] = None
    
    # EIA API Configuration
    eia_api_key: str = os.getenv('EIA_API_KEY', '')
    eia_api_url: str = 'https://api.eia.gov/v2/natural-gas/stor/operating/data/'
    
    # NOAA API Configuration
    noaa_api_url: str = 'https://api.weather.gov/alerts'
    
    # Logging Configuration
    log_level: str = 'INFO'
    log_file: str = 'trading_bot.log'
    
    def __post_init__(self):
        if self.weather_regions is None:
            self.weather_regions = [
                '40.7128,-74.0060',  # New York
                '41.8781,-87.6298',  # Chicago
                '42.3601,-71.0589',  # Boston
                '39.9526,-75.1652',  # Philadelphia
                '42.3314,-83.0458',  # Detroit
            ]
