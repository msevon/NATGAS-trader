# Processes and combines trading signals from multiple data sources to generate buy/sell decisions.
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
import pandas as pd

@dataclass
class TradingSignal:
    """Represents a trading signal with all components"""
    timestamp: datetime
    temperature_signal: float
    inventory_signal: float
    storm_signal: float
    total_signal: float
    action: str  # 'BUY', 'SELL', 'HOLD'
    symbol: str  # 'BOIL' or 'KOLD'
    confidence: float

class SignalProcessor:
    """Processes and combines all trading signals"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def calculate_total_signal(self, temp_signal: float, inventory_signal: float, storm_signal: float) -> float:
        """Calculate weighted total signal"""
        total_signal = (
            temp_signal * self.config.temperature_weight +
            inventory_signal * self.config.inventory_weight +
            storm_signal * self.config.storm_weight
        )
        
        self.logger.info(f"Signal components:")
        self.logger.info(f"  Temperature: {temp_signal:.3f} (weight: {self.config.temperature_weight})")
        self.logger.info(f"  Inventory: {inventory_signal:.3f} (weight: {self.config.inventory_weight})")
        self.logger.info(f"  Storm: {storm_signal:.3f} (weight: {self.config.storm_weight})")
        self.logger.info(f"  Total signal: {total_signal:.3f}")
        
        return total_signal
    
    def determine_action(self, total_signal: float) -> Tuple[str, str, float]:
        """Determine trading action and symbol based on signal strength"""
        if total_signal > self.config.buy_threshold:
            action = 'BUY'
            symbol = self.config.symbol  # BOIL for bullish natural gas
            confidence = min(total_signal / self.config.buy_threshold, 2.0)
        elif total_signal < self.config.sell_threshold:
            action = 'BUY'
            symbol = self.config.inverse_symbol  # KOLD for bearish natural gas
            confidence = min(abs(total_signal) / abs(self.config.sell_threshold), 2.0)
        else:
            action = 'HOLD'
            symbol = ''
            confidence = 0.0
        
        return action, symbol, confidence
    
    def create_trading_signal(self, temp_signal: float, inventory_signal: float, storm_signal: float) -> TradingSignal:
        """Create a complete trading signal"""
        total_signal = self.calculate_total_signal(temp_signal, inventory_signal, storm_signal)
        action, symbol, confidence = self.determine_action(total_signal)
        
        return TradingSignal(
            timestamp=datetime.now(),
            temperature_signal=temp_signal,
            inventory_signal=inventory_signal,
            storm_signal=storm_signal,
            total_signal=total_signal,
            action=action,
            symbol=symbol,
            confidence=confidence
        )
    
    def calculate_historical_signals(self, start_date: datetime, end_date: datetime) -> List[TradingSignal]:
        """Calculate historical signals for a given date range"""
        try:
            from src.data_sources.weather_data import WeatherDataFetcher
            from src.data_sources.eia_data import EIADataFetcher
            from src.data_sources.noaa_data import NOAADataFetcher
            
            weather_fetcher = WeatherDataFetcher(self.config)
            eia_fetcher = EIADataFetcher(self.config)
            noaa_fetcher = NOAADataFetcher(self.config)
            
            historical_signals = []
            
            # Generate daily signals for the date range
            current_date = start_date
            while current_date <= end_date:
                try:
                    # Get signals for this date
                    temp_signal = weather_fetcher.get_regional_hdd_signal()
                    inventory_signal = eia_fetcher.calculate_inventory_signal()
                    storm_signal = noaa_fetcher.calculate_storm_signal()
                    
                    # Calculate total signal
                    total_signal = self.calculate_total_signal(temp_signal, inventory_signal, storm_signal)
                    action, symbol, confidence = self.determine_action(total_signal)
                    
                    # Create historical signal
                    signal = TradingSignal(
                        timestamp=current_date,
                        temperature_signal=temp_signal,
                        inventory_signal=inventory_signal,
                        storm_signal=storm_signal,
                        total_signal=total_signal,
                        action=action,
                        symbol=symbol,
                        confidence=confidence
                    )
                    
                    historical_signals.append(signal)
                    
                except Exception as e:
                    self.logger.warning(f"Error calculating signal for {current_date}: {e}")
                
                # Move to next day
                current_date += timedelta(days=1)
            
            self.logger.info(f"Calculated {len(historical_signals)} historical signals from {start_date} to {end_date}")
            return historical_signals
            
        except Exception as e:
            self.logger.error(f"Error calculating historical signals: {e}")
            return []
