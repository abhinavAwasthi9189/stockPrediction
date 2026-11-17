"""Test intraday param variations for all 3 strategies."""
import yfinance as yf
import pandas as pd
import sys
sys.path.insert(0, ".")

from strategies.bollinger_breakout import BollingerBreakout
from strategies.zscore_reversion import ZScoreReversion
from strategies.vwap_reversion import VWAPReversion
from engine.backtester import Backtester
from metrics.analyzer import analyze_trades, print_report

SYMBOL = "TATASTEEL.NS"

raw = yf.download(SYMBOL, interval="1m", period="5d", progress=False, auto_adjust=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.columns = [str(c).lower() for c in raw.columns]
raw = raw.reset_index()
if "Datetime" in raw.columns:
    raw = raw.rename(columns={"Datetime": "datetime"})
elif "Date" in raw.columns:
    raw = raw.rename(columns={"Date": "datetime"})
raw["datetime"] = pd.to_datetime(raw["datetime"])
raw = raw.set_index("datetime")

CAPITAL = 500000
BROKERAGE = 0.0003

def test(strat_cls, param_list):
    print(f"{'='*60}")
    print(f"{strat_cls.__name__}")
    print(f"{'='*60}")
    for p in param_list:
        strat = strat_cls(p)
        data = strat.compute_signals(raw)
        bt = Backtester(strat, data, CAPITAL, BROKERAGE)
        bt.run()
        m = analyze_trades(bt.get_trade_log(), CAPITAL)
        trades = m["total_trades"]
        wr = m["win_rate"]
        pf = m["profit_factor"]
        pnl = m["total_pnl"]
        print(f"  {p} -> trades={trades:2d} win%={wr:5.1f} pf={pf:>8.2f} pnl={pnl:>10.2f}")

print(f"\nData: {len(raw)} 1m candles ({raw.index.min()} to {raw.index.max()})")

# Bollinger: vary period & std_dev
test(BollingerBreakout, [
    {"period": 20, "std_dev": 2.0},
    {"period": 20, "std_dev": 2.5},
    {"period": 20, "std_dev": 3.0},
    {"period": 30, "std_dev": 2.0},
    {"period": 30, "std_dev": 2.5},
    {"period": 30, "std_dev": 3.0},
    {"period": 40, "std_dev": 2.0},
    {"period": 40, "std_dev": 2.5},
    {"period": 40, "std_dev": 3.0},
    {"period": 50, "std_dev": 2.0},
    {"period": 50, "std_dev": 2.5},
    {"period": 50, "std_dev": 3.0},
])

# ZScore: vary lookback, entry_z, exit_z
test(ZScoreReversion, [
    {"lookback_period": 20, "entry_z": -2.0, "exit_z": -0.5},
    {"lookback_period": 20, "entry_z": -2.0, "exit_z": 0.0},
    {"lookback_period": 20, "entry_z": -1.5, "exit_z": -0.5},
    {"lookback_period": 30, "entry_z": -2.0, "exit_z": -0.5},
    {"lookback_period": 30, "entry_z": -2.0, "exit_z": 0.0},
    {"lookback_period": 30, "entry_z": -1.5, "exit_z": -0.5},
    {"lookback_period": 40, "entry_z": -2.0, "exit_z": -0.5},
    {"lookback_period": 40, "entry_z": -2.0, "exit_z": 0.0},
    {"lookback_period": 40, "entry_z": -1.5, "exit_z": -0.5},
    {"lookback_period": 50, "entry_z": -2.0, "exit_z": -0.5},
    {"lookback_period": 50, "entry_z": -2.0, "exit_z": 0.0},
    {"lookback_period": 50, "entry_z": -1.5, "exit_z": -0.5},
])

# VWAP: vary lookback & threshold
test(VWAPReversion, [
    {"lookback_period": 5, "threshold_pct": 0.1},
    {"lookback_period": 5, "threshold_pct": 0.2},
    {"lookback_period": 5, "threshold_pct": 0.3},
    {"lookback_period": 5, "threshold_pct": 0.5},
    {"lookback_period": 10, "threshold_pct": 0.1},
    {"lookback_period": 10, "threshold_pct": 0.2},
    {"lookback_period": 10, "threshold_pct": 0.3},
    {"lookback_period": 10, "threshold_pct": 0.5},
    {"lookback_period": 15, "threshold_pct": 0.1},
    {"lookback_period": 15, "threshold_pct": 0.2},
    {"lookback_period": 15, "threshold_pct": 0.3},
    {"lookback_period": 15, "threshold_pct": 0.5},
])