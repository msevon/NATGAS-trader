# NATGAS TRADER

A Python trading bot that trades natural gas ETFs (BOIL/KOLD) using multiple data sources including Yahoo Finance (for price data), EIA (for US natural gas storage data), NOAA (for storm alerts), and weather APIs (for heating degree days).

## Features

- **Weather analysis**: Fetches daily weather forecasts and calculates heating degree days (HDD) for key US regions
- **Storage data**: Retrieves weekly US natural gas storage data from EIA API
- **Storm alerts**: Monitors NOAA weather alerts for supply disruption signals
- **Signal processing**: Combines all signals with configurable weights
- **Paper trading**: Executes trades through Alpaca API in paper trading mode
- **Real-time dashboard**: Beautiful dark-themed web dashboard with live data updates
- **Comprehensive logging**: Logs all signals, trades, and portfolio status

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Get API keys**:
   - **Alpaca API** (Required): Sign up at https://app.alpaca.markets/paper/dashboard/overview
   - **EIA API** (Optional): Register at https://www.eia.gov/opendata/register.php

3. **Configure environment**:
   ```bash
   cp env_example.txt .env
   # Edit .env with your API keys
   ```

4. **Run the bot**:
   ```bash
   # Default: Run continuously with dashboard (every 6 hours)
   python main.py
   
   # Run once with dashboard
   python main.py once
   
   # Run continuously with custom interval
   python main.py continuous 12    # Every 12 hours
   
   # Dashboard only mode
   python main.py dashboard
   ```

5. **Access dashboard**:
   - Open your browser to `http://127.0.0.1:5000`
   - Monitor real-time trading signals, portfolio, and trades
   - Beautiful dark theme with live data updates

## Configuration

The bot can be configured through environment variables or by modifying `config.py`:

- `SYMBOL`: Bullish ETF symbol to trade (default: BOIL)
- `INVERSE_SYMBOL`: Bearish ETF symbol to trade (default: KOLD)
- `POSITION_SIZE`: Dollar amount per trade (default: $1000)
- `BUY_THRESHOLD`: Signal threshold to buy (default: 0.3)
- `SELL_THRESHOLD`: Signal threshold to sell (default: -0.3)
- Signal weights: `TEMPERATURE_WEIGHT`, `INVENTORY_WEIGHT`, `STORM_WEIGHT`

## Signal logic

1. **Temperature signal**: Based on heating degree days (HDD)
   - Colder than average → Bullish signal
   - Warmer than average → Bearish signal

2. **Inventory signal**: Based on natural gas storage levels
   - Lower than average → Bullish signal
   - Higher than average → Bearish signal

3. **Storm signal**: Based on weather alerts
   - Severe weather events → Bullish signal (supply disruption)

4. **Total signal**: Weighted combination of all signals
   - Above threshold → Buy ETF
   - Below threshold → Sell ETF
   - Between thresholds → Hold

## Logging

The bot creates comprehensive logs in the `logs/` directory:
- `trading_bot.log`: Main log file
- `signals.log`: All trading signals
- `trades.log`: All trade executions
- `portfolio.log`: Portfolio status updates
- `api_calls.log`: API call tracking
- `errors.log`: Error logging

## Safety features

- **Paper trading only**: Uses Alpaca paper trading API
- **Error handling**: Comprehensive error handling for API failures
- **Position limits**: Configurable position sizes
- **Signal validation**: Validates signals before trading

## Disclaimer

Trading involves risk, past performance does not guarantee future results. Always test algorithmic trading bots thoroughly in paper trading mode before considering live trading.
