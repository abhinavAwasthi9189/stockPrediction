"""Fetch 1-minute data, test all 3 strategies, print signals."""
import yfinance as yf
import pandas as pd
import sys
sys.path.insert(0, ".")

from strategies.bollinger_breakout import BollingerBreakout
from strategies.zscore_reversion import ZScoreReversion
from strategies.vwap_reversion import VWAPReversion
from config import BB_CONFIG, ZSCORE_CONFIG, VWAP_CONFIG

SYMBOL = "TATASTEEL.NS"

raw = yf.download(SYMBOL, interval="1m", period="5d", progress=False, auto_adjust=False)
if raw is None or raw.empty:
    print("No data")
    sys.exit(1)
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

# Get the latest full trading day
dates = sorted(raw.index.normalize().unique())
latest_day = dates[-1]
df = raw[raw.index.normalize() == latest_day].copy()
print(f"Data: {latest_day.date()} — {len(df)} candles ({df.index[0]} to {df.index[-1]})")
print(f"Close range: {df['close'].min():.2f} - {df['close'].max():.2f}")
print()

strategies = [
    ("BOLLINGER", BollingerBreakout(BB_CONFIG), BB_CONFIG),
    ("ZSCORE", ZScoreReversion(ZSCORE_CONFIG), ZSCORE_CONFIG),
    ("VWAP", VWAPReversion(VWAP_CONFIG), VWAP_CONFIG),
]

for name, strat, params in strategies:
    result = strat.compute_signals(df)
    signals = result[result["signal"] != 0]
    print(f"=== {name} (params: {params}) ===")
    if signals.empty:
        print("  No signals generated")
    else:
        for idx, row in signals.iterrows():
            print(f"  {idx.time()} | signal={int(row['signal']):+d} | close={row['close']:.2f}")
    print()