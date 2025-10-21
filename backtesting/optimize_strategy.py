# Optimizes trading strategy parameters using genetic algorithm and grid search to find the best configuration.

import sys
import os
import itertools
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import core components
from backtesting.core.backtest_engine import BacktestEngine
from backtesting.core.historical_data_loader import HistoricalDataLoader
from backtesting.core.signal_generator import HistoricalSignalGenerator
from backtesting.core.performance_analyzer import PerformanceAnalyzer
from backtesting.config import BacktestConfig


# Comprehensive optimizer that tests various parameter combinations
# to find the optimal trading strategy configuration.
class ComprehensiveOptimizer:
    
    # Initialize the optimizer.
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.results = []
        self.best_result = None
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('optimization.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Set backtest period (use recent period where UNG/KOLD data is available)
        self.start_date = datetime(2024, 10, 1)
        self.end_date = datetime(2025, 10, 21)
        
        # Define parameter ranges to test (only parameters that exist in BacktestConfig)
        self.parameter_ranges = {
            # Signal thresholds
            'buy_threshold': [0.4, 0.5, 0.6, 0.7, 0.8],  # Increased from 0.2-0.6
            'sell_threshold': [-0.8, -0.7, -0.6, -0.5, -0.4],  # Increased from -0.6 to -0.2
            
            # Signal weights (must sum to 1.0)
            'temperature_weight': [0.2, 0.3, 0.4, 0.5],
            'inventory_weight': [0.2, 0.3, 0.4, 0.5],
            'storm_weight': [0.1, 0.2, 0.3],
            
            # Position sizing
            'base_position_size': [500, 1000, 1500, 2000, 2500],
            'max_position_size': [3000, 4000, 5000, 6000],
            
            # Risk management
            'default_stop_loss_pct': [0.08, 0.10, 0.12, 0.15, 0.20],  # Increased from 0.02-0.10
            'take_profit_pct': [0.15, 0.20, 0.25, 0.30, 0.40],  # Increased from 0.08-0.25
            'trailing_stop_pct': [0.05, 0.08, 0.10, 0.12],  # Increased from 0.02-0.05
            
            # Trading costs
            'commission_per_trade': [0.5, 1.0, 1.5],  # Reduced options
            'slippage_pct': [0.0005, 0.001, 0.002],  # Added options
            
            # Strategy settings
            'confirmation_days': [1, 2, 3]
        }
        
        self.logger.info(f"Comprehensive Optimizer initialized")
        self.logger.info(f"Period: {self.start_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        self.logger.info(f"Total parameter combinations: {self._calculate_total_combinations()}")
    
    # Calculate total number of parameter combinations.
    def _calculate_total_combinations(self) -> int:
        total = 1
        for param, values in self.parameter_ranges.items():
            total *= len(values)
        return total
    
    # Validate parameter combination.
    def _validate_parameters(self, params: Dict[str, Any]) -> bool:
        # Buy threshold must be greater than sell threshold
        if params['buy_threshold'] <= params['sell_threshold']:
            return False
        
        # Weights must sum to 1.0 (within tolerance)
        total_weight = (params['temperature_weight'] + 
                       params['inventory_weight'] + 
                       params['storm_weight'])
        if abs(total_weight - 1.0) > 0.01:
            return False
        
        # Position sizes must be logical
        if params['base_position_size'] > params['max_position_size']:
            return False
        
        return True
    
    # Create BacktestConfig from parameters.
    def _create_config(self, params: Dict[str, Any]) -> BacktestConfig:
        # Load API keys from environment or config file
        import os
        from dotenv import load_dotenv
        
        # Load environment variables from config file
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.env')
        if os.path.exists(config_path):
            load_dotenv(config_path)
        
        # Load environment variables
        eia_key = os.getenv('EIA_API_KEY')
        self.logger.info(f"EIA API Key loaded: {'Yes' if eia_key else 'No'}")
        
        config = BacktestConfig(
            initial_capital=self.initial_capital,
            start_date=self.start_date,
            end_date=self.end_date,
            # Add API keys for real data
            eia_api_key=eia_key,
            weather_api_key=os.getenv('WEATHER_API_KEY'),  # Open-Meteo doesn't require API key
            noaa_api_key=os.getenv('NOAA_API_KEY'),  # NOAA doesn't require API key
            **params
        )
        return config
    
    # Run a single backtest with given configuration.
    def _run_single_backtest(self, config: BacktestConfig) -> Dict[str, Any]:
        try:
            self.logger.debug(f"Running backtest with config: {config.to_dict()}")
            
            # Load historical data
            data_loader = HistoricalDataLoader(config)
            historical_data = data_loader.load_all_historical_data(
                config.start_date, 
                config.end_date
            )
            
            if not historical_data or len(historical_data) == 0:
                self.logger.warning("No historical data loaded")
                return {'success': False, 'error': 'No historical data'}
            
            # Generate signals
            signal_generator = HistoricalSignalGenerator(config)
            signals = signal_generator.generate_signals(historical_data)
            
            if not signals:
                self.logger.warning("No signals generated")
                return {'success': False, 'error': 'No signals generated'}
            
            # Run backtest
            engine = BacktestEngine(config)
            
            # Extract price data for backtest engine
            price_data = {
                'ung_price': historical_data['ung_price'],
                'kold_price': historical_data['kold_price']
            }
            
            backtest_result = engine.run_backtest(signals, price_data, self.start_date, self.end_date)
            
            # Analyze performance
            analyzer = PerformanceAnalyzer(config)
            metrics = analyzer.analyze_backtest_result(backtest_result)
            
            return {
                'config': config.to_dict(),
                'metrics': metrics,
                'backtest_result': backtest_result,
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"Error in backtest: {str(e)}")
            return {
                'config': config.to_dict(),
                'error': str(e),
                'success': False
            }
    
    def optimize_grid_search(self, max_combinations: int = 1000) -> Dict[str, Any]:
        """Perform grid search optimization."""
        self.logger.info(f"Starting grid search optimization (max {max_combinations} combinations)")
        
        # Generate parameter combinations
        param_names = list(self.parameter_ranges.keys())
        param_values = list(self.parameter_ranges.values())
        combinations = list(itertools.product(*param_values))
        
        # Limit combinations if too many
        if len(combinations) > max_combinations:
            # Sample randomly
            import random
            combinations = random.sample(combinations, max_combinations)
            self.logger.info(f"Sampled {max_combinations} combinations from {len(list(itertools.product(*param_values)))} total")
        
        self.logger.info(f"Testing {len(combinations)} parameter combinations...")
        
        # Test each combination
        for i, combination in enumerate(combinations):
            params = dict(zip(param_names, combination))
            
            # Validate parameters
            if not self._validate_parameters(params):
                continue
            
            # Create config and run backtest
            config = self._create_config(params)
            result = self._run_single_backtest(config)
            
            if result['success']:
                self.results.append(result)
                
                # Check if this is the best result so far
                total_return = result['metrics'].get('Total Return (%)', -100)
                if (self.best_result is None or 
                    total_return > self.best_result['metrics'].get('Total Return (%)', -100)):
                    self.best_result = result
                
                # Print progress
                if (i + 1) % 50 == 0 or i == len(combinations) - 1:
                    best_return = self.best_result['metrics'].get('Total Return (%)', 0)
                    current_return = result['metrics'].get('Total Return (%)', 0)
                    self.logger.info(f"Progress: {i + 1}/{len(combinations)} | "
                                   f"Best: {best_return:.2f}% | Current: {current_return:.2f}%")
        
        return self.best_result
    
    # Perform genetic algorithm optimization.
    def optimize_genetic_algorithm(self, population_size: int = 50, generations: int = 20) -> Dict[str, Any]:
        self.logger.info(f"Starting genetic algorithm optimization")
        self.logger.info(f"Population size: {population_size}, Generations: {generations}")
        
        # Initialize population
        population = []
        for _ in range(population_size):
            # Generate random valid parameters
            while True:
                params = {}
                for param, values in self.parameter_ranges.items():
                    params[param] = np.random.choice(values)
                
                if self._validate_parameters(params):
                    population.append(params)
                    break
        
        # Evolution loop
        for generation in range(generations):
            self.logger.info(f"Generation {generation + 1}/{generations}")
            
            # Evaluate population
            fitness_scores = []
            for params in population:
                config = self._create_config(params)
                result = self._run_single_backtest(config)
                
                if result['success']:
                    fitness = result['metrics'].get('Total Return (%)', -100)
                    fitness_scores.append(fitness)
                    self.results.append(result)
                    
                    # Update best result
                    if (self.best_result is None or 
                        fitness > self.best_result['metrics'].get('Total Return (%)', -100)):
                        self.best_result = result
                else:
                    fitness_scores.append(-100)
            
            # Selection, crossover, and mutation
            if generation < generations - 1:  # Don't evolve on last generation
                population = self._evolve_population(population, fitness_scores)
            
            # Log best fitness
            best_fitness = max(fitness_scores) if fitness_scores else -100
            self.logger.info(f"Best fitness: {best_fitness:.2f}%")
        
        return self.best_result
    
    # Evolve population using selection, crossover, and mutation.
    def _evolve_population(self, population: List[Dict], fitness_scores: List[float]) -> List[Dict]:
        new_population = []
        
        # Keep top 20% (elitism)
        elite_count = max(1, len(population) // 5)
        elite_indices = np.argsort(fitness_scores)[-elite_count:]
        for idx in elite_indices:
            new_population.append(population[idx].copy())
        
        # Generate rest through crossover and mutation
        while len(new_population) < len(population):
            # Selection (tournament selection)
            parent1 = self._tournament_selection(population, fitness_scores)
            parent2 = self._tournament_selection(population, fitness_scores)
            
            # Crossover
            child = self._crossover(parent1, parent2)
            
            # Mutation
            child = self._mutate(child)
            
            # Validate child
            if self._validate_parameters(child):
                new_population.append(child)
        
        return new_population
    
    # Tournament selection for genetic algorithm.
    def _tournament_selection(self, population: List[Dict], fitness_scores: List[float], tournament_size: int = 3) -> Dict:
        tournament_indices = np.random.choice(len(population), tournament_size, replace=False)
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_idx = tournament_indices[np.argmax(tournament_fitness)]
        return population[winner_idx]
    
    # Single-point crossover for genetic algorithm.
    def _crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        child = {}
        for param in self.parameter_ranges.keys():
            if np.random.random() < 0.5:
                child[param] = parent1[param]
            else:
                child[param] = parent2[param]
        return child
    
    # Mutation for genetic algorithm.
    def _mutate(self, individual: Dict, mutation_rate: float = 0.1) -> Dict:
        mutated = individual.copy()
        for param, values in self.parameter_ranges.items():
            if np.random.random() < mutation_rate:
                mutated[param] = np.random.choice(values)
        return mutated
    
    # Print optimization results.
    def print_results(self):
        if not self.results:
            self.logger.error("No successful results found.")
            return
        
        # Sort results by return
        successful_results = [r for r in self.results if r['success']]
        sorted_results = sorted(successful_results, 
                              key=lambda x: x['metrics'].get('Total Return (%)', -100), 
                              reverse=True)
        
        print(f"\n{'='*80}")
        print("OPTIMIZATION RESULTS (Top 10)")
        print(f"{'='*80}")
        
        print(f"{'Rank':<4} {'Return%':<8} {'Sharpe':<7} {'MaxDD%':<7} {'Trades':<6} {'Win%':<6}")
        print("-" * 50)
        
        for i, result in enumerate(sorted_results[:10]):
            metrics = result['metrics']
            print(f"{i+1:<4} {metrics.get('Total Return (%)', 0):<8.2f} "
                  f"{metrics.get('Sharpe Ratio', 0):<7.2f} "
                  f"{metrics.get('Max Drawdown (%)', 0):<7.2f} "
                  f"{metrics.get('Total Trades', 0):<6} "
                  f"{metrics.get('Win Rate (%)', 0):<6.1f}")
        
        # Print best configuration
        if self.best_result:
            print(f"\n{'='*60}")
            print("BEST CONFIGURATION")
            print(f"{'='*60}")
            
            metrics = self.best_result['metrics']
            config = self.best_result['config']
            
            print(f"Total Return: {metrics.get('Total Return (%)', 0):.2f}%")
            print(f"Sharpe Ratio: {metrics.get('Sharpe Ratio', 0):.2f}")
            print(f"Max Drawdown: {metrics.get('Max Drawdown (%)', 0):.2f}%")
            print(f"Total Trades: {metrics.get('Total Trades', 0)}")
            print(f"Win Rate: {metrics.get('Win Rate (%)', 0):.2f}%")
            print(f"Profit Factor: {metrics.get('Profit Factor', 0):.2f}")
            
            print(f"\nOPTIMAL PARAMETERS:")
            for param, value in config.items():
                if param in self.parameter_ranges:
                    print(f"  {param}: {value}")
    
    # Save results to file.
    def save_results(self, filename: str = "optimization_results.json"):
        results_data = {
            'best_result': self.best_result,
            'all_results': self.results,
            'parameter_ranges': self.parameter_ranges,
            'summary': {
                'total_tests': len(self.results),
                'successful_tests': len([r for r in self.results if r['success']]),
                'best_return_pct': self.best_result['metrics'].get('Total Return (%)', 0) if self.best_result else None,
                'optimization_period': {
                    'start': self.start_date.isoformat(),
                    'end': self.end_date.isoformat()
                }
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        self.logger.info(f"Results saved to {filename}")


# Main function.
def main():
    print("="*80)
    print("COMPREHENSIVE STRATEGY OPTIMIZATION")
    print("Finding optimal parameters for maximum profit over 2 years (2022-2023)")
    print("="*80)
    
    # Initialize optimizer
    optimizer = ComprehensiveOptimizer(initial_capital=100000)
    
    choice = "2"  # Automatically choose Genetic Algorithm
    
    if choice == "1":
        print("\nStarting Grid Search Optimization...")
        best_result = optimizer.optimize_grid_search(max_combinations=500)
    elif choice == "2":
        print("\n Starting Genetic Algorithm Optimization...")
        best_result = optimizer.optimize_genetic_algorithm(population_size=30, generations=15)
    elif choice == "3":
        print("\n Starting Both Optimization Methods...")
        print("\n--- Grid Search ---")
        grid_result = optimizer.optimize_grid_search(max_combinations=300)
        print("\n--- Genetic Algorithm ---")
        genetic_result = optimizer.optimize_genetic_algorithm(population_size=20, generations=10)
        
        # Compare results
        grid_return = grid_result['metrics'].get('Total Return (%)', -100) if grid_result else -100
        genetic_return = genetic_result['metrics'].get('Total Return (%)', -100) if genetic_result else -100
        
        if grid_return > genetic_return:
            best_result = grid_result
            print(f"\nGrid Search performed better: {grid_return:.2f}% vs {genetic_return:.2f}%")
        else:
            best_result = genetic_result
            print(f"\nGenetic Algorithm performed better: {genetic_return:.2f}% vs {grid_return:.2f}%")
    else:
        print("Invalid choice. Running grid search by default.")
        best_result = optimizer.optimize_grid_search(max_combinations=500)
    
    # Print and save results
    optimizer.print_results()
    optimizer.save_results()
    
    print(f"\n{'='*80}")
    print("OPTIMIZATION COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
