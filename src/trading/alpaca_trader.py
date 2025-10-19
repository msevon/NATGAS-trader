import logging
import alpaca_trade_api as tradeapi
from datetime import datetime
from typing import Optional, Dict, List
import time

class AlpacaTrader:
    """Handles trading operations through Alpaca API"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize Alpaca API
        self.api = tradeapi.REST(
            self.config.alpaca_api_key,
            self.config.alpaca_secret_key,
            self.config.alpaca_base_url,
            api_version='v2'
        )
        
        # Verify connection
        try:
            account = self.api.get_account()
            self.logger.info(f"Connected to Alpaca. Account status: {account.status}")
            self.logger.info(f"Buying power: ${float(account.buying_power):,.2f}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Alpaca API: {e}")
            raise
    
    def get_current_position(self, symbol: str = None) -> Optional[Dict]:
        """Get current position for the specified symbol"""
        if symbol is None:
            symbol = self.config.symbol
            
        try:
            position = self.api.get_position(symbol)
            return {
                'symbol': position.symbol,
                'qty': float(position.qty),
                'market_value': float(position.market_value),
                'avg_entry_price': float(position.avg_entry_price),
                'unrealized_pl': float(position.unrealized_pl),
                'unrealized_plpc': float(position.unrealized_plpc)
            }
        except Exception as e:
            # Position might not exist
            if "position does not exist" in str(e).lower():
                return None
            self.logger.error(f"Error getting position for {symbol}: {e}")
            return None
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        try:
            account = self.api.get_account()
            return {
                'equity': float(account.equity),
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value)
            }
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
            return {}
    
    def place_market_order(self, side: str, qty: int, symbol: str = None) -> Optional[Dict]:
        """Place a market order"""
        if symbol is None:
            symbol = self.config.symbol
            
        try:
            self.logger.info(f"Placing {side} order for {qty} shares of {symbol}")
            
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='day'
            )
            
            # Wait for order to fill
            time.sleep(2)
            
            # Get order status
            order_status = self.api.get_order(order.id)
            
            result = {
                'order_id': order.id,
                'symbol': order.symbol,
                'qty': order.qty,
                'side': order.side,
                'status': order_status.status,
                'filled_qty': order_status.filled_qty,
                'filled_avg_price': order_status.filled_avg_price,
                'submitted_at': str(order_status.submitted_at)
            }
            
            self.logger.info(f"Order placed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None
    
    def calculate_order_quantity(self, symbol: str) -> int:
        """Calculate order quantity based on position size and current price"""
        try:
            # Get current price
            bars = self.api.get_latest_bar(symbol)
            current_price = float(bars.c)
            
            # Calculate quantity
            qty = int(self.config.position_size / current_price)
            
            # Ensure minimum quantity
            qty = max(qty, 1)
            
            self.logger.info(f"Current price: ${current_price:.2f}, Order quantity: {qty}")
            
            return qty
            
        except Exception as e:
            self.logger.error(f"Error calculating order quantity for {symbol}: {e}")
            return 1  # Fallback to 1 share
    
    def execute_trade(self, signal) -> Optional[Dict]:
        """Execute trade based on signal"""
        try:
            # Check current positions for both symbols
            boil_position = self.get_current_position(self.config.symbol)  # BOIL
            kold_position = self.get_current_position(self.config.inverse_symbol)  # KOLD
            
            account_info = self.get_account_info()
            
            self.logger.info(f"BOIL position: {boil_position}")
            self.logger.info(f"KOLD position: {kold_position}")
            self.logger.info(f"Account info: {account_info}")
            
            if signal.action == 'BUY':
                # Close any existing positions first
                if boil_position and boil_position['qty'] > 0:
                    self.logger.info("Closing existing BOIL position")
                    qty = int(abs(boil_position['qty']))
                    self.place_market_order('sell', qty, self.config.symbol)
                
                if kold_position and kold_position['qty'] > 0:
                    self.logger.info("Closing existing KOLD position")
                    qty = int(abs(kold_position['qty']))
                    self.place_market_order('sell', qty, self.config.inverse_symbol)
                
                # Place new order for the signal symbol
                qty = self.calculate_order_quantity(signal.symbol)
                return self.place_market_order('buy', qty, signal.symbol)
                
            else:  # HOLD
                self.logger.info("Signal indicates HOLD, no action taken")
                return None
                
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            return None
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        try:
            positions = self.api.list_positions()
            account = self.api.get_account()
            
            portfolio = {
                'total_value': float(account.portfolio_value),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'positions': []
            }
            
            for position in positions:
                portfolio['positions'].append({
                    'symbol': position.symbol,
                    'qty': float(position.qty),
                    'market_value': float(position.market_value),
                    'unrealized_pl': float(position.unrealized_pl),
                    'unrealized_plpc': float(position.unrealized_plpc)
                })
            
            return portfolio
            
        except Exception as e:
            self.logger.error(f"Error getting portfolio summary: {e}")
            return {}
