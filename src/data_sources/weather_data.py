# Fetches weather data and calculates heating degree days for temperature-based trading signals.

import logging
import requests
from typing import Optional, Dict

class WeatherDataFetcher:
    """Fetches weather data and calculates Heating Degree Days (HDD)"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def fetch_weather_forecast(self, region: str, days: int = 7) -> Optional[Dict]:
        """Fetch weather forecast for a specific region"""
        try:
            lat, lon = region.split(',')
            params = {
                'latitude': lat,
                'longitude': lon,
                'daily': 'temperature_2m_max,temperature_2m_min',
                'timezone': 'America/New_York',
                'forecast_days': days
            }
            
            response = requests.get(self.config.weather_api_url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching weather data for {region}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error fetching weather data: {e}")
            return None
    
    def calculate_hdd(self, temp_max: float, temp_min: float, base_temp: float = 65.0) -> float:
        """Calculate Heating Degree Days for a day"""
        avg_temp = (temp_max + temp_min) / 2
        hdd = max(0, base_temp - avg_temp)
        return hdd
    
    def get_regional_hdd_signal(self) -> float:
        """Calculate HDD-based temperature signal for all regions"""
        try:
            total_hdd = 0
            valid_regions = 0
            
            for region in self.config.weather_regions:
                weather_data = self.fetch_weather_forecast(region)
                
                if weather_data and 'daily' in weather_data:
                    daily_data = weather_data['daily']
                    temps_max = daily_data['temperature_2m_max']
                    temps_min = daily_data['temperature_2m_min']
                    
                    region_hdd = 0
                    for temp_max, temp_min in zip(temps_max, temps_min):
                        region_hdd += self.calculate_hdd(temp_max, temp_min)
                    
                    total_hdd += region_hdd
                    valid_regions += 1
                    
                    self.logger.info(f"Region {region}: HDD = {region_hdd:.2f}")
            
            if valid_regions == 0:
                self.logger.warning("No valid weather data received")
                return 0.0
            
            avg_hdd = total_hdd / valid_regions
            
            # Historical average HDD for comparison (simplified - in production, use historical data)
            historical_avg_hdd = 25.0  # Typical winter HDD
            
            # Calculate signal: positive if colder than average
            hdd_signal = (avg_hdd - historical_avg_hdd) / historical_avg_hdd
            
            self.logger.info(f"Average HDD: {avg_hdd:.2f}, Signal: {hdd_signal:.3f}")
            
            return hdd_signal
            
        except Exception as e:
            self.logger.error(f"Error calculating HDD signal: {e}")
            return 0.0
