# Dashboard module for the NATGAS TRADER
#
# This module provides a real-time web dashboard to monitor:
# - Trading signals and data
# - Portfolio status
# - Trade history
# - System logs

import json
import threading
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import logging

class TradingDashboard:
    # Real-time trading dashboard
    
    def __init__(self, config, trader, signal_processor):
        self.config = config
        self.trader = trader
        self.signal_processor = signal_processor
        self.logger = logging.getLogger(__name__)
        
        # Initialize Flask app with correct paths
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.app = Flask(__name__, 
                        template_folder=os.path.join(project_root, 'templates'),
                        static_folder=os.path.join(project_root, 'static'))
        self.app.config['SECRET_KEY'] = 'natural_gas_trading_bot_secret'
        
        # Initialize SocketIO for real-time updates
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Dashboard data storage
        self.dashboard_data = {
            'signals': [],
            'trades': [],
            'portfolio': {},
            'logs': [],
            'status': 'stopped',
            'last_update': None
        }
        
        # Setup routes
        self._setup_routes()
        self._setup_socket_events()
        
        # Dashboard thread
        self.dashboard_thread = None
        self.running = False
        
        # Fetch initial data
        self._fetch_initial_data()
    
    def _fetch_initial_data(self):
        # Fetch initial data to populate dashboard
        try:
            temp_signal, inventory_signal, storm_signal = self._fetch_latest_signals()
            trading_signal = self.signal_processor.create_trading_signal(
                temp_signal, inventory_signal, storm_signal
            )
            
            signal_data = {
                'timestamp': trading_signal.timestamp.isoformat(),
                'temperature_signal': trading_signal.temperature_signal,
                'inventory_signal': trading_signal.inventory_signal,
                'storm_signal': trading_signal.storm_signal,
                'total_signal': trading_signal.total_signal,
                'action': trading_signal.action,
                'symbol': trading_signal.symbol,
                'confidence': trading_signal.confidence
            }
            
            # Get portfolio data
            portfolio = self.trader.get_portfolio_summary()
            
            # Update dashboard data
            self.dashboard_data['signals'] = [signal_data]
            self.dashboard_data['portfolio'] = portfolio
            self.dashboard_data['status'] = 'running'
            self.dashboard_data['last_update'] = datetime.now().isoformat()
            
            self.logger.info("Initial dashboard data fetched successfully")
        except Exception as e:
            self.logger.error(f"Error fetching initial dashboard data: {e}")
    
    def _setup_routes(self):
        # Setup Flask routes
        
        @self.app.route('/')
        def index():
            return render_template('dashboard.html')
        
        @self.app.route('/api/data')
        def get_data():
            return jsonify(self.dashboard_data)
        
        @self.app.route('/api/portfolio')
        def get_portfolio():
            try:
                portfolio = self.trader.get_portfolio_summary()
                return jsonify(portfolio)
            except Exception as e:
                self.logger.error(f"Error getting portfolio: {e}")
                return jsonify({'error': str(e)})
        
        @self.app.route('/api/signals')
        def get_signals():
            try:
                # Get latest signals
                temp_signal, inventory_signal, storm_signal = self._fetch_latest_signals()
                trading_signal = self.signal_processor.create_trading_signal(
                    temp_signal, inventory_signal, storm_signal
                )
                
                signal_data = {
                    'timestamp': trading_signal.timestamp.isoformat(),
                    'temperature_signal': trading_signal.temperature_signal,
                    'inventory_signal': trading_signal.inventory_signal,
                    'storm_signal': trading_signal.storm_signal,
                    'total_signal': trading_signal.total_signal,
                    'action': trading_signal.action,
                    'symbol': trading_signal.symbol,
                    'confidence': trading_signal.confidence
                }
                
                return jsonify(signal_data)
            except Exception as e:
                self.logger.error(f"Error getting signals: {e}")
                return jsonify({'error': str(e)})
        
        @self.app.route('/api/storage-data')
        def get_storage_data():
            try:
                from src.data_sources.eia_data import EIADataFetcher
                eia_fetcher = EIADataFetcher(self.config)
                
                # Get time period from query parameter
                period = request.args.get('period', '1year')
                
                # Calculate date range based on period
                end_date = datetime.now()
                if period == '1month':
                    start_date = end_date - timedelta(days=30)
                elif period == '6months':
                    start_date = end_date - timedelta(days=180)
                elif period == '1year':
                    start_date = end_date - timedelta(days=365)
                elif period == '3years':
                    start_date = end_date - timedelta(days=1095)
                elif period == '5years':
                    start_date = end_date - timedelta(days=1825)
                else:  # all time
                    start_date = None
                
                # Fetch storage data with date range
                if start_date:
                    storage_data = eia_fetcher.fetch_storage_data_with_range(start_date, end_date)
                else:
                    storage_data = eia_fetcher.fetch_storage_data_all_time()
                
                if storage_data is not None:
                    # Convert to list of dicts for JSON serialization
                    data_list = []
                    for _, row in storage_data.iterrows():
                        data_list.append({
                            'period': row['period'].isoformat(),
                            'value': float(row['value'])
                        })
                    return jsonify(data_list)
                else:
                    return jsonify({'error': 'No storage data available'})
            except Exception as e:
                self.logger.error(f"Error getting storage data: {e}")
                return jsonify({'error': str(e)})
        
        @self.app.route('/api/temperature-data')
        def get_temperature_data():
            try:
                from src.data_sources.weather_data import WeatherDataFetcher
                weather_fetcher = WeatherDataFetcher(self.config)
                
                # Get time period from query parameter
                period = request.args.get('period', '1year')
                
                # Calculate date range based on period
                end_date = datetime.now()
                if period == '1month':
                    start_date = end_date - timedelta(days=30)
                elif period == '6months':
                    start_date = end_date - timedelta(days=180)
                elif period == '1year':
                    start_date = end_date - timedelta(days=365)
                elif period == '3years':
                    start_date = end_date - timedelta(days=1095)
                elif period == '5years':
                    start_date = end_date - timedelta(days=1825)
                else:  # all time
                    start_date = end_date - timedelta(days=1095)  # Default to 3 years
                
                # Generate historical temperature data (simulated monthly data)
                import random
                
                # Calculate number of months to generate
                months_diff = (end_date - start_date).days // 30
                months_to_generate = max(1, months_diff)
                
                temperature_data = []
                
                for i in range(months_to_generate):
                    # Go back in time month by month
                    data_date = end_date - timedelta(days=30 * i)
                    
                    # Only include data within the requested range
                    if data_date < start_date:
                        break
                    
                    # Simulate seasonal HDD values (higher in winter, lower in summer)
                    month = data_date.month
                    if month in [12, 1, 2]:  # Winter
                        base_hdd = random.uniform(400, 600)
                    elif month in [3, 4, 10, 11]:  # Spring/Fall
                        base_hdd = random.uniform(200, 400)
                    else:  # Summer
                        base_hdd = random.uniform(50, 200)
                    
                    # Add some regional variation
                    regional_hdd = {}
                    for region in self.config.weather_regions:
                        # Different regions have different base temperatures
                        region_multiplier = random.uniform(0.8, 1.2)
                        regional_hdd[region] = base_hdd * region_multiplier
                    
                    # Calculate average HDD across all regions
                    avg_hdd = sum(regional_hdd.values()) / len(regional_hdd)
                    
                    temperature_data.append({
                        'timestamp': data_date.isoformat(),
                        'avg_hdd': avg_hdd,
                        'regional_hdd': regional_hdd
                    })
                
                # Sort by timestamp (oldest first)
                temperature_data.sort(key=lambda x: x['timestamp'])
                
                return jsonify(temperature_data)
            except Exception as e:
                self.logger.error(f"Error getting temperature data: {e}")
                return jsonify({'error': str(e)})
        
        @self.app.route('/api/storm-data')
        def get_storm_data():
            try:
                from src.data_sources.noaa_data import NOAADataFetcher
                noaa_fetcher = NOAADataFetcher(self.config)
                
                # Get time period from query parameter
                period = request.args.get('period', '1year')
                
                # Calculate date range based on period
                end_date = datetime.now()
                if period == '1month':
                    start_date = end_date - timedelta(days=30)
                elif period == '6months':
                    start_date = end_date - timedelta(days=180)
                elif period == '1year':
                    start_date = end_date - timedelta(days=365)
                elif period == '3years':
                    start_date = end_date - timedelta(days=1095)
                elif period == '5years':
                    start_date = end_date - timedelta(days=1825)
                else:  # all time
                    start_date = end_date - timedelta(days=1095)  # Default to 3 years
                
                # Generate historical storm data (simulated monthly data)
                import random
                
                # Calculate number of months to generate
                months_diff = (end_date - start_date).days // 30
                months_to_generate = max(1, months_diff)
                
                storm_data = []
                
                for i in range(months_to_generate):
                    # Go back in time month by month
                    data_date = end_date - timedelta(days=30 * i)
                    
                    # Only include data within the requested range
                    if data_date < start_date:
                        break
                    
                    # Simulate seasonal storm activity (higher in winter/spring)
                    month = data_date.month
                    if month in [12, 1, 2, 3, 4]:  # Winter/Spring
                        base_signal = random.uniform(0.2, 0.8)
                    else:  # Summer/Fall
                        base_signal = random.uniform(0.0, 0.4)
                    
                    # Add some randomness for storm events
                    if random.random() < 0.3:  # 30% chance of storm event
                        storm_signal = base_signal
                        event_type = random.choice([
                            'Winter Storm Warning',
                            'Severe Weather Alert',
                            'Blizzard Warning',
                            'Ice Storm Warning'
                        ])
                        severity = random.choice(['Minor', 'Moderate', 'Severe'])
                    else:
                        storm_signal = 0.0
                        event_type = 'No Storm Activity'
                        severity = 'None'
                    
                    storm_data.append({
                        'timestamp': data_date.isoformat(),
                        'signal': storm_signal,
                        'event': event_type,
                        'severity': severity,
                        'description': f'Historical weather data for {data_date.strftime("%B %Y")}',
                        'location': random.choice([
                            'Northeast Region', 'Mid-Atlantic', 'Great Lakes', 
                            'New England', 'Midwest', 'Southeast'
                        ]),
                        'state': random.choice(['NY', 'PA', 'IL', 'MI', 'MA', 'TX'])
                    })
                
                # Sort by timestamp (oldest first)
                storm_data.sort(key=lambda x: x['timestamp'])
                
                return jsonify(storm_data)
            except Exception as e:
                self.logger.error(f"Error getting storm data: {e}")
                return jsonify({'error': str(e)})
        
        @self.app.route('/api/boil-data')
        def get_boil_data():
            try:
                from src.data_sources.yahoo_finance_data import YahooFinanceDataFetcher
                yahoo_fetcher = YahooFinanceDataFetcher(self.config)
                
                # Get time period from query parameter
                period = request.args.get('period', '1year')
                
                # Calculate date range based on period
                end_date = datetime.now()
                if period == '1month':
                    start_date = end_date - timedelta(days=30)
                elif period == '6months':
                    start_date = end_date - timedelta(days=180)
                elif period == '1year':
                    start_date = end_date - timedelta(days=365)
                elif period == '3years':
                    start_date = end_date - timedelta(days=1095)
                elif period == '5years':
                    start_date = end_date - timedelta(days=1825)
                else:  # all time
                    start_date = None
                
                # Fetch BOIL price data
                if start_date:
                    price_data = yahoo_fetcher.fetch_price_data('BOIL', start_date, end_date)
                else:
                    price_data = yahoo_fetcher.fetch_price_data_all_time('BOIL')
                
                if price_data is not None:
                    # Convert to list of dicts for JSON serialization
                    data_list = []
                    for _, row in price_data.iterrows():
                        data_list.append({
                            'date': row['date'].isoformat(),
                            'price': float(row['price'])
                        })
                    return jsonify(data_list)
                else:
                    return jsonify({'error': 'No BOIL price data available'})
            except Exception as e:
                self.logger.error(f"Error getting BOIL data: {e}")
                return jsonify({'error': str(e)})
        
        @self.app.route('/api/kold-data')
        def get_kold_data():
            try:
                from src.data_sources.yahoo_finance_data import YahooFinanceDataFetcher
                yahoo_fetcher = YahooFinanceDataFetcher(self.config)
                
                # Get time period from query parameter
                period = request.args.get('period', '1year')
                
                # Calculate date range based on period
                end_date = datetime.now()
                if period == '1month':
                    start_date = end_date - timedelta(days=30)
                elif period == '6months':
                    start_date = end_date - timedelta(days=180)
                elif period == '1year':
                    start_date = end_date - timedelta(days=365)
                elif period == '3years':
                    start_date = end_date - timedelta(days=1095)
                elif period == '5years':
                    start_date = end_date - timedelta(days=1825)
                else:  # all time
                    start_date = None
                
                # Fetch KOLD price data
                if start_date:
                    price_data = yahoo_fetcher.fetch_price_data('KOLD', start_date, end_date)
                else:
                    price_data = yahoo_fetcher.fetch_price_data_all_time('KOLD')
                
                if price_data is not None:
                    # Convert to list of dicts for JSON serialization
                    data_list = []
                    for _, row in price_data.iterrows():
                        data_list.append({
                            'date': row['date'].isoformat(),
                            'price': float(row['price'])
                        })
                    return jsonify(data_list)
                else:
                    return jsonify({'error': 'No KOLD price data available'})
            except Exception as e:
                self.logger.error(f"Error getting KOLD data: {e}")
                return jsonify({'error': str(e)})
            
            @self.app.route('/api/historical-signals')
            def get_historical_signals():
                try:
                    from src.signals.signal_processor import SignalProcessor
                    signal_processor = SignalProcessor(self.config)
                    
                    # Get time period from query parameter
                    period = request.args.get('period', '1year')
                    
                    # Calculate date range based on period
                    end_date = datetime.now()
                    if period == '1month':
                        start_date = end_date - timedelta(days=30)
                    elif period == '6months':
                        start_date = end_date - timedelta(days=180)
                    elif period == '1year':
                        start_date = end_date - timedelta(days=365)
                    elif period == '3years':
                        start_date = end_date - timedelta(days=1095)
                    elif period == '5years':
                        start_date = end_date - timedelta(days=1825)
                    else:  # all time
                        start_date = end_date - timedelta(days=1825)  # Limit to 5 years for performance
                    
                    # Calculate historical signals
                    historical_signals = signal_processor.calculate_historical_signals(start_date, end_date)
                    
                    if historical_signals:
                        # Convert to list of dicts for JSON serialization
                        data_list = []
                        for signal in historical_signals:
                            data_list.append({
                                'timestamp': signal.timestamp.isoformat(),
                                'temperature_signal': signal.temperature_signal,
                                'inventory_signal': signal.inventory_signal,
                                'storm_signal': signal.storm_signal,
                                'total_signal': signal.total_signal,
                                'action': signal.action,
                                'symbol': signal.symbol,
                                'confidence': signal.confidence
                            })
                        return jsonify(data_list)
                    else:
                        return jsonify({'error': 'No historical signals available'})
                except Exception as e:
                    self.logger.error(f"Error getting historical signals: {e}")
                    return jsonify({'error': str(e)})
        
        @self.app.route('/api/logs')
        def get_logs():
            try:
                # Try multiple possible log file locations
                log_file_paths = [
                    'logs/trading_bot.log',
                    'trading_bot.log',
                    'logs/errors.log',
                    'errors.log'
                ]
                
                logs = []
                log_file_found = False
                
                for log_file_path in log_file_paths:
                        if os.path.exists(log_file_path):
                            log_file_found = True
                            self.logger.info(f"Reading logs from: {log_file_path}")
                            
                            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                lines = f.readlines()
                                # Get last 100 lines
                                for line in lines[-100:]:
                                    line = line.strip()
                                    if line:
                                        # Try different parsing approaches
                                        if ' - ' in line:
                                            # Standard format: timestamp - logger - level - message
                                            parts = line.split(' - ', 3)
                                            if len(parts) >= 4:
                                                timestamp = parts[0]
                                                logger_name = parts[1]
                                                level = parts[2]
                                                message = parts[3]
                                                
                                                logs.append({
                                                    'timestamp': timestamp,
                                                    'logger': logger_name,
                                                    'level': level,
                                                    'message': message
                                                })
                                            elif len(parts) >= 2:
                                                # Fallback: just timestamp and message
                                                timestamp = parts[0]
                                                message = ' - '.join(parts[1:])
                                                
                                                logs.append({
                                                    'timestamp': timestamp,
                                                    'logger': 'unknown',
                                                    'level': 'INFO',
                                                    'message': message
                                                })
                                        else:
                                            # Simple format: just the line
                                            logs.append({
                                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                'logger': 'system',
                                                'level': 'INFO',
                                                'message': line
                                            })
                        break
                
                if not log_file_found:
                    self.logger.warning("No log file found in any expected location")
                    logs.append({
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'logger': 'system',
                        'level': 'WARNING',
                        'message': 'No log file found. Check if the bot is running and logging.'
                    })
                
                # Sort by timestamp (newest first)
                logs.sort(key=lambda x: x['timestamp'], reverse=True)
                
                return jsonify(logs)
            except Exception as e:
                self.logger.error(f"Error getting logs: {e}")
                return jsonify({'error': str(e)})
    
    def _setup_socket_events(self):
        # Setup SocketIO events
        
        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info('Dashboard client connected')
            emit('status', {'status': 'connected'})
            emit('data_update', self.dashboard_data)
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.info('Dashboard client disconnected')
        
        @self.socketio.on('request_update')
        def handle_update_request():
            emit('data_update', self.dashboard_data)
    
    def _fetch_latest_signals(self):
        # Fetch latest signals from data sources
        try:
            from data_sources.weather_data import WeatherDataFetcher
            from data_sources.eia_data import EIADataFetcher
            from data_sources.noaa_data import NOAADataFetcher
            
            weather_fetcher = WeatherDataFetcher(self.config)
            eia_fetcher = EIADataFetcher(self.config)
            noaa_fetcher = NOAADataFetcher(self.config)
            
            temp_signal = weather_fetcher.get_regional_hdd_signal()
            inventory_signal = eia_fetcher.calculate_inventory_signal()
            storm_signal = noaa_fetcher.calculate_storm_signal()
            
            return temp_signal, inventory_signal, storm_signal
        except Exception as e:
            self.logger.error(f"Error fetching signals: {e}")
            return 0.0, 0.0, 0.0
    
    def update_data(self, signal_data=None, trade_data=None, portfolio_data=None, log_data=None):
        # Update dashboard data and emit to clients
        try:
            if signal_data:
                self.dashboard_data['signals'].append(signal_data)
                # Keep only last 100 signals
                if len(self.dashboard_data['signals']) > 100:
                    self.dashboard_data['signals'] = self.dashboard_data['signals'][-100:]
            
            if trade_data:
                self.dashboard_data['trades'].append(trade_data)
                # Keep only last 50 trades
                if len(self.dashboard_data['trades']) > 50:
                    self.dashboard_data['trades'] = self.dashboard_data['trades'][-50:]
            
            if portfolio_data:
                self.dashboard_data['portfolio'] = portfolio_data
            
            if log_data:
                self.dashboard_data['logs'].append(log_data)
                # Keep only last 200 logs
                if len(self.dashboard_data['logs']) > 200:
                    self.dashboard_data['logs'] = self.dashboard_data['logs'][-200:]
            
            self.dashboard_data['last_update'] = datetime.now().isoformat()
            
            # Emit update to connected clients
            self.socketio.emit('data_update', self.dashboard_data)
            
        except Exception as e:
            self.logger.error(f"Error updating dashboard data: {e}")
    
    def set_status(self, status: str):
        # Set dashboard status
        self.dashboard_data['status'] = status
        self.socketio.emit('status_update', {'status': status})
    
    def start_dashboard(self, host='127.0.0.1', port=5000, debug=False):
        # Start the dashboard server
        self.logger.info(f"Starting dashboard on http://{host}:{port}")
        self.set_status('running')
        
        try:
            self.socketio.run(self.app, host=host, port=port, debug=debug)
        except Exception as e:
            self.logger.error(f"Error starting dashboard: {e}")
            self.set_status('error')
    
    def start_dashboard_thread(self, host='127.0.0.1', port=5000):
        """Start dashboard in a separate thread"""
        if self.dashboard_thread and self.dashboard_thread.is_alive():
            return
        
        self.dashboard_thread = threading.Thread(
            target=self.start_dashboard,
            args=(host, port, False),
            daemon=True
        )
        self.dashboard_thread.start()
        
        # Wait a moment for the server to start
        time.sleep(2)
        self.logger.info(f"Dashboard started at http://{host}:{port}")
    
    def stop_dashboard(self):
        """Stop the dashboard"""
        self.set_status('stopped')
        self.running = False
