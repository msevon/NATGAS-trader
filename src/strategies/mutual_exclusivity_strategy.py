# Ensures mutual exclusivity between BOIL and KOLD positions by closing opposite positions before opening new ones.

import logging
from typing import Optional, Dict, List
from datetime import datetime

class MutualExclusivityStrategy:
    """Trading strategy that enforces mutual exclusivity between BOIL and KOLD positions"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def execute_trade(self, signal, trader) -> Optional[Dict]:
        """Execute trade based on signal with mutual exclusivity strategy"""
        try:
            # Check current positions for both symbols
            boil_position = trader.get_current_position(trader.config.symbol)  # BOIL
            kold_position = trader.get_current_position(trader.config.inverse_symbol)  # KOLD
            
            account_info = trader.get_account_info()
            
            self.logger.info(f"BOIL position: {boil_position}")
            self.logger.info(f"KOLD position: {kold_position}")
            self.logger.info(f"Account info: {account_info}")
            
            if signal.action == 'BUY':
                # Mutual exclusivity strategy: Buy BOIL -> Sell all KOLD, Buy KOLD -> Sell all BOIL
                if signal.symbol == self.config.symbol:  # Buying BOIL
                    return self._execute_boil_buy(signal, trader, boil_position, kold_position)
                    
                elif signal.symbol == self.config.inverse_symbol:  # Buying KOLD
                    return self._execute_kold_buy(signal, trader, boil_position, kold_position)
                
            else:  # HOLD
                self.logger.info("Signal indicates HOLD, no action taken")
                return None
                
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            return None
    
    def _execute_boil_buy(self, signal, trader, boil_position, kold_position) -> Optional[Dict]:
        """Execute BOIL buy with mutual exclusivity"""
        try:
            # First, sell all KOLD positions
            if kold_position and kold_position['qty'] > 0:
                self.logger.info("Mutual exclusivity: Selling all KOLD positions before buying BOIL")
                qty = int(abs(kold_position['qty']))
                trader.place_market_order('sell', qty, self.config.inverse_symbol)
            
            # Close any existing BOIL position
            if boil_position and boil_position['qty'] > 0:
                self.logger.info("Closing existing BOIL position")
                qty = int(abs(boil_position['qty']))
                trader.place_market_order('sell', qty, self.config.symbol)
            
            # Place new BOIL order
            qty = trader.calculate_order_quantity(signal.symbol)
            return trader.place_market_order('buy', qty, signal.symbol)
            
        except Exception as e:
            self.logger.error(f"Error executing BOIL buy: {e}")
            return None
    
    def _execute_kold_buy(self, signal, trader, boil_position, kold_position) -> Optional[Dict]:
        """Execute KOLD buy with mutual exclusivity"""
        try:
            # First, sell all BOIL positions
            if boil_position and boil_position['qty'] > 0:
                self.logger.info("Mutual exclusivity: Selling all BOIL positions before buying KOLD")
                qty = int(abs(boil_position['qty']))
                trader.place_market_order('sell', qty, self.config.symbol)
            
            # Close any existing KOLD position
            if kold_position and kold_position['qty'] > 0:
                self.logger.info("Closing existing KOLD position")
                qty = int(abs(kold_position['qty']))
                trader.place_market_order('sell', qty, self.config.inverse_symbol)
            
            # Place new KOLD order
            qty = trader.calculate_order_quantity(signal.symbol)
            return trader.place_market_order('buy', qty, signal.symbol)
            
        except Exception as e:
            self.logger.error(f"Error executing KOLD buy: {e}")
            return None
    
    def get_strategy_description(self) -> str:
        """Get a description of this trading strategy"""
        return """
        Mutual Exclusivity Strategy:
        
        - Only one of BOIL or KOLD positions can be held at a time
        - When buying BOIL: Sell all KOLD positions first, then buy BOIL
        - When buying KOLD: Sell all BOIL positions first, then buy KOLD
        - HOLD signals result in no action
        
        Benefits:
        - Prevents conflicting bullish/bearish positions
        - Maximizes capital efficiency
        - Creates clear directional bias
        - Reduces portfolio complexity
        """
    
    def validate_signal(self, signal) -> bool:
        """Validate that the signal is compatible with this strategy"""
        if signal.action == 'BUY':
            if signal.symbol not in [self.config.symbol, self.config.inverse_symbol]:
                self.logger.warning(f"Signal symbol {signal.symbol} not supported by strategy")
                return False
        return True
