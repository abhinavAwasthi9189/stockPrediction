"""Central configuration for the algorithmic trading bot."""

STOCK_SYMBOL = "POWERGRID.NS"
STOCK_TOKEN = "YOUR_KITE_TOKEN"

INITIAL_CAPITAL = 500
BACKTEST_CAPITAL = 500000
BROKERAGE = 0.0003
TIMEFRAME = "1m"
TRAIN_SPLIT = 0.8
LOG_LEVEL = "INFO"

# Bollinger breakout — no viable params found for POWERGRID daily data
BB_CONFIG = {"period": 10, "std_dev": 1.5}

# Z-Score Mean Reversion — tuned on POWERGRID daily sweep: lookback=50, entry_z=-1.0, exit_z=-1.0
ZSCORE_CONFIG = {"lookback_period": 50, "entry_z": -1.0, "exit_z": -1.0}

# VWAP Reversion — tuned on POWERGRID 1m sweep: lookback=10, threshold=0.3%
VWAP_CONFIG = {"lookback_period": 10, "threshold_pct": 0.3}

NIFTY_50 = [
    "POWERGRID.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
]