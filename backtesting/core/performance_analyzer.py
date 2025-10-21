# Analyzes backtest results and calculates performance metrics like returns, drawdown, and Sharpe ratio.
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os
from dataclasses import asdict

# Analyzes backtest performance and generates reports
class PerformanceAnalyzer:
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Set up plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
    # Perform comprehensive analysis of backtest results
    def analyze_backtest_result(self, result) -> Dict[str, any]:
        try:
            self.logger.info("Analyzing backtest results")
            
            analysis = {}
            
            # Basic performance metrics
            analysis['basic_metrics'] = self._calculate_basic_metrics(result)
            
            # Risk metrics
            analysis['risk_metrics'] = self._calculate_risk_metrics(result)
            
            # Trade analysis
            analysis['trade_analysis'] = self._analyze_trades(result.trades)
            
            # Monthly performance
            analysis['monthly_performance'] = self._calculate_monthly_performance(result)
            
            # Signal analysis
            analysis['signal_analysis'] = self._analyze_signals(result.trades)
            
            # Benchmark comparison (if available)
            analysis['benchmark_comparison'] = self._compare_to_benchmark(result)
            
            self.logger.info("Backtest analysis completed")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing backtest results: {e}")
            return {}
    
    # Calculate basic performance metrics
    def _calculate_basic_metrics(self, result) -> Dict[str, float]:
        try:
            # Calculate time period
            days = (result.end_date - result.start_date).days
            years = days / 365.25
            
            # Annualized return
            annualized_return = ((result.final_capital / result.initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
            
            # Total return
            total_return_pct = result.total_return_pct
            
            # Number of trades
            total_trades = len(result.trades)
            
            # Win rate
            win_rate = result.win_rate * 100
            
            # Average win/loss
            avg_win = result.avg_win
            avg_loss = result.avg_loss
            
            # Profit factor
            profit_factor = result.profit_factor
            
            # Sharpe ratio
            sharpe_ratio = result.sharpe_ratio
            
            # Max drawdown
            max_drawdown = result.max_drawdown * 100
            
            metrics = {
                'total_return_pct': total_return_pct,
                'annualized_return_pct': annualized_return,
                'total_trades': total_trades,
                'win_rate_pct': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown_pct': max_drawdown,
                'initial_capital': result.initial_capital,
                'final_capital': result.final_capital,
                'total_return': result.total_return,
                'days_traded': days,
                'years_traded': years
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating basic metrics: {e}")
            return {}
    
    # Calculate risk-related metrics
    def _calculate_risk_metrics(self, result) -> Dict[str, float]:
        try:
            if not result.daily_returns:
                return {}
            
            returns = np.array(result.daily_returns)
            
            # Volatility (annualized)
            volatility = np.std(returns) * np.sqrt(252) * 100
            
            # Downside deviation
            downside_returns = returns[returns < 0]
            downside_deviation = np.std(downside_returns) * np.sqrt(252) * 100 if len(downside_returns) > 0 else 0
            
            # Sortino ratio
            mean_return = np.mean(returns) * 252 * 100  # Annualized
            sortino_ratio = mean_return / downside_deviation if downside_deviation > 0 else 0
            
            # Calmar ratio
            annualized_return = ((result.final_capital / result.initial_capital) ** (1/((result.end_date - result.start_date).days/365.25)) - 1) * 100
            calmar_ratio = annualized_return / (result.max_drawdown * 100) if result.max_drawdown > 0 else 0
            
            # Value at Risk (VaR) - 95% confidence
            var_95 = np.percentile(returns, 5) * 100
            
            # Conditional Value at Risk (CVaR)
            cvar_95 = np.mean(returns[returns <= np.percentile(returns, 5)]) * 100
            
            # Maximum consecutive losses
            max_consecutive_losses = self._calculate_max_consecutive_losses(result.trades)
            
            risk_metrics = {
                'volatility_pct': volatility,
                'downside_deviation_pct': downside_deviation,
                'sortino_ratio': sortino_ratio,
                'calmar_ratio': calmar_ratio,
                'var_95_pct': var_95,
                'cvar_95_pct': cvar_95,
                'max_consecutive_losses': max_consecutive_losses
            }
            
            return risk_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            return {}
    
    # Analyze individual trades
    def _analyze_trades(self, trades: List) -> Dict[str, any]:
        try:
            if not trades:
                return {}
            
            # Separate buy and sell trades
            buy_trades = [t for t in trades if t.action == 'BUY']
            sell_trades = [t for t in trades if t.action == 'SELL']
            
            # Calculate trade statistics
            total_buy_value = sum(t.value for t in buy_trades)
            total_sell_value = sum(t.value for t in sell_trades)
            
            # Analyze by symbol
            boil_trades = [t for t in trades if t.symbol == 'BOIL']
            kold_trades = [t for t in trades if t.symbol == 'KOLD']
            
            # Analyze by reason
            signal_trades = [t for t in trades if t.reason == 'SIGNAL']
            stop_loss_trades = [t for t in trades if t.reason == 'STOP_LOSS']
            take_profit_trades = [t for t in trades if t.reason == 'TAKE_PROFIT']
            mutual_exclusivity_trades = [t for t in trades if t.reason == 'MUTUAL_EXCLUSIVITY']
            
            # Calculate average trade size
            avg_trade_size = np.mean([t.value for t in buy_trades]) if buy_trades else 0
            
            # Calculate average holding period (simplified)
            avg_holding_period = self._calculate_avg_holding_period(trades)
            
            trade_analysis = {
                'total_trades': len(trades),
                'buy_trades': len(buy_trades),
                'sell_trades': len(sell_trades),
                'total_buy_value': total_buy_value,
                'total_sell_value': total_sell_value,
                'boil_trades': len(boil_trades),
                'kold_trades': len(kold_trades),
                'signal_trades': len(signal_trades),
                'stop_loss_trades': len(stop_loss_trades),
                'take_profit_trades': len(take_profit_trades),
                'mutual_exclusivity_trades': len(mutual_exclusivity_trades),
                'avg_trade_size': avg_trade_size,
                'avg_holding_period_days': avg_holding_period
            }
            
            return trade_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing trades: {e}")
            return {}
    
    # Calculate monthly performance breakdown
    def _calculate_monthly_performance(self, result) -> Dict[str, List]:
        try:
            if not result.daily_portfolio_values:
                return {}
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(result.daily_portfolio_values, columns=['date', 'value'])
            df['date'] = pd.to_datetime(df['date'])
            df['month'] = df['date'].dt.to_period('M')
            
            # Calculate monthly returns
            monthly_returns = df.groupby('month')['value'].apply(
                lambda x: (x.iloc[-1] - x.iloc[0]) / x.iloc[0] * 100
            ).to_dict()
            
            # Convert to lists for JSON serialization
            months = [str(m) for m in monthly_returns.keys()]
            returns = list(monthly_returns.values())
            
            return {
                'months': months,
                'returns': returns
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating monthly performance: {e}")
            return {}
    
    # Analyze signal effectiveness
    def _analyze_signals(self, trades: List) -> Dict[str, any]:
        try:
            signal_trades = [t for t in trades if t.reason == 'SIGNAL']
            
            if not signal_trades:
                return {}
            
            # Analyze signal strength vs performance
            signal_strengths = [t.signal_strength for t in signal_trades]
            confidences = [t.confidence for t in signal_trades]
            
            # Calculate average signal strength
            avg_signal_strength = np.mean(signal_strengths) if signal_strengths else 0
            avg_confidence = np.mean(confidences) if confidences else 0
            
            # Analyze by symbol
            boil_signals = [t for t in signal_trades if t.symbol == 'BOIL']
            kold_signals = [t for t in signal_trades if t.symbol == 'KOLD']
            
            signal_analysis = {
                'total_signal_trades': len(signal_trades),
                'avg_signal_strength': avg_signal_strength,
                'avg_confidence': avg_confidence,
                'boil_signal_trades': len(boil_signals),
                'kold_signal_trades': len(kold_signals),
                'signal_strengths': signal_strengths,
                'confidences': confidences
            }
            
            return signal_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing signals: {e}")
            return {}
    
    # Compare performance to benchmark (simplified)
    def _compare_to_benchmark(self, result) -> Dict[str, any]:
        try:
            # For now, use a simple benchmark (buy and hold SPY)
            # In a real implementation, you'd load actual benchmark data
            
            days = (result.end_date - result.start_date).days
            years = days / 365.25
            
            # Assume SPY returns 10% annually (simplified)
            benchmark_annual_return = 10.0
            benchmark_total_return = ((1 + benchmark_annual_return/100) ** years - 1) * 100
            
            # Calculate strategy return
            strategy_total_return = result.total_return_pct
            
            # Calculate outperformance
            outperformance = strategy_total_return - benchmark_total_return
            
            benchmark_comparison = {
                'benchmark_total_return_pct': benchmark_total_return,
                'strategy_total_return_pct': strategy_total_return,
                'outperformance_pct': outperformance,
                'benchmark_name': 'SPY (simplified)'
            }
            
            return benchmark_comparison
            
        except Exception as e:
            self.logger.error(f"Error comparing to benchmark: {e}")
            return {}
    
    # Calculate maximum consecutive losing trades
    def _calculate_max_consecutive_losses(self, trades: List) -> int:
        try:
            if not trades:
                return 0
            
            # Group trades by position (buy-sell pairs)
            positions = {}
            trade_pnls = []
            
            for trade in trades:
                if trade.action == 'BUY':
                    positions[trade.symbol] = trade
                elif trade.action == 'SELL' and trade.symbol in positions:
                    buy_trade = positions[trade.symbol]
                    pnl = trade.value - buy_trade.value
                    trade_pnls.append(pnl)
                    del positions[trade.symbol]
            
            # Calculate consecutive losses
            max_consecutive = 0
            current_consecutive = 0
            
            for pnl in trade_pnls:
                if pnl < 0:
                    current_consecutive += 1
                    max_consecutive = max(max_consecutive, current_consecutive)
                else:
                    current_consecutive = 0
            
            return max_consecutive
            
        except Exception as e:
            self.logger.error(f"Error calculating max consecutive losses: {e}")
            return 0
    
    # Calculate average holding period for positions
    def _calculate_avg_holding_period(self, trades: List) -> float:
        try:
            if not trades:
                return 0.0
            
            # Group trades by position
            positions = {}
            holding_periods = []
            
            for trade in trades:
                if trade.action == 'BUY':
                    positions[trade.symbol] = trade.timestamp
                elif trade.action == 'SELL' and trade.symbol in positions:
                    buy_time = positions[trade.symbol]
                    holding_period = (trade.timestamp - buy_time).days
                    holding_periods.append(holding_period)
                    del positions[trade.symbol]
            
            return np.mean(holding_periods) if holding_periods else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating avg holding period: {e}")
            return 0.0
    
    # Generate comprehensive backtest report
    def generate_report(self, result, analysis: Dict[str, any], output_dir: str = "backtesting/reports") -> str:
        try:
            self.logger.info("Generating backtest report")
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate timestamp for report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"backtest_report_{timestamp}.html"
            report_path = os.path.join(output_dir, report_filename)
            
            # Generate HTML report
            html_content = self._generate_html_report(result, analysis)
            
            # Write report
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Generate charts
            self._generate_charts(result, analysis, output_dir, timestamp)
            
            # Generate JSON data
            self._generate_json_data(result, analysis, output_dir, timestamp)
            
            self.logger.info(f"Report generated: {report_path}")
            return report_path
            
        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return ""
    
    # Generate HTML report content
    def _generate_html_report(self, result, analysis: Dict[str, any]) -> str:
        try:
            basic_metrics = analysis.get('basic_metrics', {})
            risk_metrics = analysis.get('risk_metrics', {})
            trade_analysis = analysis.get('trade_analysis', {})
            
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Backtest Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #e8f4f8; border-radius: 5px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ font-size: 12px; color: #7f8c8d; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Backtest Report</h1>
        <p>Period: {result.start_date.date()} to {result.end_date.date()}</p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="section">
        <h2>Performance Summary</h2>
        <div class="metric">
            <div class="metric-value {'positive' if basic_metrics.get('total_return_pct', 0) > 0 else 'negative'}">
                {basic_metrics.get('total_return_pct', 0):.2f}%
            </div>
            <div class="metric-label">Total Return</div>
        </div>
        <div class="metric">
            <div class="metric-value {'positive' if basic_metrics.get('annualized_return_pct', 0) > 0 else 'negative'}">
                {basic_metrics.get('annualized_return_pct', 0):.2f}%
            </div>
            <div class="metric-label">Annualized Return</div>
        </div>
        <div class="metric">
            <div class="metric-value">
                {basic_metrics.get('sharpe_ratio', 0):.2f}
            </div>
            <div class="metric-label">Sharpe Ratio</div>
        </div>
        <div class="metric">
            <div class="metric-value negative">
                {basic_metrics.get('max_drawdown_pct', 0):.2f}%
            </div>
            <div class="metric-label">Max Drawdown</div>
        </div>
    </div>
    
    <div class="section">
        <h2>Trade Statistics</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Trades</td><td>{trade_analysis.get('total_trades', 0)}</td></tr>
            <tr><td>Win Rate</td><td>{basic_metrics.get('win_rate_pct', 0):.2f}%</td></tr>
            <tr><td>Average Win</td><td>${basic_metrics.get('avg_win', 0):.2f}</td></tr>
            <tr><td>Average Loss</td><td>${basic_metrics.get('avg_loss', 0):.2f}</td></tr>
            <tr><td>Profit Factor</td><td>{basic_metrics.get('profit_factor', 0):.2f}</td></tr>
            <tr><td>Average Trade Size</td><td>${trade_analysis.get('avg_trade_size', 0):.2f}</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>Risk Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Volatility</td><td>{risk_metrics.get('volatility_pct', 0):.2f}%</td></tr>
            <tr><td>Sortino Ratio</td><td>{risk_metrics.get('sortino_ratio', 0):.2f}</td></tr>
            <tr><td>Calmar Ratio</td><td>{risk_metrics.get('calmar_ratio', 0):.2f}</td></tr>
            <tr><td>VaR (95%)</td><td>{risk_metrics.get('var_95_pct', 0):.2f}%</td></tr>
            <tr><td>CVaR (95%)</td><td>{risk_metrics.get('cvar_95_pct', 0):.2f}%</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>Capital</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Initial Capital</td><td>${basic_metrics.get('initial_capital', 0):,.2f}</td></tr>
            <tr><td>Final Capital</td><td>${basic_metrics.get('final_capital', 0):,.2f}</td></tr>
            <tr><td>Total Return</td><td>${basic_metrics.get('total_return', 0):,.2f}</td></tr>
        </table>
    </div>
</body>
</html>
            """
            
            return html
            
        except Exception as e:
            self.logger.error(f"Error generating HTML report: {e}")
            return ""
    
    # Generate performance charts
    def _generate_charts(self, result, analysis: Dict[str, any], output_dir: str, timestamp: str):
        try:
            # Portfolio value chart
            if result.daily_portfolio_values:
                plt.figure(figsize=(12, 6))
                dates = [pv[0] for pv in result.daily_portfolio_values]
                values = [pv[1] for pv in result.daily_portfolio_values]
                
                plt.plot(dates, values, linewidth=2)
                plt.title('Portfolio Value Over Time')
                plt.xlabel('Date')
                plt.ylabel('Portfolio Value ($)')
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                chart_path = os.path.join(output_dir, f"portfolio_value_{timestamp}.png")
                plt.savefig(chart_path, dpi=300, bbox_inches='tight')
                plt.close()
            
            # Monthly returns chart
            monthly_perf = analysis.get('monthly_performance', {})
            if monthly_perf.get('returns'):
                plt.figure(figsize=(12, 6))
                months = monthly_perf['months']
                returns = monthly_perf['returns']
                
                colors = ['green' if r > 0 else 'red' for r in returns]
                plt.bar(months, returns, color=colors, alpha=0.7)
                plt.title('Monthly Returns')
                plt.xlabel('Month')
                plt.ylabel('Return (%)')
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                chart_path = os.path.join(output_dir, f"monthly_returns_{timestamp}.png")
                plt.savefig(chart_path, dpi=300, bbox_inches='tight')
                plt.close()
            
        except Exception as e:
            self.logger.error(f"Error generating charts: {e}")
    
    # Generate JSON data files
    def _generate_json_data(self, result, analysis: Dict[str, any], output_dir: str, timestamp: str):
        try:
            # Convert result to dictionary
            result_dict = asdict(result)
            
            # Save result data
            result_path = os.path.join(output_dir, f"backtest_result_{timestamp}.json")
            with open(result_path, 'w') as f:
                json.dump(result_dict, f, indent=2, default=str)
            
            # Save analysis data
            analysis_path = os.path.join(output_dir, f"backtest_analysis_{timestamp}.json")
            with open(analysis_path, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            
        except Exception as e:
            self.logger.error(f"Error generating JSON data: {e}")
    
    # Print a summary of the backtest results
    def print_summary(self, result, analysis: Dict[str, any]):
        try:
            basic_metrics = analysis.get('basic_metrics', {})
            risk_metrics = analysis.get('risk_metrics', {})
            trade_analysis = analysis.get('trade_analysis', {})
            
            print("\n" + "="*60)
            print("BACKTEST SUMMARY")
            print("="*60)
            print(f"Period: {result.start_date.date()} to {result.end_date.date()}")
            print(f"Initial Capital: ${basic_metrics.get('initial_capital', 0):,.2f}")
            print(f"Final Capital: ${basic_metrics.get('final_capital', 0):,.2f}")
            print(f"Total Return: {basic_metrics.get('total_return_pct', 0):.2f}%")
            print(f"Annualized Return: {basic_metrics.get('annualized_return_pct', 0):.2f}%")
            print(f"Sharpe Ratio: {basic_metrics.get('sharpe_ratio', 0):.2f}")
            print(f"Max Drawdown: {basic_metrics.get('max_drawdown_pct', 0):.2f}%")
            print(f"Total Trades: {trade_analysis.get('total_trades', 0)}")
            print(f"Win Rate: {basic_metrics.get('win_rate_pct', 0):.2f}%")
            print(f"Profit Factor: {basic_metrics.get('profit_factor', 0):.2f}")
            print("="*60)
            
        except Exception as e:
            self.logger.error(f"Error printing summary: {e}")
