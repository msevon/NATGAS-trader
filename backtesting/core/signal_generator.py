# Generates trading signals using historical weather, inventory, and storm data for backtesting.
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Represents a historical trading signal
@dataclass
class HistoricalTradingSignal:
    timestamp: datetime
    temperature_signal: float
    inventory_signal: float
    storm_signal: float
    total_signal: float
    action: str  # 'BUY', 'SELL', 'HOLD'
    symbol: str  # 'UNG' or 'KOLD'
    confidence: float
    data_date: datetime  # The date this signal is based on

# Generates trading signals using historical data
class HistoricalSignalGenerator:
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Signal calculation parameters
        self.temperature_weight = getattr(config, 'temperature_weight', 0.4)
        self.inventory_weight = getattr(config, 'inventory_weight', 0.4)
        self.storm_weight = getattr(config, 'storm_weight', 0.2)
        
        # Signal thresholds
        self.buy_threshold = getattr(config, 'buy_threshold', 0.3)
        self.sell_threshold = getattr(config, 'sell_threshold', -0.3)
        
        # Symbols
        self.symbol = getattr(config, 'symbol', 'BOIL')  # Fixed: Use BOIL instead of UNG
        self.inverse_symbol = getattr(config, 'inverse_symbol', 'KOLD')
    
    # Calculate temperature-based signal using HDD data
    def calculate_temperature_signal(self, temperature_df: pd.DataFrame, current_date: datetime) -> float:
        try:
            # Get temperature data for the current date
            current_data = temperature_df[temperature_df['timestamp'].dt.date == current_date.date()]
            
            if current_data.empty:
                # Find the closest available day
                closest_data = self._find_closest_temperature_data(temperature_df, current_date)
                if closest_data is None:
                    self.logger.warning(f"No temperature data available for {current_date.date()} or nearby dates")
                    return 0.0
                
                current_data = closest_data
                self.logger.debug(f"Using closest temperature data from {current_data['timestamp'].iloc[0].date()} for {current_date.date()}")
            
            current_hdd = current_data['hdd'].iloc[0]
            
            # Calculate historical average HDD for comparison
            historical_avg_hdd = temperature_df['hdd'].mean()
            
            # Calculate signal: positive if colder than average (higher HDD)
            temperature_signal = (current_hdd - historical_avg_hdd) / historical_avg_hdd
            
            self.logger.debug(f"Temperature signal for {current_date.date()}: HDD={current_hdd:.2f}, Avg={historical_avg_hdd:.2f}, Signal={temperature_signal:.3f}")
            
            return temperature_signal
            
        except Exception as e:
            self.logger.error(f"Error calculating temperature signal: {e}")
            return 0.0
    
    # Calculate inventory-based signal using EIA storage data
    def calculate_inventory_signal(self, eia_df: pd.DataFrame, current_date: datetime) -> float:
        try:
            # Get the most recent EIA data before or on the current date
            available_data = eia_df[eia_df['period'] <= current_date]
            
            if available_data.empty:
                self.logger.warning(f"No EIA data available for {current_date.date()}")
                return 0.0
            
            # Use the most recent data point
            current_storage = available_data.iloc[-1]['value']
            
            # Calculate historical average
            historical_avg = eia_df['value'].mean()
            
            # Calculate signal: positive if below average (bullish for prices)
            inventory_signal = (historical_avg - current_storage) / historical_avg
            
            self.logger.debug(f"Inventory signal for {current_date.date()}: Storage={current_storage:.0f}, Avg={historical_avg:.0f}, Signal={inventory_signal:.3f}")
            
            return inventory_signal
            
        except Exception as e:
            self.logger.error(f"Error calculating inventory signal: {e}")
            return 0.0
    
    # Calculate storm-based signal using storm data
    def calculate_storm_signal(self, storm_df: pd.DataFrame, current_date: datetime) -> float:
        try:
            # Get storm data for the current date
            current_data = storm_df[storm_df['timestamp'].dt.date == current_date.date()]
            
            if current_data.empty:
                # Find the closest available day
                closest_data = self._find_closest_storm_data(storm_df, current_date)
                if closest_data is None:
                    self.logger.warning(f"No storm data available for {current_date.date()} or nearby dates")
                    return 0.0
                
                current_data = closest_data
                self.logger.debug(f"Using closest storm data from {current_data['timestamp'].iloc[0].date()} for {current_date.date()}")
            
            # Check if storm_signal column exists, otherwise use has_storm
            if 'storm_signal' in current_data.columns:
                storm_signal = current_data['storm_signal'].iloc[0]
            elif 'has_storm' in current_data.columns:
                storm_signal = 1.0 if current_data['has_storm'].iloc[0] else 0.0
            else:
                # Default to 0 if no storm signal column found
                storm_signal = 0.0
            
            self.logger.debug(f"Storm signal for {current_date.date()}: {storm_signal:.3f}")
            
            return storm_signal
            
        except Exception as e:
            self.logger.error(f"Error calculating storm signal: {e}")
            return 0.0
    
    # Calculate weighted total signal
    def calculate_total_signal(self, temp_signal: float, inventory_signal: float, storm_signal: float) -> float:
        total_signal = (
            temp_signal * self.temperature_weight +
            inventory_signal * self.inventory_weight +
            storm_signal * self.storm_weight
        )
        
        self.logger.debug(f"Signal components:")
        self.logger.debug(f"  Temperature: {temp_signal:.3f} (weight: {self.temperature_weight})")
        self.logger.debug(f"  Inventory: {inventory_signal:.3f} (weight: {self.inventory_weight})")
        self.logger.debug(f"  Storm: {storm_signal:.3f} (weight: {self.storm_weight})")
        self.logger.debug(f"  Total signal: {total_signal:.3f}")
        
        return total_signal
    
    # Determine trading action and symbol based on signal strength
    def determine_action(self, total_signal: float) -> Tuple[str, str, float]:
        if total_signal > self.buy_threshold:
            action = 'BUY'
            symbol = self.symbol  # BOIL for bullish natural gas
            confidence = min(total_signal / self.buy_threshold, 2.0)
        elif total_signal < self.sell_threshold:
            action = 'BUY'
            symbol = self.inverse_symbol  # KOLD for bearish natural gas
            confidence = min(abs(total_signal) / abs(self.sell_threshold), 2.0)
        else:
            action = 'HOLD'
            symbol = ''
            confidence = 0.0
        
        return action, symbol, confidence
    
    # Generate a trading signal for a specific date using historical data
    def generate_signal_for_date(self, historical_data: Dict[str, pd.DataFrame], current_date: datetime) -> Optional[HistoricalTradingSignal]:
        try:
            # Calculate individual signals
            temp_signal = self.calculate_temperature_signal(historical_data['temperature'], current_date)
            inventory_signal = self.calculate_inventory_signal(historical_data['eia'], current_date)
            storm_signal = self.calculate_storm_signal(historical_data['storm'], current_date)
            
            # Calculate total signal
            total_signal = self.calculate_total_signal(temp_signal, inventory_signal, storm_signal)
            
            # Determine action
            action, symbol, confidence = self.determine_action(total_signal)
            
            # Create signal
            signal = HistoricalTradingSignal(
                timestamp=current_date,
                temperature_signal=temp_signal,
                inventory_signal=inventory_signal,
                storm_signal=storm_signal,
                total_signal=total_signal,
                action=action,
                symbol=symbol,
                confidence=confidence,
                data_date=current_date
            )
            
            self.logger.debug(f"Generated signal for {current_date.date()}: {action} {symbol} (confidence: {confidence:.2f})")
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Error generating signal for {current_date.date()}: {e}")
            return None
    
    # Generate trading signals for a date range
    def generate_signals_for_period(self, historical_data: Dict[str, pd.DataFrame],
                                  start_date: datetime, end_date: datetime) -> List[HistoricalTradingSignal]:
        try:
            self.logger.info(f"Generating signals from {start_date.date()} to {end_date.date()}")
            
            signals = []
            current_date = start_date
            
            while current_date <= end_date:
                signal = self.generate_signal_for_date(historical_data, current_date)
                if signal:
                    signals.append(signal)
                
                current_date += timedelta(days=1)
            
            self.logger.info(f"Generated {len(signals)} signals for the period")
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating signals for period: {e}")
            return []
    
    # Apply signal confirmation logic (require consecutive days of same signal)
    def apply_signal_confirmation(self, signals: List[HistoricalTradingSignal],
                                min_consecutive_days: int = 2) -> List[HistoricalTradingSignal]:
        try:
            self.logger.info(f"Applying signal confirmation with {min_consecutive_days} consecutive days")
            
            confirmed_signals = []
            signal_history = []
            
            for signal in signals:
                # Add to history
                signal_history.append(signal)
                
                # Keep only recent history (last 7 days)
                cutoff_date = signal.timestamp - timedelta(days=7)
                signal_history = [s for s in signal_history if s.timestamp >= cutoff_date]
                
                # Check for confirmation
                if self._is_signal_confirmed(signal, signal_history, min_consecutive_days):
                    confirmed_signals.append(signal)
                    self.logger.debug(f"Signal confirmed for {signal.timestamp.date()}: {signal.action} {signal.symbol}")
                else:
                    # Create a HOLD signal instead
                    hold_signal = HistoricalTradingSignal(
                        timestamp=signal.timestamp,
                        temperature_signal=signal.temperature_signal,
                        inventory_signal=signal.inventory_signal,
                        storm_signal=signal.storm_signal,
                        total_signal=signal.total_signal,
                        action='HOLD',
                        symbol='',
                        confidence=0.0,
                        data_date=signal.data_date
                    )
                    confirmed_signals.append(hold_signal)
                    self.logger.debug(f"Signal not confirmed for {signal.timestamp.date()}, using HOLD")
            
            self.logger.info(f"Applied signal confirmation: {len(confirmed_signals)} signals")
            return confirmed_signals
            
        except Exception as e:
            self.logger.error(f"Error applying signal confirmation: {e}")
            return signals
    
    # Check if a signal is confirmed for the required consecutive days
    def _is_signal_confirmed(self, current_signal: HistoricalTradingSignal,
                           signal_history: List[HistoricalTradingSignal],
                           min_consecutive_days: int) -> bool:
        try:
            if current_signal.action != 'BUY':
                return False  # Only confirm BUY signals
            
            # Get recent signals for the same symbol
            recent_signals = [
                s for s in signal_history 
                if s.symbol == current_signal.symbol and 
                s.timestamp >= current_signal.timestamp - timedelta(days=min_consecutive_days)
            ]
            
            # Sort by date
            recent_signals.sort(key=lambda x: x.timestamp)
            
            if len(recent_signals) < min_consecutive_days:
                return False
            
            # Check if we have consecutive BUY signals
            consecutive_buys = 0
            for signal in recent_signals[-min_consecutive_days:]:
                if signal.action == 'BUY' and signal.symbol == current_signal.symbol:
                    consecutive_buys += 1
                else:
                    break
            
            return consecutive_buys >= min_consecutive_days
            
        except Exception as e:
            self.logger.error(f"Error checking signal confirmation: {e}")
            return False
    
    # Get a summary of generated signals
    def get_signal_summary(self, signals: List[HistoricalTradingSignal]) -> Dict[str, any]:
        try:
            if not signals:
                return {}
            
            total_signals = len(signals)
            buy_signals = len([s for s in signals if s.action == 'BUY'])
            hold_signals = len([s for s in signals if s.action == 'HOLD'])
            
            boil_signals = len([s for s in signals if s.symbol == 'UNG'])
            kold_signals = len([s for s in signals if s.symbol == 'KOLD'])
            
            avg_confidence = np.mean([s.confidence for s in signals if s.confidence > 0])
            avg_total_signal = np.mean([s.total_signal for s in signals])
            
            summary = {
                'total_signals': total_signals,
                'buy_signals': buy_signals,
                'hold_signals': hold_signals,
                'boil_signals': boil_signals,
                'kold_signals': kold_signals,
                'avg_confidence': avg_confidence,
                'avg_total_signal': avg_total_signal,
                'signal_rate': buy_signals / total_signals if total_signals > 0 else 0
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating signal summary: {e}")
            return {}
    
    # Export signals to a pandas DataFrame for analysis
    def export_signals_to_dataframe(self, signals: List[HistoricalTradingSignal]) -> pd.DataFrame:
        try:
            if not signals:
                return pd.DataFrame()
            
            data = []
            for signal in signals:
                data.append({
                    'timestamp': signal.timestamp,
                    'temperature_signal': signal.temperature_signal,
                    'inventory_signal': signal.inventory_signal,
                    'storm_signal': signal.storm_signal,
                    'total_signal': signal.total_signal,
                    'action': signal.action,
                    'symbol': signal.symbol,
                    'confidence': signal.confidence,
                    'data_date': signal.data_date
                })
            
            df = pd.DataFrame(data)
            df = df.sort_values('timestamp')
            
            self.logger.info(f"Exported {len(df)} signals to DataFrame")
            return df
            
        except Exception as e:
            self.logger.error(f"Error exporting signals to DataFrame: {e}")
            return pd.DataFrame()
            
    # Generate trading signals using historical data (wrapper method)
    def generate_signals(self, historical_data: Dict[str, pd.DataFrame]) -> List[HistoricalTradingSignal]:
        try:
            # Extract date range from the data
            start_date = None
            end_date = None
            
            for key, df in historical_data.items():
                if df is not None and len(df) > 0:
                    # Handle different column names for timestamps
                    if 'timestamp' in df.columns:
                        time_col = 'timestamp'
                    elif 'period' in df.columns:
                        time_col = 'period'
                    else:
                        self.logger.warning(f"No timestamp column found in {key} data")
                        continue
                    
                    df_start = df[time_col].min()
                    df_end = df[time_col].max()
                    
                    if start_date is None or df_start < start_date:
                        start_date = df_start
                    if end_date is None or df_end > end_date:
                        end_date = df_end
            
            if start_date is None or end_date is None:
                self.logger.error("No valid date range found in historical data")
                return []
            
            # Generate signals for the period
            signals = self.generate_signals_for_period(historical_data, start_date, end_date)
            
            # Apply signal confirmation
            confirmed_signals = self.apply_signal_confirmation(signals)
            
            return confirmed_signals
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            return []
    
    def _find_closest_temperature_data(self, temperature_df: pd.DataFrame, current_date: datetime) -> Optional[pd.DataFrame]:
        """Find the closest temperature data to the current date"""
        try:
            if temperature_df.empty:
                return None
            
            # Calculate time differences
            temperature_df = temperature_df.copy()
            temperature_df['time_diff'] = abs((temperature_df['timestamp'] - current_date).dt.total_seconds())
            
            # Find the row with minimum time difference
            closest_idx = temperature_df['time_diff'].idxmin()
            closest_row = temperature_df.loc[[closest_idx]]
            
            # Remove the temporary column
            closest_row = closest_row.drop('time_diff', axis=1)
            
            return closest_row
            
        except Exception as e:
            self.logger.error(f"Error finding closest temperature data: {e}")
            return None
    
    def _find_closest_storm_data(self, storm_df: pd.DataFrame, current_date: datetime) -> Optional[pd.DataFrame]:
        """Find the closest storm data to the current date"""
        try:
            if storm_df.empty:
                return None
            
            # Calculate time differences
            storm_df = storm_df.copy()
            storm_df['time_diff'] = abs((storm_df['timestamp'] - current_date).dt.total_seconds())
            
            # Find the row with minimum time difference
            closest_idx = storm_df['time_diff'].idxmin()
            closest_row = storm_df.loc[[closest_idx]]
            
            # Remove the temporary column
            closest_row = closest_row.drop('time_diff', axis=1)
            
            return closest_row
            
        except Exception as e:
            self.logger.error(f"Error finding closest storm data: {e}")
            return None