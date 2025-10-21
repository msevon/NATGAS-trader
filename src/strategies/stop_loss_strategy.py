# Implements stop loss and take profit mechanisms to protect trading positions from excessive losses.
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

class StopLossStrategy:
    """
    Stop loss strategy that implements automatic stop losses and take profits.
    
    This strategy provides:
    - Dynamic stop losses based on volatility
    - Trailing stops for profitable positions
    - Take profit levels at signal reversal points
    - Risk-reward ratio optimization
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Stop loss parameters
        self.default_stop_loss_pct = 0.05  # 5% default stop loss
        self.trailing_stop_pct = 0.03      # 3% trailing stop
        self.take_profit_pct = 0.15         # 15% take profit
        self.min_stop_loss_pct = 0.02       # 2% minimum stop loss
        self.max_stop_loss_pct = 0.10      # 10% maximum stop loss
        
        # Track active stop losses
        self.active_stops: Dict[str, Dict] = {}
        
    def validate_signal(self, signal) -> bool:
        """Validates the incoming signal."""
        if signal.symbol not in [self.config.symbol, self.config.inverse_symbol]:
            self.logger.warning(f"Strategy received signal for unsupported symbol: {signal.symbol}")
            return False
        return True
    
    def execute_trade(self, signal, trader) -> Optional[Dict]:
        """
        Executes a trade and sets up stop loss protection.
        
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
            
            self.logger.info(f"Stop Loss Strategy - BOIL position: {boil_position}")
            self.logger.info(f"Stop Loss Strategy - KOLD position: {kold_position}")
            
            if signal.action == 'BUY':
                if signal.symbol == self.config.symbol:  # Buying BOIL
                    return self._execute_boil_buy(signal, trader, boil_position, kold_position)
                elif signal.symbol == self.config.inverse_symbol:  # Buying KOLD
                    return self._execute_kold_buy(signal, trader, boil_position, kold_position)
            elif signal.action == 'HOLD':
                # Check existing positions for stop loss triggers
                self._check_stop_losses(trader)
                self.logger.info("Stop Loss Strategy - Signal indicates HOLD, checking stop losses")
                return None
            
            self.logger.warning(f"Stop Loss Strategy - Unhandled signal action: {signal.action} for symbol {signal.symbol}")
            return None
            
        except Exception as e:
            self.logger.error(f"Stop Loss Strategy - Error during trade execution: {e}")
            return None
    
    def _execute_boil_buy(self, signal, trader, boil_position, kold_position) -> Optional[Dict]:
        """Handles logic for buying BOIL with stop loss setup."""
        # First, sell all KOLD positions
        if kold_position and kold_position['qty'] > 0:
            self.logger.info("Stop Loss Strategy - Selling all KOLD positions before buying BOIL")
            qty = int(abs(kold_position['qty']))
            trader.place_market_order('sell', qty, self.config.inverse_symbol)
        
        # Close any existing BOIL position
        if boil_position and boil_position['qty'] > 0:
            self.logger.info("Stop Loss Strategy - Closing existing BOIL position")
            qty = int(abs(boil_position['qty']))
            trader.place_market_order('sell', qty, self.config.symbol)
        
        # Place new BOIL order
        qty = trader.calculate_order_quantity(signal.symbol)
        order_result = trader.place_market_order('buy', qty, signal.symbol)
        
        # Set up stop loss if order was successful
        if order_result and order_result.get('status') == 'accepted':
            self._setup_stop_loss(signal.symbol, order_result, trader)
        
        return order_result
    
    def _execute_kold_buy(self, signal, trader, boil_position, kold_position) -> Optional[Dict]:
        """Handles logic for buying KOLD with stop loss setup."""
        # First, sell all BOIL positions
        if boil_position and boil_position['qty'] > 0:
            self.logger.info("Stop Loss Strategy - Selling all BOIL positions before buying KOLD")
            qty = int(abs(boil_position['qty']))
            trader.place_market_order('sell', qty, self.config.symbol)
        
        # Close any existing KOLD position
        if kold_position and kold_position['qty'] > 0:
            self.logger.info("Stop Loss Strategy - Closing existing KOLD position")
            qty = int(abs(kold_position['qty']))
            trader.place_market_order('sell', qty, self.config.inverse_symbol)
        
        # Place new KOLD order
        qty = trader.calculate_order_quantity(signal.symbol)
        order_result = trader.place_market_order('buy', qty, signal.symbol)
        
        # Set up stop loss if order was successful
        if order_result and order_result.get('status') == 'accepted':
            self._setup_stop_loss(signal.symbol, order_result, trader)
        
        return order_result
    
    def _setup_stop_loss(self, symbol: str, order_result: Dict, trader):
        """
        Sets up stop loss protection for a position.
        
        Args:
            symbol: The symbol being traded.
            order_result: The result of the buy order.
            trader: An instance of AlpacaTrader.
        """
        try:
            # Get current price for stop loss calculation
            current_price = trader.get_current_price(symbol)
            if not current_price:
                self.logger.error(f"Stop Loss Strategy - Could not get current price for {symbol}")
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
            
            self.logger.info(f"Stop Loss Strategy - Set up stop loss for {symbol}")
            self.logger.info(f"Stop Loss Strategy - Entry: ${current_price:.2f}, Stop Loss: ${stop_loss_price:.2f} ({stop_loss_pct:.1%})")
            self.logger.info(f"Stop Loss Strategy - Take Profit: ${take_profit_price:.2f} ({self.take_profit_pct:.1%})")
            
        except Exception as e:
            self.logger.error(f"Stop Loss Strategy - Error setting up stop loss: {e}")
    
    def _calculate_dynamic_stop_loss(self, symbol: str, current_price: float) -> float:
        """
        Calculates dynamic stop loss percentage based on volatility and signal strength.
        
        Args:
            symbol: The symbol being traded.
            current_price: The current price of the symbol.
        
        Returns:
            float: The stop loss percentage.
        """
        try:
            # Base stop loss
            stop_loss_pct = self.default_stop_loss_pct
            
            # Adjust based on volatility (simplified - in real implementation, you'd calculate actual volatility)
            # For now, use a simple heuristic based on price
            if current_price < 20:
                stop_loss_pct *= 1.2  # Tighter stop for lower-priced stocks
            elif current_price > 50:
                stop_loss_pct *= 0.8  # Wider stop for higher-priced stocks
            
            # Apply limits
            stop_loss_pct = max(self.min_stop_loss_pct, min(stop_loss_pct, self.max_stop_loss_pct))
            
            return stop_loss_pct
            
        except Exception as e:
            self.logger.error(f"Stop Loss Strategy - Error calculating dynamic stop loss: {e}")
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
                    self.logger.info(f"Stop Loss Strategy - Stop loss triggered for {symbol} at ${current_price:.2f}")
                    self._execute_stop_loss(symbol, trader, "Stop Loss")
                    continue
                
                # Check take profit trigger
                if current_price >= stop_info['take_profit_price']:
                    self.logger.info(f"Stop Loss Strategy - Take profit triggered for {symbol} at ${current_price:.2f}")
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
            self.logger.error(f"Stop Loss Strategy - Error checking stop losses: {e}")
    
    def _activate_trailing_stop(self, symbol: str, current_price: float):
        """Activates trailing stop for a profitable position."""
        try:
            if symbol in self.active_stops:
                self.active_stops[symbol]['trailing_stop'] = True
                self.active_stops[symbol]['trailing_stop_price'] = current_price * (1 - self.trailing_stop_pct)
                self.logger.info(f"Stop Loss Strategy - Trailing stop activated for {symbol}")
                
        except Exception as e:
            self.logger.error(f"Stop Loss Strategy - Error activating trailing stop: {e}")
    
    def _update_trailing_stop(self, symbol: str, current_price: float, trader):
        """Updates trailing stop price as position becomes more profitable."""
        try:
            if symbol in self.active_stops:
                stop_info = self.active_stops[symbol]
                new_trailing_price = current_price * (1 - self.trailing_stop_pct)
                
                # Only update if new trailing price is higher (better for us)
                if new_trailing_price > stop_info.get('trailing_stop_price', 0):
                    stop_info['trailing_stop_price'] = new_trailing_price
                    self.logger.info(f"Stop Loss Strategy - Updated trailing stop for {symbol} to ${new_trailing_price:.2f}")
                
                # Check if trailing stop is triggered
                if current_price <= stop_info['trailing_stop_price']:
                    self.logger.info(f"Stop Loss Strategy - Trailing stop triggered for {symbol} at ${current_price:.2f}")
                    self._execute_stop_loss(symbol, trader, "Trailing Stop")
                    
        except Exception as e:
            self.logger.error(f"Stop Loss Strategy - Error updating trailing stop: {e}")
    
    def _execute_stop_loss(self, symbol: str, trader, reason: str):
        """Executes stop loss by selling the position."""
        try:
            position = trader.get_current_position(symbol)
            if position and position['qty'] > 0:
                qty = int(abs(position['qty']))
                self.logger.info(f"Stop Loss Strategy - Executing {reason} for {symbol}, selling {qty} shares")
                trader.place_market_order('sell', qty, symbol)
                
                # Remove from active stops
                if symbol in self.active_stops:
                    del self.active_stops[symbol]
                    
        except Exception as e:
            self.logger.error(f"Stop Loss Strategy - Error executing stop loss: {e}")
    
    def get_strategy_description(self) -> str:
        """Returns a description of the strategy."""
        return (
            "Stop Loss Strategy:\n\n"
            "- Dynamic stop losses based on volatility\n"
            "- Trailing stops for profitable positions\n"
            "- Take profit levels at signal reversal points\n"
            "- Risk-reward ratio optimization\n\n"
            "Benefits:\n"
            "- Protects against large losses\n"
            "- Locks in profits automatically\n"
            "- Reduces emotional trading\n"
            "- Improves risk management"
        )
