# Manages and coordinates multiple trading strategies and their execution.
import logging
from typing import Optional, Dict, List
from datetime import datetime

class StrategyManager:
    """
    Manages multiple trading strategies and allows switching between them.
    
    This manager provides:
    - Strategy selection and switching
    - Strategy performance tracking
    - Fallback strategy handling
    - Strategy configuration management
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Available strategies
        self.strategies = {}
        self.current_strategy = None
        self.strategy_history = []
        
        # Initialize strategies
        self._initialize_strategies()
        
        # Set default strategy
        self.set_strategy('unified')
        
    def _initialize_strategies(self):
        """Initializes all available strategies."""
        try:
            from .mutual_exclusivity_strategy import MutualExclusivityStrategy
            from .position_sizing_strategy import PositionSizingStrategy
            from .signal_confirmation_strategy import SignalConfirmationStrategy
            from .stop_loss_strategy import StopLossStrategy
            from .unified_strategy import UnifiedStrategy
            
            self.strategies = {
                'unified': UnifiedStrategy(self.config),
                'mutual_exclusivity': MutualExclusivityStrategy(self.config),
                'position_sizing': PositionSizingStrategy(self.config),
                'signal_confirmation': SignalConfirmationStrategy(self.config),
                'stop_loss': StopLossStrategy(self.config)
            }
            
            self.logger.info(f"Strategy Manager - Initialized {len(self.strategies)} strategies")
            
        except ImportError as e:
            self.logger.error(f"Strategy Manager - Error importing strategies: {e}")
            # Fallback to basic strategy
            from .mutual_exclusivity_strategy import MutualExclusivityStrategy
            self.strategies = {
                'mutual_exclusivity': MutualExclusivityStrategy(self.config)
            }
            self.current_strategy = 'mutual_exclusivity'
    
    def set_strategy(self, strategy_name: str) -> bool:
        """
        Sets the active trading strategy.
        
        Args:
            strategy_name: Name of the strategy to activate.
        
        Returns:
            bool: True if strategy was set successfully, False otherwise.
        """
        try:
            if strategy_name not in self.strategies:
                self.logger.error(f"Strategy Manager - Unknown strategy: {strategy_name}")
                return False
            
            # Log strategy change
            if self.current_strategy:
                self.logger.info(f"Strategy Manager - Switching from {self.current_strategy} to {strategy_name}")
            else:
                self.logger.info(f"Strategy Manager - Setting initial strategy to {strategy_name}")
            
            self.current_strategy = strategy_name
            
            # Add to history
            self.strategy_history.append({
                'strategy': strategy_name,
                'timestamp': datetime.now(),
                'action': 'activated'
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Strategy Manager - Error setting strategy: {e}")
            return False
    
    def get_current_strategy(self):
        """Gets the current active strategy."""
        if self.current_strategy and self.current_strategy in self.strategies:
            return self.strategies[self.current_strategy]
        return None
    
    def validate_signal(self, signal) -> bool:
        """Validates the incoming signal using the current strategy."""
        try:
            current_strategy = self.get_current_strategy()
            if not current_strategy:
                self.logger.error("Strategy Manager - No active strategy")
                return False
            
            return current_strategy.validate_signal(signal)
            
        except Exception as e:
            self.logger.error(f"Strategy Manager - Error validating signal: {e}")
            return False
    
    def execute_trade(self, signal, trader) -> Optional[Dict]:
        """
        Executes a trade using the current strategy.
        
        Args:
            signal: The trading signal object.
            trader: An instance of AlpacaTrader to execute orders.
        
        Returns:
            Optional[Dict]: The executed order details or None if no trade was made.
        """
        try:
            current_strategy = self.get_current_strategy()
            if not current_strategy:
                self.logger.error("Strategy Manager - No active strategy")
                return None
            
            # Execute trade with current strategy
            result = current_strategy.execute_trade(signal, trader)
            
            # Log trade execution
            if result:
                self.strategy_history.append({
                    'strategy': self.current_strategy,
                    'timestamp': datetime.now(),
                    'action': 'trade_executed',
                    'symbol': signal.symbol,
                    'action_type': signal.action,
                    'order_id': result.get('order_id')
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Strategy Manager - Error executing trade: {e}")
            return None
    
    def get_strategy_info(self) -> Dict:
        """Gets information about the current strategy."""
        try:
            current_strategy = self.get_current_strategy()
            if not current_strategy:
                return {
                    'strategy_name': 'None',
                    'description': 'No active strategy',
                    'available_strategies': list(self.strategies.keys())
                }
            
            return {
                'strategy_name': self.current_strategy,
                'description': current_strategy.get_strategy_description(),
                'available_strategies': list(self.strategies.keys()),
                'strategy_history': self.strategy_history[-10:]  # Last 10 entries
            }
            
        except Exception as e:
            self.logger.error(f"Strategy Manager - Error getting strategy info: {e}")
            return {
                'strategy_name': 'Error',
                'description': f'Error getting strategy info: {e}',
                'available_strategies': []
            }
    
    def get_available_strategies(self) -> List[str]:
        """Gets list of available strategy names."""
        return list(self.strategies.keys())
    
    def get_strategy_performance(self) -> Dict:
        """Gets performance metrics for all strategies."""
        try:
            performance = {}
            
            for strategy_name, strategy in self.strategies.items():
                # Count trades executed by this strategy
                trades = [entry for entry in self.strategy_history 
                         if entry.get('strategy') == strategy_name and entry.get('action') == 'trade_executed']
                
                performance[strategy_name] = {
                    'total_trades': len(trades),
                    'last_trade': trades[-1]['timestamp'] if trades else None,
                    'is_active': strategy_name == self.current_strategy
                }
            
            return performance
            
        except Exception as e:
            self.logger.error(f"Strategy Manager - Error getting strategy performance: {e}")
            return {}
    
    def get_strategy_description(self) -> str:
        """Returns a description of the strategy manager."""
        return (
            "Strategy Manager:\n\n"
            "- Manages multiple trading strategies\n"
            "- Allows dynamic strategy switching\n"
            "- Tracks strategy performance\n"
            "- Provides fallback handling\n\n"
            "Available Strategies:\n"
            "- Mutual Exclusivity: Only one position at a time\n"
            "- Position Sizing: Dynamic position sizing\n"
            "- Signal Confirmation: Multiple signal validation\n"
            "- Stop Loss: Automatic stop losses and take profits"
        )
