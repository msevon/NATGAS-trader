# Executes trades through the Alpaca API and manages live trading operations.
import logging
import alpaca_trade_api as tradeapi
from datetime import datetime
from typing import Optional, Dict, List
import time
from strategies.strategy_manager import StrategyManager

class AlpacaTrader:
    """Handles trading operations through Alpaca API"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize strategy manager
        self.strategy_manager = StrategyManager(config)
        
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
        """Execute trade using the configured strategy manager"""
        try:
            # Validate signal with strategy manager
            if not self.strategy_manager.validate_signal(signal):
                self.logger.warning("Signal validation failed, skipping trade")
                return None
            
            # Execute trade using strategy manager
            return self.strategy_manager.execute_trade(signal, self)
                
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            return None
    
    def set_strategy(self, strategy_name: str) -> bool:
        """Set the active trading strategy"""
        return self.strategy_manager.set_strategy(strategy_name)
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available trading strategies"""
        return self.strategy_manager.get_available_strategies()
    
    def get_strategy_performance(self) -> Dict:
        """Get performance metrics for all strategies"""
        return self.strategy_manager.get_strategy_performance()
    
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
                # Calculate current price from market value and quantity
                current_price = float(position.market_value) / float(position.qty) if float(position.qty) != 0 else 0
                
                portfolio['positions'].append({
                    'symbol': position.symbol,
                    'qty': float(position.qty),
                    'current_price': current_price,
                    'market_value': float(position.market_value),
                    'unrealized_pl': float(position.unrealized_pl),
                    'unrealized_plpc': float(position.unrealized_plpc)
                })
            
            return portfolio
            
        except Exception as e:
            self.logger.error(f"Error getting portfolio summary: {e}")
            return {}
