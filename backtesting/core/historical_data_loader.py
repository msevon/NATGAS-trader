# Loads historical data from EIA, weather, NOAA, and Yahoo Finance APIs for backtesting.
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import json
import yfinance as yf
from dataclasses import dataclass

# Represents a single data point with timestamp and value
@dataclass
class HistoricalDataPoint:
    timestamp: datetime
    value: float
    data_type: str  # 'eia', 'temperature', 'storm', 'price'

# Loads historical data from various sources for backtesting
class HistoricalDataLoader:
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Ensure environment variables are loaded
        import os
        from dotenv import load_dotenv
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config', 'config.env')
        if os.path.exists(config_path):
            load_dotenv(config_path)
        
        # Update config with environment variables if not already set
        if not hasattr(config, 'eia_api_key') or not config.eia_api_key:
            config.eia_api_key = os.getenv('EIA_API_KEY')
        
    # Load historical EIA natural gas storage data
    def load_eia_historical_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        try:
            self.logger.info(f"Loading EIA historical data from {start_date} to {end_date}")
            
            # Try to fetch from EIA API first (same as working dashboard)
            try:
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                from src.data_sources.eia_data import EIADataFetcher
                eia_fetcher = EIADataFetcher(self.config)
                df = eia_fetcher.fetch_storage_data_with_range(start_date, end_date)
                if df is not None and len(df) > 0:
                    # Normalize timezone-aware timestamps to timezone-naive
                    if 'period' in df.columns and len(df) > 0 and hasattr(df['period'].iloc[0], 'tz') and df['period'].iloc[0].tz is not None:
                        df['period'] = df['period'].dt.tz_localize(None)
                    elif 'timestamp' in df.columns and len(df) > 0 and hasattr(df['timestamp'].iloc[0], 'tz') and df['timestamp'].iloc[0].tz is not None:
                        df['timestamp'] = df['timestamp'].dt.tz_localize(None)
                    
                    self.logger.info(f"Successfully loaded {len(df)} EIA data points from API")
                    return df
                else:
                    raise ValueError("No real EIA data available")
            except Exception as e:
                self.logger.error(f"EIA API failed: {e}")
                raise ValueError(f"No real EIA data available: {e}")
            
        except Exception as e:
            self.logger.error(f"Error loading EIA historical data: {e}")
            raise ValueError(f"No real EIA data available: {e}")
    
    # Load historical temperature data for HDD calculations
    def load_temperature_historical_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        try:
            self.logger.info(f"Loading temperature historical data from {start_date} to {end_date}")
            
            # Try to fetch real weather data
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from src.data_sources.weather_data import WeatherDataFetcher
            weather_fetcher = WeatherDataFetcher(self.config)
            
            # Get temperature data for major US cities
            cities = ['New York', 'Chicago', 'Houston', 'Los Angeles', 'Phoenix']
            all_temp_data = []
            
            for city in cities:
                try:
                    # Convert city name to coordinates (simplified)
                    city_coords = {
                        'New York': '40.7128,-74.0060',
                        'Chicago': '41.8781,-87.6298',
                        'Houston': '29.7604,-95.3698',
                        'Los Angeles': '34.0522,-118.2437',
                        'Phoenix': '33.4484,-112.0740'
                    }
                    
                    if city in city_coords:
                        temp_data = weather_fetcher.fetch_weather_forecast(city_coords[city], days=7)
                        if temp_data and 'daily' in temp_data:
                            daily_data = temp_data['daily']
                            temps_max = daily_data['temperature_2m_max']
                            temps_min = daily_data['temperature_2m_min']
                            times = daily_data['time']
                            
                            for i, (temp_max, temp_min, time_str) in enumerate(zip(temps_max, temps_min, times)):
                                hdd = weather_fetcher.calculate_hdd(temp_max, temp_min)
                                all_temp_data.append({
                                    'timestamp': pd.to_datetime(time_str),
                                    'temp_max': temp_max,
                                    'temp_min': temp_min,
                                    'hdd': hdd
                                })
                except Exception as e:
                    self.logger.warning(f"Could not fetch temperature data for {city}: {e}")
            
            if not all_temp_data:
                raise ValueError("No real temperature data available")
            
            # Convert to DataFrame
            df = pd.DataFrame(all_temp_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Normalize timezone-aware timestamps to timezone-naive
            if len(df) > 0 and hasattr(df['timestamp'].iloc[0], 'tz') and df['timestamp'].iloc[0].tz is not None:
                df['timestamp'] = df['timestamp'].dt.tz_localize(None)
            
            df = df.sort_values('timestamp')
            
            self.logger.info(f"Successfully loaded {len(df)} temperature data points")
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading temperature historical data: {e}")
            raise ValueError(f"No real temperature data available: {e}")
    
    # Load historical storm/disruption data
    def load_storm_historical_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        try:
            self.logger.info(f"Loading storm historical data from {start_date} to {end_date}")
            
            # Try to fetch real NOAA storm data
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from src.data_sources.noaa_data import NOAADataFetcher
            noaa_fetcher = NOAADataFetcher(self.config)
            
            storm_data = noaa_fetcher.fetch_weather_alerts()
            if not storm_data:
                raise ValueError("No real storm data available")
            
            # Convert to DataFrame
            df = pd.DataFrame(storm_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Normalize timezone-aware timestamps to timezone-naive
            if len(df) > 0 and hasattr(df['timestamp'].iloc[0], 'tz') and df['timestamp'].iloc[0].tz is not None:
                df['timestamp'] = df['timestamp'].dt.tz_localize(None)
            
            df = df.sort_values('timestamp')
            
            self.logger.info(f"Successfully loaded {len(df)} storm data points")
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading storm historical data: {e}")
            raise ValueError(f"No real storm data available: {e}")
    
    # Load historical price data for BOIL/KOLD
    def load_price_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        try:
            self.logger.info(f"Loading {symbol} price data from {start_date} to {end_date}")
            
            # Use the same approach as YahooFinanceDataFetcher (which works in dashboard)
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            
            # Check if hist is a DataFrame and not empty
            if hist is None or not isinstance(hist, pd.DataFrame) or hist.empty:
                self.logger.error(f"No price data found for {symbol}")
                raise ValueError(f"No real price data available for {symbol} in the specified date range")
            
            # Convert to our format (same as YahooFinanceDataFetcher)
            df = pd.DataFrame({
                'timestamp': hist.index,
                'price': hist['Close']
            })
            
            df_clean = df.reset_index(drop=True)
            df_clean = df_clean.sort_values('timestamp')
            
            # Handle timezone-aware datetime objects - normalize to timezone-naive
            if len(df_clean) > 0 and hasattr(df_clean['timestamp'].iloc[0], 'tz') and df_clean['timestamp'].iloc[0].tz is not None:
                df_clean['timestamp'] = df_clean['timestamp'].dt.tz_localize(None)
            
            # Filter to date range if we got more data than requested
            df_clean = df_clean[(df_clean['timestamp'] >= start_date) & (df_clean['timestamp'] <= end_date)]
            
            if len(df_clean) == 0:
                raise ValueError(f"No data available for {symbol} in the specified date range")
            
            df = df_clean
            
            self.logger.info(f"Successfully loaded {len(df)} price data points for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading price data for {symbol}: {e}")
            raise ValueError(f"No real price data available for {symbol}: {e}")
    
    # Load all historical data sources
    def load_all_historical_data(self, start_date: datetime, end_date: datetime) -> Dict[str, pd.DataFrame]:
        self.logger.info(f"Loading all historical data from {start_date} to {end_date}")
        
        data = {}
        
        # Load EIA data
        try:
            data['eia'] = self.load_eia_historical_data(start_date, end_date)
        except Exception as e:
            self.logger.error(f"Failed to load EIA data: {e}")
            raise ValueError(f"Cannot proceed with backtesting: EIA data unavailable - {e}")
        
        # Load temperature data
        try:
            data['temperature'] = self.load_temperature_historical_data(start_date, end_date)
        except Exception as e:
            self.logger.error(f"Failed to load temperature data: {e}")
            raise ValueError(f"Cannot proceed with backtesting: Temperature data unavailable - {e}")
        
        # Load storm data
        try:
            data['storm'] = self.load_storm_historical_data(start_date, end_date)
        except Exception as e:
            self.logger.error(f"Failed to load storm data: {e}")
            raise ValueError(f"Cannot proceed with backtesting: Storm data unavailable - {e}")
        
        # Load price data for both symbols
        try:
            symbol = getattr(self.config, 'symbol', 'UNG')  # Use config symbol, default to UNG
            data['ung_price'] = self.load_price_historical_data(symbol, start_date, end_date)
        except Exception as e:
            self.logger.error(f"Failed to load {symbol} price data: {e}")
            raise ValueError(f"Cannot proceed with backtesting: {symbol} price data unavailable - {e}")
        
        try:
            data['kold_price'] = self.load_price_historical_data('KOLD', start_date, end_date)
        except Exception as e:
            self.logger.error(f"Failed to load KOLD price data: {e}")
            raise ValueError(f"Cannot proceed with backtesting: KOLD price data unavailable - {e}")
        
        # Normalize all timestamps to be timezone-naive
        self._normalize_timestamps(data)
        
        self.logger.info("Successfully loaded all historical data sources")
        return data
    
    def _normalize_timestamps(self, data: Dict[str, pd.DataFrame]) -> None:
        """Normalize all timestamps in the data to be timezone-naive"""
        for name, df in data.items():
            if df is not None and len(df) > 0:
                # Check for different timestamp column names
                timestamp_cols = ['timestamp', 'period']
                for col in timestamp_cols:
                    if col in df.columns:
                        # Normalize timezone-aware timestamps to timezone-naive
                        if hasattr(df[col].iloc[0], 'tz') and df[col].iloc[0].tz is not None:
                            df[col] = df[col].dt.tz_localize(None)
                            self.logger.debug(f"Normalized timezone for {name}.{col}")
                        break
    
    def align_data_by_date(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Align all data sources by date for consistent backtesting"""
        try:
            self.logger.info("Aligning all data sources by date")
            
            # Get the common date range
            all_dates = set()
            for df in data_dict.values():
                if 'timestamp' in df.columns:
                    all_dates.update(df['timestamp'].dt.date)
                elif 'period' in df.columns:
                    all_dates.update(df['period'].dt.date)
            
            common_dates = sorted(list(all_dates))
            
            # Align each dataset
            aligned_data = {}
            for name, df in data_dict.items():
                if 'timestamp' in df.columns:
                    df_aligned = df[df['timestamp'].dt.date.isin(common_dates)].copy()
                    df_aligned = df_aligned.sort_values('timestamp')
                elif 'period' in df.columns:
                    df_aligned = df[df['period'].dt.date.isin(common_dates)].copy()
                    df_aligned = df_aligned.sort_values('period')
                else:
                    df_aligned = df.copy()
                
                aligned_data[name] = df_aligned
            
            self.logger.info(f"Aligned {len(aligned_data)} data sources with {len(common_dates)} common dates")
            return aligned_data
            
        except Exception as e:
            self.logger.error(f"Error aligning data by date: {e}")
            return data_dict
