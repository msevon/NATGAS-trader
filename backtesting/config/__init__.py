# Configuration classes and utilities for managing backtesting parameters and settings.

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime


# Configuration class for backtesting parameters.
#
# This class contains all the parameters needed to configure a backtest,
# including strategy parameters, risk management settings, and data sources.
@dataclass
class BacktestConfig:
    
    # Basic settings
    initial_capital: float = 100000.0
    symbol: str = "BOIL"
    inverse_symbol: str = "KOLD"
    
    # Strategy parameters
    buy_threshold: float = 0.3
    sell_threshold: float = -0.3
    temperature_weight: float = 0.4
    inventory_weight: float = 0.4
    storm_weight: float = 0.2
    
    # Position sizing
    base_position_size: float = 1000.0
    max_position_size: float = 5000.0
    min_position_size: float = 100.0
    
    # Risk management
    default_stop_loss_pct: float = 0.05
    trailing_stop_pct: float = 0.03
    take_profit_pct: float = 0.15
    
    # Trading costs
    commission_per_trade: float = 1.0
    slippage_pct: float = 0.001
    
    # Signal confirmation
    confirmation_days: int = 2
    
    # Data sources
    eia_api_key: Optional[str] = None
    weather_api_key: Optional[str] = None
    weather_api_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_regions: List[str] = None
    noaa_api_key: Optional[str] = None
    noaa_api_url: str = "https://api.weather.gov/alerts"
    
    # Backtest period
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Additional settings
    enable_logging: bool = True
    log_level: str = "INFO"
    generate_reports: bool = True
    report_format: str = "html"
    
    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)
    
    # Convert configuration to dictionary.
    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat() if value else None
            else:
                result[key] = value
        return result
    
    # Create configuration from dictionary.
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BacktestConfig':
        # Handle datetime fields
        if 'start_date' in config_dict and config_dict['start_date']:
            config_dict['start_date'] = datetime.fromisoformat(config_dict['start_date'])
        if 'end_date' in config_dict and config_dict['end_date']:
            config_dict['end_date'] = datetime.fromisoformat(config_dict['end_date'])
        
        return cls(**config_dict)
    
    # Validate configuration parameters.
    #
    # Returns:
    #     List of validation errors
    def validate(self) -> List[str]:
        errors = []
        
        # Check required fields
        if self.initial_capital <= 0:
            errors.append("Initial capital must be positive")
        
        if self.buy_threshold <= self.sell_threshold:
            errors.append("Buy threshold must be greater than sell threshold")
        
        if self.base_position_size <= 0:
            errors.append("Base position size must be positive")
        
        if self.max_position_size <= self.base_position_size:
            errors.append("Max position size must be greater than base position size")
        
        if self.min_position_size <= 0:
            errors.append("Min position size must be positive")
        
        # Check percentages
        percentages = [
            ('default_stop_loss_pct', self.default_stop_loss_pct),
            ('trailing_stop_pct', self.trailing_stop_pct),
            ('take_profit_pct', self.take_profit_pct),
            ('slippage_pct', self.slippage_pct)
        ]
        
        for name, value in percentages:
            if not 0 <= value <= 1:
                errors.append(f"{name} must be between 0 and 1")
        
        # Check weights sum to 1
        total_weight = self.temperature_weight + self.inventory_weight + self.storm_weight
        if abs(total_weight - 1.0) > 0.01:
            errors.append("Signal weights must sum to 1.0")
        
        # Check date range
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                errors.append("Start date must be before end date")
        
        return errors
    
    # Get strategy-specific parameters.
    def get_strategy_params(self) -> Dict[str, Any]:
        return {
            'buy_threshold': self.buy_threshold,
            'sell_threshold': self.sell_threshold,
            'temperature_weight': self.temperature_weight,
            'inventory_weight': self.inventory_weight,
            'storm_weight': self.storm_weight,
            'base_position_size': self.base_position_size,
            'max_position_size': self.max_position_size,
            'min_position_size': self.min_position_size,
            'default_stop_loss_pct': self.default_stop_loss_pct,
            'trailing_stop_pct': self.trailing_stop_pct,
            'take_profit_pct': self.take_profit_pct,
            'commission_per_trade': self.commission_per_trade,
            'slippage_pct': self.slippage_pct,
            'confirmation_days': self.confirmation_days
        }
    
    # Get risk management parameters.
    def get_risk_params(self) -> Dict[str, Any]:
        return {
            'default_stop_loss_pct': self.default_stop_loss_pct,
            'trailing_stop_pct': self.trailing_stop_pct,
            'take_profit_pct': self.take_profit_pct,
            'max_position_size': self.max_position_size,
            'min_position_size': self.min_position_size
        }
    
    # Get data source parameters.
    def get_data_params(self) -> Dict[str, Any]:
        return {
            'eia_api_key': self.eia_api_key,
            'weather_api_key': self.weather_api_key,
            'noaa_api_key': self.noaa_api_key,
            'start_date': self.start_date,
            'end_date': self.end_date
        }


# Create a default configuration.
def create_default_config() -> BacktestConfig:
    return BacktestConfig()


# Create a conservative configuration.
def create_conservative_config() -> BacktestConfig:
    config = BacktestConfig()
    config.buy_threshold = 0.5
    config.sell_threshold = -0.5
    config.default_stop_loss_pct = 0.03
    config.take_profit_pct = 0.10
    config.base_position_size = 500.0
    config.max_position_size = 2000.0
    return config


# Create an aggressive configuration.
def create_aggressive_config() -> BacktestConfig:
    config = BacktestConfig()
    config.buy_threshold = 0.2
    config.sell_threshold = -0.2
    config.default_stop_loss_pct = 0.08
    config.take_profit_pct = 0.20
    config.base_position_size = 2000.0
    config.max_position_size = 8000.0
    config.trailing_stop_pct = 0.05
    return config


# Create a balanced configuration.
def create_balanced_config() -> BacktestConfig:
    config = BacktestConfig()
    config.buy_threshold = 0.4
    config.sell_threshold = -0.4
    config.default_stop_loss_pct = 0.05
    config.take_profit_pct = 0.15
    config.base_position_size = 1000.0
    config.max_position_size = 4000.0
    return config
