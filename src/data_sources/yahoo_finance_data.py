import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf
import time

class YahooFinanceDataFetcher:
    """Fetches price data using Yahoo Finance API only - no mock data"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def fetch_price_data(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Fetch price data for a symbol from Yahoo Finance using the simplest working method"""
        try:
            self.logger.info(f"Fetching {symbol} price data from Yahoo Finance")
            
            # Simple approach - just get the data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist is None or hist.empty:
                raise Exception(f"No price data returned for {symbol} from Yahoo Finance")
            
            # Convert to our format
            df = pd.DataFrame({
                'date': hist.index,
                'price': hist['Close']
            })
            
            df_clean = df.reset_index(drop=True)
            df_clean = df_clean.sort_values('date')
            
            # Handle timezone-aware datetime objects
            if len(df_clean) > 0 and hasattr(df_clean['date'].iloc[0], 'tz') and df_clean['date'].iloc[0].tz is not None:
                df_clean['date'] = df_clean['date'].dt.tz_localize(None)
            
            # Filter to date range if we got more data than requested
            df_clean = df_clean[(df_clean['date'] >= start_date) & (df_clean['date'] <= end_date)]
            
            if len(df_clean) == 0:
                raise Exception(f"No data available for {symbol} in the specified date range")
            
            self.logger.info(f"Successfully fetched {len(df_clean)} price points for {symbol} from Yahoo Finance")
            return df_clean
            
        except Exception as e:
            self.logger.error(f"Yahoo Finance failed for {symbol}: {e}")
            raise e
    
    def fetch_price_data_all_time(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch all available price data for a symbol from Yahoo Finance using the simplest working method"""
        try:
            self.logger.info(f"Fetching all available {symbol} price data from Yahoo Finance")
            
            # Simple approach - just get the data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="max")
            
            if hist is None or hist.empty:
                raise Exception(f"No price data returned for {symbol} from Yahoo Finance")
            
            # Convert to our format
            df = pd.DataFrame({
                'date': hist.index,
                'price': hist['Close']
            })
            
            df_clean = df.reset_index(drop=True)
            df_clean = df_clean.sort_values('date')
            
            # Handle timezone-aware datetime objects
            if len(df_clean) > 0 and hasattr(df_clean['date'].iloc[0], 'tz') and df_clean['date'].iloc[0].tz is not None:
                df_clean['date'] = df_clean['date'].dt.tz_localize(None)
            
            self.logger.info(f"Successfully fetched {len(df_clean)} price points for {symbol} from Yahoo Finance (all time)")
            return df_clean
            
        except Exception as e:
            self.logger.error(f"Yahoo Finance failed for {symbol}: {e}")
            raise e