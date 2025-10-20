import logging
from typing import Optional, Dict
import math

class PositionSizingStrategy:
    """
    Dynamic position sizing strategy based on signal strength and volatility.
    
    This strategy adjusts position sizes based on:
    - Signal strength (stronger signals = larger positions)
    - Account volatility (higher volatility = smaller positions)
    - Risk management (maximum position size limits)
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Position sizing parameters
        self.base_position_size = 1000  # Base position size in dollars
        self.max_position_size = 5000   # Maximum position size in dollars
        self.min_position_size = 100    # Minimum position size in dollars
        self.signal_strength_multiplier = 2.0  # How much signal strength affects sizing
        self.volatility_adjustment = 0.5  # How much volatility reduces position size
        
    def validate_signal(self, signal) -> bool:
        """Validates the incoming signal."""
        if signal.symbol not in [self.config.symbol, self.config.inverse_symbol]:
            self.logger.warning(f"Strategy received signal for unsupported symbol: {signal.symbol}")
            return False
        return True
    
    def execute_trade(self, signal, trader) -> Optional[Dict]:
        """
        Executes a trade with dynamic position sizing.
        
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
            
            # Get account info for volatility calculation
            account_info = trader.get_account_info()
            
            self.logger.info(f"Position Sizing Strategy - BOIL position: {boil_position}")
            self.logger.info(f"Position Sizing Strategy - KOLD position: {kold_position}")
            self.logger.info(f"Position Sizing Strategy - Account info: {account_info}")
            
            if signal.action == 'BUY':
                # Calculate dynamic position size
                position_size = self._calculate_position_size(signal, account_info)
                
                if signal.symbol == self.config.symbol:  # Buying BOIL
                    return self._execute_boil_buy(signal, trader, boil_position, kold_position, position_size)
                elif signal.symbol == self.config.inverse_symbol:  # Buying KOLD
                    return self._execute_kold_buy(signal, trader, boil_position, kold_position, position_size)
            elif signal.action == 'HOLD':
                self.logger.info("Position Sizing Strategy - Signal indicates HOLD, no action taken")
                return None
            
            self.logger.warning(f"Position Sizing Strategy - Unhandled signal action: {signal.action} for symbol {signal.symbol}")
            return None
            
        except Exception as e:
            self.logger.error(f"Position Sizing Strategy - Error during trade execution: {e}")
            return None
    
    def _calculate_position_size(self, signal, account_info) -> float:
        """
        Calculates the optimal position size based on signal strength and account volatility.
        
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
            # Use portfolio value volatility as a proxy
            portfolio_value = account_info.get('portfolio_value', 100000)
            volatility_factor = max(0.5, 1.0 - (portfolio_value / 100000) * self.volatility_adjustment)
            
            # Calculate final position size
            position_size = base_size * signal_multiplier * volatility_factor
            
            # Apply limits
            position_size = max(self.min_position_size, min(position_size, self.max_position_size))
            
            self.logger.info(f"Position Sizing Strategy - Calculated position size: ${position_size:.2f}")
            self.logger.info(f"Position Sizing Strategy - Signal strength: {signal_strength:.3f}, Multiplier: {signal_multiplier:.3f}")
            self.logger.info(f"Position Sizing Strategy - Volatility factor: {volatility_factor:.3f}")
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Position Sizing Strategy - Error calculating position size: {e}")
            return self.base_position_size
    
    def _execute_boil_buy(self, signal, trader, boil_position, kold_position, position_size) -> Optional[Dict]:
        """Handles logic for buying BOIL with dynamic position sizing."""
        # First, sell all KOLD positions
        if kold_position and kold_position['qty'] > 0:
            self.logger.info("Position Sizing Strategy - Selling all KOLD positions before buying BOIL")
            qty = int(abs(kold_position['qty']))
            trader.place_market_order('sell', qty, self.config.inverse_symbol)
        
        # Close any existing BOIL position
        if boil_position and boil_position['qty'] > 0:
            self.logger.info("Position Sizing Strategy - Closing existing BOIL position")
            qty = int(abs(boil_position['qty']))
            trader.place_market_order('sell', qty, self.config.symbol)
        
        # Calculate quantity based on dynamic position size
        current_price = trader.get_current_price(signal.symbol)
        if current_price:
            qty = int(position_size / current_price)
            self.logger.info(f"Position Sizing Strategy - Buying {qty} shares of BOIL at ${current_price:.2f} (${position_size:.2f} total)")
            return trader.place_market_order('buy', qty, signal.symbol)
        else:
            self.logger.error("Position Sizing Strategy - Could not get current price for BOIL")
            return None
    
    def _execute_kold_buy(self, signal, trader, boil_position, kold_position, position_size) -> Optional[Dict]:
        """Handles logic for buying KOLD with dynamic position sizing."""
        # First, sell all BOIL positions
        if boil_position and boil_position['qty'] > 0:
            self.logger.info("Position Sizing Strategy - Selling all BOIL positions before buying KOLD")
            qty = int(abs(boil_position['qty']))
            trader.place_market_order('sell', qty, self.config.symbol)
        
        # Close any existing KOLD position
        if kold_position and kold_position['qty'] > 0:
            self.logger.info("Position Sizing Strategy - Closing existing KOLD position")
            qty = int(abs(kold_position['qty']))
            trader.place_market_order('sell', qty, self.config.inverse_symbol)
        
        # Calculate quantity based on dynamic position size
        current_price = trader.get_current_price(signal.symbol)
        if current_price:
            qty = int(position_size / current_price)
            self.logger.info(f"Position Sizing Strategy - Buying {qty} shares of KOLD at ${current_price:.2f} (${position_size:.2f} total)")
            return trader.place_market_order('buy', qty, signal.symbol)
        else:
            self.logger.error("Position Sizing Strategy - Could not get current price for KOLD")
            return None
    
    def get_strategy_description(self) -> str:
        """Returns a description of the strategy."""
        return (
            "Dynamic Position Sizing Strategy:\n\n"
            "- Adjusts position sizes based on signal strength\n"
            "- Stronger signals result in larger positions\n"
            "- Accounts for account volatility\n"
            "- Enforces minimum and maximum position limits\n\n"
            "Benefits:\n"
            "- Maximizes returns on strong signals\n"
            "- Reduces risk during volatile periods\n"
            "- Prevents oversized positions\n"
            "- Adapts to market conditions"
        )
