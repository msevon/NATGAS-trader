import logging
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class NOAADataFetcher:
    """Fetches storm and disruption alerts from NOAA"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def fetch_weather_alerts(self) -> Optional[List[Dict]]:
        """Fetch weather alerts from NOAA API"""
        try:
            # Get alerts for the next 7 days
            params = {
                'active': 'true',
                'status': 'actual',
                'message_type': 'alert'
            }
            
            response = requests.get(self.config.noaa_api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'features' in data:
                alerts = []
                for feature in data['features']:
                    properties = feature.get('properties', {})
                    
                    # Filter for relevant alerts (storms, winter weather, etc.)
                    event_type = properties.get('event', '').lower()
                    if any(keyword in event_type for keyword in [
                        'storm', 'winter', 'blizzard', 'ice', 'freeze', 
                        'hurricane', 'tornado', 'severe'
                    ]):
                        alerts.append({
                            'event': properties.get('event', ''),
                            'severity': properties.get('severity', ''),
                            'urgency': properties.get('urgency', ''),
                            'description': properties.get('description', ''),
                            'effective': properties.get('effective', ''),
                            'expires': properties.get('expires', ''),
                            'location': properties.get('areaDesc', 'Unknown Location'),
                            'state': properties.get('state', 'Unknown State')
                        })
                
                return alerts
            
            return []
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching NOAA alerts: {e}")
            return self._get_mock_alerts()
        except Exception as e:
            self.logger.error(f"Unexpected error fetching alerts: {e}")
            return self._get_mock_alerts()
    
    def _get_mock_alerts(self) -> List[Dict]:
        """Generate mock alerts for testing when API is unavailable"""
        self.logger.info("Using mock weather alerts")
        
        # Simulate occasional storm alerts
        import random
        if random.random() < 0.3:  # 30% chance of storm alert
            return [{
                'event': 'Winter Storm Warning',
                'severity': 'Moderate',
                'urgency': 'Expected',
                'description': 'Mock winter storm affecting natural gas infrastructure',
                'effective': datetime.now().isoformat(),
                'expires': (datetime.now() + timedelta(days=2)).isoformat(),
                'location': 'Northeast Region',
                'state': 'NY'
            }]
        
        return []
    
    def calculate_storm_signal(self) -> float:
        """Calculate storm/disruption signal based on weather alerts"""
        try:
            alerts = self.fetch_weather_alerts()
            
            if not alerts:
                self.logger.info("No relevant weather alerts")
                return 0.0
            
            storm_signal = 0.0
            
            for alert in alerts:
                event = alert['event'].lower()
                severity = alert['severity'].lower()
                
                # Base signal strength based on event type
                if 'winter' in event or 'blizzard' in event:
                    base_signal = 0.3
                elif 'storm' in event:
                    base_signal = 0.2
                elif 'severe' in event:
                    base_signal = 0.15
                else:
                    base_signal = 0.1
                
                # Adjust based on severity
                if severity == 'extreme':
                    multiplier = 1.5
                elif severity == 'severe':
                    multiplier = 1.2
                elif severity == 'moderate':
                    multiplier = 1.0
                else:
                    multiplier = 0.8
                
                storm_signal += base_signal * multiplier
                
                self.logger.info(f"Alert: {alert['event']} ({severity}) - Signal: {base_signal * multiplier:.3f}")
            
            # Cap the signal at 1.0
            storm_signal = min(storm_signal, 1.0)
            
            self.logger.info(f"Total storm signal: {storm_signal:.3f}")
            
            return storm_signal
            
        except Exception as e:
            self.logger.error(f"Error calculating storm signal: {e}")
            return 0.0
