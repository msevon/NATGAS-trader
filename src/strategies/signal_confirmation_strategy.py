# Confirms trading signals by requiring multiple consecutive days of the same signal before executing trades.

import logging
from typing import Optional, Dict, List

class SignalConfirmationStrategy:
    """
    Signal confirmation strategy that requires multiple confirmations before trading.
    
    This strategy waits for:
    - Multiple consecutive signals in the same direction
    - Cross-validation between different data sources
    - Minimum signal strength threshold
    - Time-based confirmation windows
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Confirmation parameters
        self.min_consecutive_signals = 2  # Minimum consecutive signals required
        self.min_signal_strength = 3.0    # Minimum signal strength threshold
        self.confirmation_window_hours = 6  # Hours to wait for confirmation
        self.signal_history: List[Dict] = []  # Store recent signals
        
    def validate_signal(self, signal) -> bool:
        """Validates the incoming signal and checks for confirmation."""
        if signal.symbol not in [self.config.symbol, self.config.inverse_symbol]:
            self.logger.warning(f"Strategy received signal for unsupported symbol: {signal.symbol}")
            return False
        
        # Add signal to history
        self._add_signal_to_history(signal)
        
        # Check if signal meets confirmation criteria
        if self._is_signal_confirmed(signal):
            self.logger.info(f"Signal Confirmation Strategy - Signal confirmed for {signal.symbol}")
            return True
        else:
            self.logger.info(f"Signal Confirmation Strategy - Signal not yet confirmed for {signal.symbol}")
            return False
    
    def execute_trade(self, signal, trader) -> Optional[Dict]:
        """
        Executes a trade only if signal is confirmed.
        
        Args:
            signal: The trading signal object.
            trader: An instance of AlpacaTrader to execute orders.
        
        Returns:
            Optional[Dict]: The executed order details or None if no trade was made.
        """
        try:
            # Get current positions
            boil_position = trader.get_current_position(self.config.symbol)
            kold_position = trader.get_current_position(self.config.inverse_symbol)
            
            self.logger.info(f"Signal Confirmation Strategy - BOIL position: {boil_position}")
            self.logger.info(f"Signal Confirmation Strategy - KOLD position: {kold_position}")
            
            if signal.action == 'BUY':
                if signal.symbol == self.config.symbol:  # Buying BOIL
                    return self._execute_boil_buy(signal, trader, boil_position, kold_position)
                elif signal.symbol == self.config.inverse_symbol:  # Buying KOLD
                    return self._execute_kold_buy(signal, trader, boil_position, kold_position)
            elif signal.action == 'HOLD':
                self.logger.info("Signal Confirmation Strategy - Signal indicates HOLD, no action taken")
                return None
            
            self.logger.warning(f"Signal Confirmation Strategy - Unhandled signal action: {signal.action} for symbol {signal.symbol}")
            return None
            
        except Exception as e:
            self.logger.error(f"Signal Confirmation Strategy - Error during trade execution: {e}")
            return None
    
    def _add_signal_to_history(self, signal):
        """Adds a signal to the history for confirmation analysis."""
        signal_data = {
            'timestamp': signal.timestamp,
            'symbol': signal.symbol,
            'action': signal.action,
            'total_signal': signal.total_signal,
            'temperature_signal': signal.temperature_signal,
            'inventory_signal': signal.inventory_signal,
            'storm_signal': signal.storm_signal,
            'confidence': signal.confidence
        }
        
        self.signal_history.append(signal_data)
        
        # Keep only recent signals (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.signal_history = [
            s for s in self.signal_history 
            if s['timestamp'] > cutoff_time
        ]
        
        self.logger.info(f"Signal Confirmation Strategy - Added signal to history. Total signals: {len(self.signal_history)}")
    
    def _is_signal_confirmed(self, signal) -> bool:
        """
        Checks if the current signal is confirmed based on historical signals.
        
        Args:
            signal: The current trading signal object.
        
        Returns:
            bool: True if signal is confirmed, False otherwise.
        """
        try:
            # Check signal strength threshold
            if abs(signal.total_signal) < self.min_signal_strength:
                self.logger.info(f"Signal Confirmation Strategy - Signal strength {abs(signal.total_signal):.3f} below threshold {self.min_signal_strength}")
                return False
            
            # Check for consecutive signals in same direction
            recent_signals = self._get_recent_signals_for_symbol(signal.symbol)
            
            if len(recent_signals) < self.min_consecutive_signals:
                self.logger.info(f"Signal Confirmation Strategy - Only {len(recent_signals)} recent signals, need {self.min_consecutive_signals}")
                return False
            
            # Check if all recent signals are in same direction
            if not self._are_signals_consecutive(recent_signals):
                self.logger.info("Signal Confirmation Strategy - Recent signals are not consecutive in same direction")
                return False
            
            # Check signal consistency
            if not self._are_signals_consistent(recent_signals):
                self.logger.info("Signal Confirmation Strategy - Recent signals are not consistent")
                return False
            
            self.logger.info("Signal Confirmation Strategy - Signal confirmed!")
            return True
            
        except Exception as e:
            self.logger.error(f"Signal Confirmation Strategy - Error checking signal confirmation: {e}")
            return False
    
    def _get_recent_signals_for_symbol(self, symbol) -> List[Dict]:
        """Gets recent signals for a specific symbol."""
        # Get signals from the last confirmation window
        cutoff_time = datetime.now() - timedelta(hours=self.confirmation_window_hours)
        
        recent_signals = [
            s for s in self.signal_history 
            if s['symbol'] == symbol and s['timestamp'] > cutoff_time
        ]
        
        # Sort by timestamp (most recent first)
        recent_signals.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return recent_signals
    
    def _are_signals_consecutive(self, signals: List[Dict]) -> bool:
        """Checks if signals are consecutive in the same direction."""
        if len(signals) < self.min_consecutive_signals:
            return False
        
        # Check if all signals have the same action
        first_action = signals[0]['action']
        for signal in signals[:self.min_consecutive_signals]:
            if signal['action'] != first_action:
                return False
        
        return True
    
    def _are_signals_consistent(self, signals: List[Dict]) -> bool:
        """Checks if signals are consistent in strength and direction."""
        if len(signals) < self.min_consecutive_signals:
            return False
        
        # Check if signal strengths are consistent (not wildly different)
        strengths = [abs(s['total_signal']) for s in signals[:self.min_consecutive_signals]]
        avg_strength = sum(strengths) / len(strengths)
        
        # Allow 50% variation in signal strength
        for strength in strengths:
            if abs(strength - avg_strength) / avg_strength > 0.5:
                return False
        
        return True
    
    def _execute_boil_buy(self, signal, trader, boil_position, kold_position) -> Optional[Dict]:
        """Handles logic for buying BOIL with confirmation."""
        # First, sell all KOLD positions
        if kold_position and kold_position['qty'] > 0:
            self.logger.info("Signal Confirmation Strategy - Selling all KOLD positions before buying BOIL")
            qty = int(abs(kold_position['qty']))
            trader.place_market_order('sell', qty, self.config.inverse_symbol)
        
        # Close any existing BOIL position
        if boil_position and boil_position['qty'] > 0:
            self.logger.info("Signal Confirmation Strategy - Closing existing BOIL position")
            qty = int(abs(boil_position['qty']))
            trader.place_market_order('sell', qty, self.config.symbol)
        
        # Place new BOIL order
        qty = trader.calculate_order_quantity(signal.symbol)
        self.logger.info(f"Signal Confirmation Strategy - Confirmed buy signal for BOIL, placing order for {qty} shares")
        return trader.place_market_order('buy', qty, signal.symbol)
    
    def _execute_kold_buy(self, signal, trader, boil_position, kold_position) -> Optional[Dict]:
        """Handles logic for buying KOLD with confirmation."""
        # First, sell all BOIL positions
        if boil_position and boil_position['qty'] > 0:
            self.logger.info("Signal Confirmation Strategy - Selling all BOIL positions before buying KOLD")
            qty = int(abs(boil_position['qty']))
            trader.place_market_order('sell', qty, self.config.symbol)
        
        # Close any existing KOLD position
        if kold_position and kold_position['qty'] > 0:
            self.logger.info("Signal Confirmation Strategy - Closing existing KOLD position")
            qty = int(abs(kold_position['qty']))
            trader.place_market_order('sell', qty, self.config.inverse_symbol)
        
        # Place new KOLD order
        qty = trader.calculate_order_quantity(signal.symbol)
        self.logger.info(f"Signal Confirmation Strategy - Confirmed buy signal for KOLD, placing order for {qty} shares")
        return trader.place_market_order('buy', qty, signal.symbol)
    
    def get_strategy_description(self) -> str:
        """Returns a description of the strategy."""
        return (
            "Signal Confirmation Strategy:\n\n"
            "- Requires multiple consecutive signals in same direction\n"
            "- Enforces minimum signal strength threshold\n"
            "- Cross-validates signal consistency\n"
            "- Uses time-based confirmation windows\n\n"
            "Benefits:\n"
            "- Reduces false signals\n"
            "- Increases trade accuracy\n"
            "- Prevents premature entries\n"
            "- Improves risk management"
        )
