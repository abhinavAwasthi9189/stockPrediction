"""Fetch last 3 months of daily data and backtest Bollinger with tested params."""
import sys
sys.path.insert(0, ".")

from data.fetcher import fetch_daily
from strategies.bollinger_breakout import BollingerBreakout
from engine.backtester import Backtester
from metrics.analyzer import analyze_trades, print_report
from datetime import datetime, timedelta
from config import BACKTEST_CAPITAL, BROKERAGE, STOCK_SYMBOL

params = {"period": 10, "std_dev": 1.5}
df = fetch_daily(STOCK_SYMBOL, start_date=datetime.now() - timedelta(days=90))
if df is None or len(df) < 30:
    print(f"Not enough data: {len(df) if df is not None else 0} rows")
    sys.exit(1)

print(f"Data: {len(df)} rows ({df.index[0].date()} to {df.index[-1].date()})\n")

strategy = BollingerBreakout(params)
data = strategy.compute_signals(df)
bt = Backtester(strategy, data, BACKTEST_CAPITAL, BROKERAGE)
bt.run()
metrics = analyze_trades(bt.get_trade_log(), BACKTEST_CAPITAL)
print_report(metrics)

print("\n=== Individual Trades ===")
for t in bt.get_trade_log():
    print(f"  {t['entry_time'].date()} -> {t['exit_time'].date()} | "
          f"entry={t['entry_price']:.2f} exit={t['exit_price']:.2f} | "
          f"PnL={t['pnl']:.2f}")