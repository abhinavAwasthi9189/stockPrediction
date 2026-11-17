"""Central configuration for the algorithmic trading bot."""

STOCK_SYMBOL = "TATASTEEL.NS"
STOCK_TOKEN = "YOUR_KITE_TOKEN"

INITIAL_CAPITAL = 500
BACKTEST_CAPITAL = 500000
BROKERAGE = 0.0003
TIMEFRAME = "1m"
TRAIN_SPLIT = 0.8
LOG_LEVEL = "INFO"

# Bollinger — intraday tuned on 5d 1m data: period=20, std_dev=2.0 (53 trades, 67.9% win, PF=2.68)
BB_CONFIG = {"period": 20, "std_dev": 2.0}

# Z-Score — intraday tuned on 5d 1m data: lookback=30, entry_z=-2.0, exit_z=-0.5
ZSCORE_CONFIG = {"lookback_period": 30, "entry_z": -2.0, "exit_z": -0.5}

# VWAP — intraday tuned on 5d 1m data: lookback=15, threshold=0.2%
VWAP_CONFIG = {"lookback_period": 15, "threshold_pct": 0.2}

NIFTY_50 = [
    "TATASTEEL.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
]