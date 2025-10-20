import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

class UnifiedStrategy:
    """
    Unified trading strategy that combines all strategies:
    - Signal confirmation (2 consecutive days)
    - Dynamic position sizing
    - Stop loss protection
    - Mutual exclusivity (main strategy)
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Signal confirmation parameters
        self.min_consecutive_days = 2  # Require 2 consecutive days of same signal
        self.signal_history: List[Dict] = []  # Store daily signals
        
        # Position sizing parameters
        self.base_position_size = 1000  # Base position size in dollars
        self.max_position_size = 5000   # Maximum position size in dollars
        self.min_position_size = 100    # Minimum position size in dollars
        self.signal_strength_multiplier = 2.0  # How much signal strength affects sizing
        
        # Stop loss parameters
        self.default_stop_loss_pct = 0.05  # 5% default stop loss
        self.trailing_stop_pct = 0.03      # 3% trailing stop
        self.take_profit_pct = 0.15         # 15% take profit
        self.min_stop_loss_pct = 0.02       # 2% minimum stop loss
        self.max_stop_loss_pct = 0.10      # 10% maximum stop loss
        
        # Track active stop losses
        self.active_stops: Dict[str, Dict] = {}
        
    def validate_signal(self, signal) -> bool:
        """
        Validates the incoming signal and checks for 2-day confirmation.
        Main strategy: Follow the signal if confirmed for 2 consecutive days.
        """
        if signal.symbol not in [self.config.symbol, self.config.inverse_symbol]:
            self.logger.warning(f"Unified Strategy - Unsupported symbol: {signal.symbol}")
            return False
        
        # Add signal to daily history
        self._add_daily_signal(signal)
        
        # Check if signal is confirmed for 2 consecutive days
        if self._is_signal_confirmed_for_two_days(signal):
            self.logger.info(f"Unified Strategy - Signal confirmed for 2 consecutive days: {signal.symbol}")
            return True
        else:
            self.logger.info(f"Unified Strategy - Signal not yet confirmed for 2 consecutive days: {signal.symbol}")
            return False
    
    def execute_trade(self, signal, trader) -> Optional[Dict]:
        """
        Executes a trade using unified strategy:
        1. Signal confirmation (2 consecutive days)
        2. Dynamic position sizing
        3. Stop loss protection
        4. Mutual exclusivity (main strategy)
        """
        try:
            # Get current positions
            boil_position = trader.get_current_position(self.config.symbol)
            kold_position = trader.get_current_position(self.config.inverse_symbol)
            
            self.logger.info(f"Unified Strategy - BOIL position: {boil_position}")
            self.logger.info(f"Unified Strategy - KOLD position: {kold_position}")
            
            if signal.action == 'BUY':
                # Calculate dynamic position size
                account_info = trader.get_account_info()
                position_size = self._calculate_dynamic_position_size(signal, account_info)
                
                if signal.symbol == self.config.symbol:  # Buying BOIL
                    return self._execute_boil_buy_unified(signal, trader, boil_position, kold_position, position_size)
                elif signal.symbol == self.config.inverse_symbol:  # Buying KOLD
                    return self._execute_kold_buy_unified(signal, trader, boil_position, kold_position, position_size)
            elif signal.action == 'HOLD':
                # Check existing positions for stop loss triggers
                self._check_stop_losses(trader)
                self.logger.info("Unified Strategy - Signal indicates HOLD, checking stop losses")
                return None
            
            self.logger.warning(f"Unified Strategy - Unhandled signal action: {signal.action} for symbol {signal.symbol}")
            return None
            
        except Exception as e:
            self.logger.error(f"Unified Strategy - Error during trade execution: {e}")
            return None
    
    def _add_daily_signal(self, signal):
        """Adds a daily signal to the history for confirmation analysis."""
        signal_data = {
            'date': datetime.now().date(),
            'timestamp': signal.timestamp,
            'symbol': signal.symbol,
            'action': signal.action,
            'total_signal': signal.total_signal,
            'temperature_signal': signal.temperature_signal,
            'inventory_signal': signal.inventory_signal,
            'storm_signal': signal.storm_signal,
            'confidence': signal.confidence
        }
        
        # Remove any existing signal for today (in case bot runs multiple times)
        today = datetime.now().date()
        self.signal_history = [s for s in self.signal_history if s['date'] != today]
        
        # Add new signal
        self.signal_history.append(signal_data)
        
        # Keep only last 7 days of history
        cutoff_date = today - timedelta(days=7)
        self.signal_history = [s for s in self.signal_history if s['date'] >= cutoff_date]
        
        self.logger.info(f"Unified Strategy - Added daily signal. Total signals: {len(self.signal_history)}")
    
    def _is_signal_confirmed_for_two_days(self, signal) -> bool:
        """
        Checks if the current signal is confirmed for 2 consecutive days.
        
        Args:
            signal: The current trading signal object.
        
        Returns:
            bool: True if signal is confirmed for 2 consecutive days, False otherwise.
        """
        try:
            # Get signals for the same symbol from the last 2 days
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            recent_signals = [
                s for s in self.signal_history 
                if s['symbol'] == signal.symbol and s['date'] in [today, yesterday]
            ]
            
            # Sort by date (oldest first)
            recent_signals.sort(key=lambda x: x['date'])
            
            if len(recent_signals) < 2:
                self.logger.info(f"Unified Strategy - Only {len(recent_signals)} recent signals, need 2 consecutive days")
                return False
            
            # Check if we have signals for both today and yesterday
            signal_dates = [s['date'] for s in recent_signals]
            if today not in signal_dates or yesterday not in signal_dates:
                self.logger.info("Unified Strategy - Missing signals for consecutive days")
                return False
            
            # Check if both signals have the same action
            today_signal = next(s for s in recent_signals if s['date'] == today)
            yesterday_signal = next(s for s in recent_signals if s['date'] == yesterday)
            
            if today_signal['action'] != yesterday_signal['action']:
                self.logger.info("Unified Strategy - Consecutive day signals have different actions")
                return False
            
            # Check if both signals are BUY signals (we only trade on BUY)
            if today_signal['action'] != 'BUY':
                self.logger.info("Unified Strategy - Consecutive day signals are not BUY signals")
                return False
            
            # Check signal consistency (not wildly different)
            today_strength = abs(today_signal['total_signal'])
            yesterday_strength = abs(yesterday_signal['total_signal'])
            
            # Allow 50% variation in signal strength
            if abs(today_strength - yesterday_strength) / max(today_strength, yesterday_strength) > 0.5:
                self.logger.info("Unified Strategy - Consecutive day signals have inconsistent strength")
                return False
            
            self.logger.info("Unified Strategy - Signal confirmed for 2 consecutive days!")
            return True
            
        except Exception as e:
            self.logger.error(f"Unified Strategy - Error checking 2-day confirmation: {e}")
            return False
    
    def _calculate_dynamic_position_size(self, signal, account_info) -> float:
        """
        Calculates dynamic position size based on signal strength and account info.
        
        Args:
            signal: The trading signal object.
            account_info: Account information from Alpaca.
        
        Returns:
            float: The calculated position size in dollars.
        """
        try:
            # Base position size
            base_size = self.base_position_size
            
            # Adjust for signal strength (stronger signals = larger positions)
            signal_strength = abs(signal.total_signal)
            signal_multiplier = min(signal_strength / 5.0, self.signal_strength_multiplier)  # Cap at 2x
            
            # Adjust for account volatility (higher volatility = smaller positions)
            portfolio_value = account_info.get('portfolio_value', 100000)
            volatility_factor = max(0.5, 1.0 - (portfolio_value / 100000) * 0.5)
            
            # Calculate final position size
            position_size = base_size * signal_multiplier * volatility_factor
            
            # Apply limits
            position_size = max(self.min_position_size, min(position_size, self.max_position_size))
            
            self.logger.info(f"Unified Strategy - Calculated position size: ${position_size:.2f}")
            self.logger.info(f"Unified Strategy - Signal strength: {signal_strength:.3f}, Multiplier: {signal_multiplier:.3f}")
            self.logger.info(f"Unified Strategy - Volatility factor: {volatility_factor:.3f}")
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Unified Strategy - Error calculating position size: {e}")
            return self.base_position_size
    
    def _execute_boil_buy_unified(self, signal, trader, boil_position, kold_position, position_size) -> Optional[Dict]:
        """Handles unified logic for buying BOIL with all strategies."""
        # 1. Mutual exclusivity: Sell all KOLD positions first
        if kold_position and kold_position['qty'] > 0:
            self.logger.info("Unified Strategy - Mutual exclusivity: Selling all KOLD positions before buying BOIL")
            qty = int(abs(kold_position['qty']))
            trader.place_market_order('sell', qty, self.config.inverse_symbol)
        
        # Close any existing BOIL position
        if boil_position and boil_position['qty'] > 0:
            self.logger.info("Unified Strategy - Closing existing BOIL position")
            qty = int(abs(boil_position['qty']))
            trader.place_market_order('sell', qty, self.config.symbol)
        
        # 2. Dynamic position sizing: Calculate quantity based on position size
        current_price = trader.get_current_price(signal.symbol)
        if current_price:
            qty = int(position_size / current_price)
            self.logger.info(f"Unified Strategy - Buying {qty} shares of BOIL at ${current_price:.2f} (${position_size:.2f} total)")
            order_result = trader.place_market_order('buy', qty, signal.symbol)
            
            # 3. Stop loss protection: Set up stop loss if order was successful
            if order_result and order_result.get('status') == 'accepted':
                self._setup_stop_loss(signal.symbol, order_result, trader)
            
            return order_result
        else:
            self.logger.error("Unified Strategy - Could not get current price for BOIL")
            return None
    
    def _execute_kold_buy_unified(self, signal, trader, boil_position, kold_position, position_size) -> Optional[Dict]:
        """Handles unified logic for buying KOLD with all strategies."""
        # 1. Mutual exclusivity: Sell all BOIL positions first
        if boil_position and boil_position['qty'] > 0:
            self.logger.info("Unified Strategy - Mutual exclusivity: Selling all BOIL positions before buying KOLD")
            qty = int(abs(boil_position['qty']))
            trader.place_market_order('sell', qty, self.config.symbol)
        
        # Close any existing KOLD position
        if kold_position and kold_position['qty'] > 0:
            self.logger.info("Unified Strategy - Closing existing KOLD position")
            qty = int(abs(kold_position['qty']))
            trader.place_market_order('sell', qty, self.config.inverse_symbol)
        
        # 2. Dynamic position sizing: Calculate quantity based on position size
        current_price = trader.get_current_price(signal.symbol)
        if current_price:
            qty = int(position_size / current_price)
            self.logger.info(f"Unified Strategy - Buying {qty} shares of KOLD at ${current_price:.2f} (${position_size:.2f} total)")
            order_result = trader.place_market_order('buy', qty, signal.symbol)
            
            # 3. Stop loss protection: Set up stop loss if order was successful
            if order_result and order_result.get('status') == 'accepted':
                self._setup_stop_loss(signal.symbol, order_result, trader)
            
            return order_result
        else:
            self.logger.error("Unified Strategy - Could not get current price for KOLD")
            return None
    
    def _setup_stop_loss(self, symbol: str, order_result: Dict, trader):
        """Sets up stop loss protection for a position."""
        try:
            # Get current price for stop loss calculation
            current_price = trader.get_current_price(symbol)
            if not current_price:
                self.logger.error(f"Unified Strategy - Could not get current price for {symbol}")
                return
            
            # Calculate stop loss price
            stop_loss_pct = self._calculate_dynamic_stop_loss(symbol, current_price)
            stop_loss_price = current_price * (1 - stop_loss_pct)
            
            # Calculate take profit price
            take_profit_price = current_price * (1 + self.take_profit_pct)
            
            # Store stop loss information
            self.active_stops[symbol] = {
                'entry_price': current_price,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'stop_loss_pct': stop_loss_pct,
                'order_id': order_result.get('order_id'),
                'timestamp': datetime.now(),
                'trailing_stop': False
            }
            
            self.logger.info(f"Unified Strategy - Set up stop loss for {symbol}")
            self.logger.info(f"Unified Strategy - Entry: ${current_price:.2f}, Stop Loss: ${stop_loss_price:.2f} ({stop_loss_pct:.1%})")
            self.logger.info(f"Unified Strategy - Take Profit: ${take_profit_price:.2f} ({self.take_profit_pct:.1%})")
            
        except Exception as e:
            self.logger.error(f"Unified Strategy - Error setting up stop loss: {e}")
    
    def _calculate_dynamic_stop_loss(self, symbol: str, current_price: float) -> float:
        """Calculates dynamic stop loss percentage based on volatility."""
        try:
            # Base stop loss
            stop_loss_pct = self.default_stop_loss_pct
            
            # Adjust based on volatility (simplified)
            if current_price < 20:
                stop_loss_pct *= 1.2  # Tighter stop for lower-priced stocks
            elif current_price > 50:
                stop_loss_pct *= 0.8  # Wider stop for higher-priced stocks
            
            # Apply limits
            stop_loss_pct = max(self.min_stop_loss_pct, min(stop_loss_pct, self.max_stop_loss_pct))
            
            return stop_loss_pct
            
        except Exception as e:
            self.logger.error(f"Unified Strategy - Error calculating dynamic stop loss: {e}")
            return self.default_stop_loss_pct
    
    def _check_stop_losses(self, trader):
        """Checks all active stop losses and executes if triggered."""
        try:
            for symbol, stop_info in list(self.active_stops.items()):
                # Get current position
                position = trader.get_current_position(symbol)
                if not position or position['qty'] <= 0:
                    # Position no longer exists, remove stop loss
                    del self.active_stops[symbol]
                    continue
                
                # Get current price
                current_price = trader.get_current_price(symbol)
                if not current_price:
                    continue
                
                # Check stop loss trigger
                if current_price <= stop_info['stop_loss_price']:
                    self.logger.info(f"Unified Strategy - Stop loss triggered for {symbol} at ${current_price:.2f}")
                    self._execute_stop_loss(symbol, trader, "Stop Loss")
                    continue
                
                # Check take profit trigger
                if current_price >= stop_info['take_profit_price']:
                    self.logger.info(f"Unified Strategy - Take profit triggered for {symbol} at ${current_price:.2f}")
                    self._execute_stop_loss(symbol, trader, "Take Profit")
                    continue
                
                # Check for trailing stop activation
                if not stop_info['trailing_stop']:
                    profit_pct = (current_price - stop_info['entry_price']) / stop_info['entry_price']
                    if profit_pct >= 0.05:  # 5% profit threshold for trailing stop
                        self._activate_trailing_stop(symbol, current_price)
                
                # Update trailing stop if active
                if stop_info['trailing_stop']:
                    self._update_trailing_stop(symbol, current_price, trader)
                    
        except Exception as e:
            self.logger.error(f"Unified Strategy - Error checking stop losses: {e}")
    
    def _activate_trailing_stop(self, symbol: str, current_price: float):
        """Activates trailing stop for a profitable position."""
        try:
            if symbol in self.active_stops:
                self.active_stops[symbol]['trailing_stop'] = True
                self.active_stops[symbol]['trailing_stop_price'] = current_price * (1 - self.trailing_stop_pct)
                self.logger.info(f"Unified Strategy - Trailing stop activated for {symbol}")
                
        except Exception as e:
            self.logger.error(f"Unified Strategy - Error activating trailing stop: {e}")
    
    def _update_trailing_stop(self, symbol: str, current_price: float, trader):
        """Updates trailing stop price as position becomes more profitable."""
        try:
            if symbol in self.active_stops:
                stop_info = self.active_stops[symbol]
                new_trailing_price = current_price * (1 - self.trailing_stop_pct)
                
                # Only update if new trailing price is higher (better for us)
                if new_trailing_price > stop_info.get('trailing_stop_price', 0):
                    stop_info['trailing_stop_price'] = new_trailing_price
                    self.logger.info(f"Unified Strategy - Updated trailing stop for {symbol} to ${new_trailing_price:.2f}")
                
                # Check if trailing stop is triggered
                if current_price <= stop_info['trailing_stop_price']:
                    self.logger.info(f"Unified Strategy - Trailing stop triggered for {symbol} at ${current_price:.2f}")
                    self._execute_stop_loss(symbol, trader, "Trailing Stop")
                    
        except Exception as e:
            self.logger.error(f"Unified Strategy - Error updating trailing stop: {e}")
    
    def _execute_stop_loss(self, symbol: str, trader, reason: str):
        """Executes stop loss by selling the position."""
        try:
            position = trader.get_current_position(symbol)
            if position and position['qty'] > 0:
                qty = int(abs(position['qty']))
                self.logger.info(f"Unified Strategy - Executing {reason} for {symbol}, selling {qty} shares")
                trader.place_market_order('sell', qty, symbol)
                
                # Remove from active stops
                if symbol in self.active_stops:
                    del self.active_stops[symbol]
                    
        except Exception as e:
            self.logger.error(f"Unified Strategy - Error executing stop loss: {e}")
    
    def get_strategy_description(self) -> str:
        """Returns a description of the unified strategy."""
        return (
            "Unified Trading Strategy:\n\n"
            "Main Strategy: Follow the signal with mutual exclusivity\n"
            "Signal Confirmation: Require 2 consecutive days of same signal\n"
            "Dynamic Position Sizing: Adjust size based on signal strength\n"
            "Stop Loss Protection: Automatic stop losses and take profits\n\n"
            "Benefits:\n"
            "- Reduces false signals with 2-day confirmation\n"
            "- Maximizes returns with dynamic position sizing\n"
            "- Protects against losses with stop losses\n"
            "- Maintains clear directional bias\n"
            "- Runs once per day for consistent execution"
        )
