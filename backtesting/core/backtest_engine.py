# Simulates trading execution and portfolio management for backtesting strategies.

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

# Represents a single trade
@dataclass
class Trade:
    timestamp: datetime
    symbol: str
    action: str  # 'BUY', 'SELL'
    quantity: int
    price: float
    value: float
    signal_strength: float
    confidence: float
    reason: str  # 'SIGNAL', 'STOP_LOSS', 'TAKE_PROFIT', 'MUTUAL_EXCLUSIVITY'

# Represents a current position
@dataclass
class Position:
    symbol: str
    quantity: int
    avg_price: float
    current_value: float
    unrealized_pnl: float
    entry_date: datetime

# Represents the result of a backtest
@dataclass
class BacktestResult:
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    trades: List[Trade]
    positions: List[Position]
    daily_returns: List[float]
    daily_portfolio_values: List[Tuple[datetime, float]]
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float

# Simulates trading based on historical signals and price data
class BacktestEngine:
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Trading parameters
        self.initial_capital = getattr(config, 'initial_capital', 100000)
        self.base_position_size = getattr(config, 'base_position_size', 1000)
        self.max_position_size = getattr(config, 'max_position_size', 5000)
        self.min_position_size = getattr(config, 'min_position_size', 100)
        
        # Stop loss parameters
        self.default_stop_loss_pct = getattr(config, 'default_stop_loss_pct', 0.05)
        self.trailing_stop_pct = getattr(config, 'trailing_stop_pct', 0.03)
        self.take_profit_pct = getattr(config, 'take_profit_pct', 0.15)
        
        # Commission and slippage
        self.commission_per_trade = getattr(config, 'commission_per_trade', 1.0)
        self.slippage_pct = getattr(config, 'slippage_pct', 0.001)  # 0.1%
        
        # Symbols
        self.symbol = getattr(config, 'symbol', 'UNG')
        self.inverse_symbol = getattr(config, 'inverse_symbol', 'KOLD')
        
        # State tracking
        self.current_capital = self.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_portfolio_values: List[Tuple[datetime, float]] = []
        self.active_stops: Dict[str, Dict] = {}
        
    # Run the complete backtest
    def run_backtest(self, signals: List, price_data: Dict[str, pd.DataFrame],
                    start_date: datetime, end_date: datetime) -> BacktestResult:
        try:
            self.logger.info(f"Starting backtest from {start_date.date()} to {end_date.date()}")
            self.logger.info(f"Initial capital: ${self.initial_capital:,.2f}")
            
            # Reset state
            self._reset_state()
            
            # Process signals day by day
            current_date = start_date
            while current_date <= end_date:
                self._process_day(current_date, signals, price_data)
                current_date += timedelta(days=1)
            
            # Close any remaining positions
            self._close_all_positions(price_data, end_date)
            
            # Calculate results
            result = self._calculate_results(start_date, end_date)
            
            self.logger.info(f"Backtest completed. Final capital: ${result.final_capital:,.2f}")
            self.logger.info(f"Total return: {result.total_return_pct:.2f}%")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error running backtest: {e}")
            raise e
    
    # Reset the backtest state
    def _reset_state(self):
        self.current_capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.daily_portfolio_values = []
        self.active_stops = {}
    
    # Process trading for a single day
    def _process_day(self, current_date: datetime, signals: List, price_data: Dict[str, pd.DataFrame]):
        try:
            # Get signal for this date
            signal = self._get_signal_for_date(signals, current_date)
            
            # Get current prices
            ung_price = self._get_price_for_date(price_data['ung_price'], current_date)
            kold_price = self._get_price_for_date(price_data['kold_price'], current_date)
            
            if ung_price is None or kold_price is None:
                self.logger.warning(f"No price data for {current_date.date()}")
                return
            
            # Update portfolio value
            portfolio_value = self._calculate_portfolio_value(ung_price, kold_price)
            self.daily_portfolio_values.append((current_date, portfolio_value))
            
            # Check stop losses first
            self._check_stop_losses(current_date, ung_price, kold_price)
            
            # Process signal if available
            if signal and signal.action == 'BUY':
                self._process_buy_signal(signal, current_date, ung_price, kold_price)
            elif signal and signal.action == 'HOLD':
                self.logger.debug(f"HOLD signal for {current_date.date()}")
            
        except Exception as e:
            self.logger.error(f"Error processing day {current_date.date()}: {e}")
    
    # Get the signal for a specific date
    def _get_signal_for_date(self, signals: List, current_date: datetime):
        for signal in signals:
            if signal.timestamp.date() == current_date.date():
                return signal
        return None
    
    # Get price for a specific date
    def _get_price_for_date(self, price_df: pd.DataFrame, current_date: datetime) -> Optional[float]:
        try:
            # Try exact date match first
            exact_match = price_df[price_df['timestamp'].dt.date == current_date.date()]
            if not exact_match.empty:
                return exact_match['price'].iloc[0]
            
            # Try to get the most recent price before this date
            available_prices = price_df[price_df['timestamp'] <= current_date]
            if not available_prices.empty:
                return available_prices['price'].iloc[-1]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting price for {current_date.date()}: {e}")
            return None
    
    # Calculate current portfolio value
    def _calculate_portfolio_value(self, ung_price: float, kold_price: float) -> float:
        try:
            total_value = self.current_capital
            
            # Add position values
            for symbol, position in self.positions.items():
                if symbol == self.symbol:
                    current_price = ung_price
                elif symbol == self.inverse_symbol:
                    current_price = kold_price
                else:
                    continue
                
                position_value = position.quantity * current_price
                total_value += position_value
            
            return total_value
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio value: {e}")
            return self.current_capital
    
    # Process a BUY signal
    def _process_buy_signal(self, signal, current_date: datetime, ung_price: float, kold_price: float):
        try:
            if signal.symbol == self.symbol:  # Buy UNG
                self._execute_boil_buy(signal, current_date, ung_price, kold_price)
            elif signal.symbol == self.inverse_symbol:  # Buy KOLD
                self._execute_kold_buy(signal, current_date, ung_price, kold_price)
            
        except Exception as e:
            self.logger.error(f"Error processing buy signal: {e}")
    
    # Execute UNG buy with unified strategy logic
    def _execute_boil_buy(self, signal, current_date: datetime, ung_price: float, kold_price: float):
        try:
            # 1. Mutual exclusivity: Sell all KOLD positions first
            if self.inverse_symbol in self.positions:
                self._close_position(self.inverse_symbol, current_date, kold_price, "MUTUAL_EXCLUSIVITY")
            
            # Close any existing UNG position
            if self.symbol in self.positions:
                self._close_position(self.symbol, current_date, ung_price, "SIGNAL")
            
            # 2. Calculate position size
            position_size = self._calculate_position_size(signal)
            quantity = int(position_size / ung_price)
            
            if quantity <= 0:
                self.logger.warning("Calculated quantity is 0 or negative")
                return
            
            # Check minimum trade value to avoid commission impact
            trade_value = quantity * ung_price
            if trade_value < 100:  # Minimum $100 trade to avoid commission impact
                self.logger.warning(f"Trade value too small: ${trade_value:.2f} < $100")
                return
            
            # 3. Execute buy order
            if trade_value > self.current_capital:
                self.logger.warning(f"Insufficient capital for trade: ${trade_value:.2f} > ${self.current_capital:.2f}")
                return
            
            # Apply slippage
            actual_price = ung_price * (1 + self.slippage_pct)
            actual_value = quantity * actual_price
            
            # Create trade
            trade = Trade(
                timestamp=current_date,
                symbol=self.symbol,
                action='BUY',
                quantity=quantity,
                price=actual_price,
                value=actual_value,
                signal_strength=signal.total_signal,
                confidence=signal.confidence,
                reason='SIGNAL'
            )
            
            self.trades.append(trade)
            
            # Update capital
            self.current_capital -= actual_value
            self.current_capital -= self.commission_per_trade
            
            # Create position
            self.positions[self.symbol] = Position(
                symbol=self.symbol,
                quantity=quantity,
                avg_price=actual_price,
                current_value=actual_value,
                unrealized_pnl=0.0,
                entry_date=current_date
            )
            
            # 4. Set up stop loss
            self._setup_stop_loss(self.symbol, actual_price, current_date)
            
            self.logger.info(f"Bought {quantity} shares of {self.symbol} at ${actual_price:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error executing UNG buy: {e}")
    
    # Execute KOLD buy with unified strategy logic
    def _execute_kold_buy(self, signal, current_date: datetime, ung_price: float, kold_price: float):
        try:
            # 1. Mutual exclusivity: Sell all UNG positions first
            if self.symbol in self.positions:
                self._close_position(self.symbol, current_date, ung_price, "MUTUAL_EXCLUSIVITY")
            
            # Close any existing KOLD position
            if self.inverse_symbol in self.positions:
                self._close_position(self.inverse_symbol, current_date, kold_price, "SIGNAL")
            
            # 2. Calculate position size
            position_size = self._calculate_position_size(signal)
            quantity = int(position_size / kold_price)
            
            if quantity <= 0:
                self.logger.warning("Calculated quantity is 0 or negative")
                return
            
            # Check minimum trade value to avoid commission impact
            trade_value = quantity * kold_price
            if trade_value < 100:  # Minimum $100 trade to avoid commission impact
                self.logger.warning(f"Trade value too small: ${trade_value:.2f} < $100")
                return
            
            # 3. Execute buy order
            if trade_value > self.current_capital:
                self.logger.warning(f"Insufficient capital for trade: ${trade_value:.2f} > ${self.current_capital:.2f}")
                return
            
            # Apply slippage
            actual_price = kold_price * (1 + self.slippage_pct)
            actual_value = quantity * actual_price
            
            # Create trade
            trade = Trade(
                timestamp=current_date,
                symbol=self.inverse_symbol,
                action='BUY',
                quantity=quantity,
                price=actual_price,
                value=actual_value,
                signal_strength=signal.total_signal,
                confidence=signal.confidence,
                reason='SIGNAL'
            )
            
            self.trades.append(trade)
            
            # Update capital
            self.current_capital -= actual_value
            self.current_capital -= self.commission_per_trade
            
            # Create position
            self.positions[self.inverse_symbol] = Position(
                symbol=self.inverse_symbol,
                quantity=quantity,
                avg_price=actual_price,
                current_value=actual_value,
                unrealized_pnl=0.0,
                entry_date=current_date
            )
            
            # 4. Set up stop loss
            self._setup_stop_loss(self.inverse_symbol, actual_price, current_date)
            
            self.logger.info(f"Bought {quantity} shares of {self.inverse_symbol} at ${actual_price:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error executing KOLD buy: {e}")
    
    # Calculate dynamic position size based on signal strength
    def _calculate_position_size(self, signal) -> float:
        try:
            # Base position size
            base_size = self.base_position_size
            
            # Adjust for signal strength
            signal_strength = abs(signal.total_signal)
            signal_multiplier = min(signal_strength / 0.5, 2.0)  # Cap at 2x
            
            # Adjust for available capital
            capital_factor = min(self.current_capital / self.initial_capital, 1.0)
            
            # Calculate final position size
            position_size = base_size * signal_multiplier * capital_factor
            
            # Apply limits
            position_size = max(self.min_position_size, min(position_size, self.max_position_size))
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return self.base_position_size
    
    # Set up stop loss for a position
    def _setup_stop_loss(self, symbol: str, entry_price: float, entry_date: datetime):
        try:
            # Calculate stop loss price
            stop_loss_price = entry_price * (1 - self.default_stop_loss_pct)
            take_profit_price = entry_price * (1 + self.take_profit_pct)
            
            # Store stop loss information
            self.active_stops[symbol] = {
                'entry_price': entry_price,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'entry_date': entry_date,
                'trailing_stop': False
            }
            
            self.logger.debug(f"Set up stop loss for {symbol}: Entry=${entry_price:.2f}, Stop=${stop_loss_price:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error setting up stop loss: {e}")
    
    # Check all active stop losses
    def _check_stop_losses(self, current_date: datetime, ung_price: float, kold_price: float):
        try:
            for symbol, stop_info in list(self.active_stops.items()):
                if symbol not in self.positions:
                    # Position no longer exists, remove stop loss
                    del self.active_stops[symbol]
                    continue
                
                # Get current price
                if symbol == self.symbol:
                    current_price = ung_price
                elif symbol == self.inverse_symbol:
                    current_price = kold_price
                else:
                    continue
                
                if current_price is None:
                    continue
                
                # Check stop loss trigger
                if current_price <= stop_info['stop_loss_price']:
                    self.logger.info(f"Stop loss triggered for {symbol} at ${current_price:.2f}")
                    self._close_position(symbol, current_date, current_price, "STOP_LOSS")
                    continue
                
                # Check take profit trigger
                if current_price >= stop_info['take_profit_price']:
                    self.logger.info(f"Take profit triggered for {symbol} at ${current_price:.2f}")
                    self._close_position(symbol, current_date, current_price, "TAKE_PROFIT")
                    continue
                
                # Check for trailing stop activation
                if not stop_info['trailing_stop']:
                    profit_pct = (current_price - stop_info['entry_price']) / stop_info['entry_price']
                    if profit_pct >= 0.10:  # Increased from 5% to 10% profit threshold for trailing stop
                        self._activate_trailing_stop(symbol, current_price)
                
                # Update trailing stop if active
                if stop_info['trailing_stop']:
                    self._update_trailing_stop(symbol, current_price, current_date)
                    
        except Exception as e:
            self.logger.error(f"Error checking stop losses: {e}")
    
    # Activate trailing stop for a profitable position
    def _activate_trailing_stop(self, symbol: str, current_price: float):
        try:
            if symbol in self.active_stops:
                self.active_stops[symbol]['trailing_stop'] = True
                self.active_stops[symbol]['trailing_stop_price'] = current_price * (1 - self.trailing_stop_pct)
                self.logger.debug(f"Trailing stop activated for {symbol}")
                
        except Exception as e:
            self.logger.error(f"Error activating trailing stop: {e}")
    
    # Update trailing stop price as position becomes more profitable
    def _update_trailing_stop(self, symbol: str, current_price: float, current_date: datetime):
        try:
            if symbol in self.active_stops:
                stop_info = self.active_stops[symbol]
                new_trailing_price = current_price * (1 - self.trailing_stop_pct)
                
                # Only update if new trailing price is higher (better for us)
                if new_trailing_price > stop_info.get('trailing_stop_price', 0):
                    stop_info['trailing_stop_price'] = new_trailing_price
                    self.logger.debug(f"Updated trailing stop for {symbol} to ${new_trailing_price:.2f}")
                
                # Check if trailing stop is triggered
                if current_price <= stop_info['trailing_stop_price']:
                    self.logger.info(f"Trailing stop triggered for {symbol} at ${current_price:.2f}")
                    self._close_position(symbol, current_date, current_price, "TRAILING_STOP")
                    
        except Exception as e:
            self.logger.error(f"Error updating trailing stop: {e}")
    
    # Close a position
    def _close_position(self, symbol: str, current_date: datetime, current_price: float, reason: str):
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            
            # Apply slippage
            actual_price = current_price * (1 - self.slippage_pct)
            actual_value = position.quantity * actual_price
            
            # Create trade
            trade = Trade(
                timestamp=current_date,
                symbol=symbol,
                action='SELL',
                quantity=position.quantity,
                price=actual_price,
                value=actual_value,
                signal_strength=0.0,
                confidence=0.0,
                reason=reason
            )
            
            self.trades.append(trade)
            
            # Update capital
            self.current_capital += actual_value
            self.current_capital -= self.commission_per_trade
            
            # Remove position
            del self.positions[symbol]
            
            # Remove stop loss
            if symbol in self.active_stops:
                del self.active_stops[symbol]
            
            self.logger.info(f"Sold {position.quantity} shares of {symbol} at ${actual_price:.2f} ({reason})")
            
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
    
    # Close all remaining positions at the end of backtest
    def _close_all_positions(self, price_data: Dict[str, pd.DataFrame], end_date: datetime):
        try:
            ung_price = self._get_price_for_date(price_data['ung_price'], end_date)
            kold_price = self._get_price_for_date(price_data['kold_price'], end_date)
            
            for symbol in list(self.positions.keys()):
                if symbol == self.symbol and ung_price:
                    self._close_position(symbol, end_date, ung_price, "END_OF_BACKTEST")
                elif symbol == self.inverse_symbol and kold_price:
                    self._close_position(symbol, end_date, kold_price, "END_OF_BACKTEST")
            
        except Exception as e:
            self.logger.error(f"Error closing all positions: {e}")
    
    # Calculate backtest results
    def _calculate_results(self, start_date: datetime, end_date: datetime) -> BacktestResult:
        try:
            # Calculate daily returns
            daily_returns = []
            if len(self.daily_portfolio_values) > 1:
                for i in range(1, len(self.daily_portfolio_values)):
                    prev_value = self.daily_portfolio_values[i-1][1]
                    curr_value = self.daily_portfolio_values[i][1]
                    daily_return = (curr_value - prev_value) / prev_value
                    daily_returns.append(daily_return)
            
            # Calculate metrics
            final_capital = self.current_capital
            total_return = final_capital - self.initial_capital
            total_return_pct = (total_return / self.initial_capital) * 100
            
            # Calculate max drawdown
            max_drawdown = self._calculate_max_drawdown()
            
            # Calculate Sharpe ratio
            sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
            
            # Calculate trade statistics
            win_rate, avg_win, avg_loss, profit_factor = self._calculate_trade_stats()
            
            # Get final positions
            final_positions = list(self.positions.values())
            
            result = BacktestResult(
                start_date=start_date,
                end_date=end_date,
                initial_capital=self.initial_capital,
                final_capital=final_capital,
                total_return=total_return,
                total_return_pct=total_return_pct,
                trades=self.trades,
                positions=final_positions,
                daily_returns=daily_returns,
                daily_portfolio_values=self.daily_portfolio_values,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                profit_factor=profit_factor
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating results: {e}")
            raise e
    
    # Calculate maximum drawdown
    def _calculate_max_drawdown(self) -> float:
        try:
            if not self.daily_portfolio_values:
                return 0.0
            
            values = [pv[1] for pv in self.daily_portfolio_values]
            peak = values[0]
            max_dd = 0.0
            
            for value in values:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak
                max_dd = max(max_dd, dd)
            
            return max_dd
            
        except Exception as e:
            self.logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
    
    # Calculate Sharpe ratio
    def _calculate_sharpe_ratio(self, daily_returns: List[float]) -> float:
        try:
            if not daily_returns:
                return 0.0
            
            mean_return = np.mean(daily_returns)
            std_return = np.std(daily_returns)
            
            if std_return == 0:
                return 0.0
            
            # Assume risk-free rate of 0 for simplicity
            sharpe_ratio = mean_return / std_return * np.sqrt(252)  # Annualized
            
            return sharpe_ratio
            
        except Exception as e:
            self.logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0
    
    # Calculate trade statistics
    def _calculate_trade_stats(self) -> Tuple[float, float, float, float]:
        try:
            if not self.trades:
                return 0.0, 0.0, 0.0, 0.0
            
            # Group trades by position (buy-sell pairs)
            positions = {}
            for trade in self.trades:
                if trade.action == 'BUY':
                    positions[trade.symbol] = trade
                elif trade.action == 'SELL' and trade.symbol in positions:
                    buy_trade = positions[trade.symbol]
                    pnl = trade.value - buy_trade.value
                    
                    # Store PnL for analysis
                    if not hasattr(trade, 'pnl'):
                        trade.pnl = pnl
                    
                    del positions[trade.symbol]
            
            # Calculate statistics
            completed_trades = [t for t in self.trades if hasattr(t, 'pnl')]
            
            if not completed_trades:
                return 0.0, 0.0, 0.0, 0.0
            
            wins = [t.pnl for t in completed_trades if t.pnl > 0]
            losses = [t.pnl for t in completed_trades if t.pnl < 0]
            
            win_rate = len(wins) / len(completed_trades) if completed_trades else 0.0
            avg_win = np.mean(wins) if wins else 0.0
            avg_loss = np.mean(losses) if losses else 0.0
            
            total_wins = sum(wins) if wins else 0.0
            total_losses = abs(sum(losses)) if losses else 0.0
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            
            return win_rate, avg_win, avg_loss, profit_factor
            
        except Exception as e:
            self.logger.error(f"Error calculating trade stats: {e}")
            return 0.0, 0.0, 0.0, 0.0
