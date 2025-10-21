# Provides centralized logging functionality for trading operations and system events.
import logging
import json
from datetime import datetime
from typing import Dict, Any
import os

class TradingLogger:
    """Comprehensive logging system for the trading bot"""
    
    def __init__(self, config):
        self.config = config
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/{self.config.log_file}'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
    def log_signal(self, signal) -> None:
        """Log trading signal"""
        signal_data = {
            'timestamp': signal.timestamp.isoformat(),
            'temperature_signal': signal.temperature_signal,
            'inventory_signal': signal.inventory_signal,
            'storm_signal': signal.storm_signal,
            'total_signal': signal.total_signal,
            'action': signal.action,
            'confidence': signal.confidence
        }
        
        self.logger.info(f"TRADING SIGNAL: {json.dumps(signal_data, indent=2)}")
        
        # Save to separate signal log file
        with open('logs/signals.log', 'a') as f:
            f.write(json.dumps(signal_data) + '\n')
    
    def log_trade(self, trade_result: Dict[str, Any]) -> None:
        """Log trade execution"""
        if trade_result:
            self.logger.info(f"TRADE EXECUTED: {json.dumps(trade_result, indent=2)}")
            
            # Save to separate trade log file
            with open('logs/trades.log', 'a') as f:
                trade_data = {
                    'timestamp': datetime.now().isoformat(),
                    'trade': trade_result
                }
                f.write(json.dumps(trade_data) + '\n')
        else:
            self.logger.info("No trade executed")
    
    def log_portfolio(self, portfolio: Dict[str, Any]) -> None:
        """Log portfolio status"""
        self.logger.info(f"PORTFOLIO STATUS: {json.dumps(portfolio, indent=2)}")
        
        # Save to separate portfolio log file
        with open('logs/portfolio.log', 'a') as f:
            portfolio_data = {
                'timestamp': datetime.now().isoformat(),
                'portfolio': portfolio
            }
            f.write(json.dumps(portfolio_data) + '\n')
    
    def log_error(self, error: Exception, context: str = "") -> None:
        """Log errors with context"""
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context
        }
        
        self.logger.error(f"ERROR: {json.dumps(error_data, indent=2)}")
        
        # Save to separate error log file
        with open('logs/errors.log', 'a') as f:
            f.write(json.dumps(error_data) + '\n')
    
    def log_api_call(self, api_name: str, endpoint: str, status: str, response_time: float = None) -> None:
        """Log API calls"""
        api_data = {
            'timestamp': datetime.now().isoformat(),
            'api': api_name,
            'endpoint': endpoint,
            'status': status,
            'response_time': response_time
        }
        
        self.logger.info(f"API CALL: {json.dumps(api_data)}")
        
        # Save to separate API log file
        with open('logs/api_calls.log', 'a') as f:
            f.write(json.dumps(api_data) + '\n')
