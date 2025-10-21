# Fetches stock price data from Yahoo Finance API for trading and backtesting.

import logging
import requests
import pandas as pd
import yfinance as yf
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
import json
import os

class YahooFinanceDataFetcher:
    """Fetches price data using Yahoo Finance API with rate limiting and caching"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.cache_dir = "cache"
        self.cache_duration = 3600  # 1 hour cache to reduce API calls
        self.max_retries = 3  # Allow more retries with proper delays
        self.retry_delay = 60  # 60 seconds delay between retries
        self.request_delay = 5  # 5 seconds delay between requests
        self.last_request_time = 0  # Track last request time
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _enforce_request_throttling(self):
        """Enforce minimum delay between requests to avoid rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            self.logger.info(f"Throttling request - waiting {sleep_time:.1f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_cache_key(self, symbol: str, start_date: datetime, end_date: datetime) -> str:
        """Generate cache key for the request"""
        return f"{symbol}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    
    def _get_cache_file(self, cache_key: str) -> str:
        """Get cache file path"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def _is_cache_valid(self, cache_file: str) -> bool:
        """Check if cache file is still valid"""
        if not os.path.exists(cache_file):
            return False
        
        # Check if cache is older than cache_duration
        cache_time = os.path.getmtime(cache_file)
        current_time = time.time()
        return (current_time - cache_time) < self.cache_duration
    
    def _load_from_cache(self, cache_file: str) -> Optional[pd.DataFrame]:
        """Load data from cache file"""
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            df = pd.DataFrame(data['data'])
            df['date'] = pd.to_datetime(df['date'])
            self.logger.info(f"Loaded {len(df)} data points from cache")
            return df
        except Exception as e:
            self.logger.warning(f"Failed to load from cache: {e}")
            return None
    
    def _save_to_cache(self, cache_file: str, df: pd.DataFrame):
        """Save data to cache file"""
        try:
            cache_data = {
                'data': df.to_dict('records'),
                'timestamp': datetime.now().isoformat()
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            self.logger.info(f"Saved {len(df)} data points to cache")
        except Exception as e:
            self.logger.warning(f"Failed to save to cache: {e}")
    
    def _fetch_with_retry(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Fetch data with retry logic for rate limiting"""
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Fetching {symbol} price data from Yahoo Finance (attempt {attempt + 1})")
                
                # Enforce request throttling
                self._enforce_request_throttling()
                
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
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(f"Rate limited for {symbol}, waiting {wait_time} seconds before retry")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"HTTP error for {symbol}: {e}")
                    raise e
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"Rate limited for {symbol}, waiting {wait_time} seconds before retry")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"Yahoo Finance failed for {symbol}: {e}")
                    raise e
        
        # If all retries failed
        self.logger.error(f"Failed to fetch data for {symbol} after {self.max_retries} attempts")
        return None
        
    def fetch_price_data(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Fetch price data for a symbol from Yahoo Finance with caching and retry logic"""
        try:
            # Check cache first
            cache_key = self._get_cache_key(symbol, start_date, end_date)
            cache_file = self._get_cache_file(cache_key)
            
            if self._is_cache_valid(cache_file):
                cached_data = self._load_from_cache(cache_file)
                if cached_data is not None:
                    return cached_data
            
            # Fetch from API with retry logic
            df = self._fetch_with_retry(symbol, start_date, end_date)
            
            if df is not None:
                # Save to cache
                self._save_to_cache(cache_file, df)
                return df
            else:
                # If API fails, try to return cached data even if expired
                cached_data = self._load_from_cache(cache_file)
                if cached_data is not None:
                    self.logger.warning(f"Using expired cache data for {symbol}")
                    return cached_data
                
                raise Exception(f"Failed to fetch data for {symbol} and no cache available")
            
        except Exception as e:
            self.logger.error(f"Yahoo Finance failed for {symbol}: {e}")
            # Return None when Yahoo Finance is unavailable
            return None
    
    def fetch_price_data_all_time(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch all available price data for a symbol from Yahoo Finance with caching and retry logic"""
        try:
            # Use a long date range for "all time" data
            start_date = datetime(2020, 1, 1)  # Start from 2020
            end_date = datetime.now()
            
            # Check cache first
            cache_key = f"{symbol}_all_time"
            cache_file = self._get_cache_file(cache_key)
            
            if self._is_cache_valid(cache_file):
                cached_data = self._load_from_cache(cache_file)
                if cached_data is not None:
                    return cached_data
            
            # Fetch from API with retry logic
            df = self._fetch_with_retry(symbol, start_date, end_date)
            
            if df is not None:
                # Save to cache
                self._save_to_cache(cache_file, df)
                self.logger.info(f"Successfully fetched {len(df)} price points for {symbol} from Yahoo Finance (all time)")
                return df
            else:
                # If API fails, try to return cached data even if expired
                cached_data = self._load_from_cache(cache_file)
                if cached_data is not None:
                    self.logger.warning(f"Using expired cache data for {symbol}")
                    return cached_data
                
                raise Exception(f"Failed to fetch data for {symbol} and no cache available")
            
        except Exception as e:
            self.logger.error(f"Yahoo Finance failed for {symbol}: {e}")
            # Return None when Yahoo Finance is unavailable
            return None