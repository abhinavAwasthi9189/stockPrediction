"""Central configuration for the algorithmic trading bot."""

STOCK_SYMBOL = "ITC.NS"
STOCK_TOKEN = "YOUR_KITE_TOKEN"

INITIAL_CAPITAL = 500
BACKTEST_CAPITAL = 500000
BROKERAGE = 0.0003
TIMEFRAME = "1m"
TRAIN_SPLIT = 0.8
LOG_LEVEL = "INFO"

# Bollinger breakout — tuned on 1-minute sweep: period=30, std_dev=1.5
BB_CONFIG = {"period": 30, "std_dev": 1.5}

# Z-Score Mean Reversion — tuned on 3yr sweep: lookback=60, entry_z=-1.0, exit_z=-1.0
ZSCORE_CONFIG = {"lookback_period": 60, "entry_z": -1.0, "exit_z": -1.0}

# VWAP Reversion — tuned on 3yr sweep: lookback=10, threshold=1%
VWAP_CONFIG = {"lookback_period": 10, "threshold_pct": 1}

NIFTY_50 = [
    "ITC.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
]