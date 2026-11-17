"""Paper trading engine that simulates live trading with 1-minute candles."""

import csv
import math
import os
import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from loguru import logger

from config import STOCK_SYMBOL

IST = timezone(timedelta(hours=5, minutes=30))
MARKET_OPEN = 9 * 60 + 15
MARKET_CLOSE = 15 * 60 + 30


def _required_lookback(strategy) -> int:
    """Return the longest period parameter across strategy params, else a safe default."""
    values = []
    for key, value in strategy.get_params().items():
        if isinstance(value, (int, float)) and value > 0 and not isinstance(value, bool):
            if "period" in key.lower() or key.lower() == "std":
                values.append(int(value))
    return max(values) if values else 60


class PaperTrader:
    """Simulate live trading with 1-minute candles fetched from yfinance."""

    def __init__(self, strategy, capital: float, brokerage: float):
        """Initialize the paper trader with a strategy, starting capital, and brokerage rate."""
        self.strategy = strategy
        self.capital = capital
        self.brokerage = brokerage
        self.initial_capital = capital
        self.position = None
        self.trade_log = []
        self.running_capital = capital
        self.lookback = _required_lookback(strategy) + 50

    def _fetch_live_candles(self, count=None):
        """Fetch the last `count` 1-minute candles for the configured symbol from yfinance."""
        raw = yf.download(
            STOCK_SYMBOL,
            interval="1m",
            period="7d",
            progress=False,
            auto_adjust=False,
        )
        if raw is None or raw.empty:
            logger.warning("No data returned from yfinance")
            return pd.DataFrame()
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw.columns = [str(col).lower() for col in raw.columns]
        raw = raw.reset_index()
        if "Datetime" in raw.columns:
            raw = raw.rename(columns={"Datetime": "datetime"})
        elif "Date" in raw.columns:
            raw = raw.rename(columns={"Date": "datetime"})
        raw = raw[["datetime", "open", "high", "low", "close", "volume"]]
        raw["datetime"] = pd.to_datetime(raw["datetime"])
        raw = raw.set_index("datetime")
        raw = raw.tail(count or self.lookback)
        logger.debug("Fetched {} 1m candles", len(raw))
        return raw

    def run_once(self):
        """Fetch latest candles, compute signals, and execute one trading step."""
        df = self._fetch_live_candles()
        if df.empty:
            return
        data = self.strategy.compute_signals(df)
        latest = data.iloc[-1]
        signal = int(latest["signal"])
        close = float(latest["close"])
        timestamp = data.index[-1]

        position_value = self.position["quantity"] * close if self.position else 0
        total_equity = self.capital + position_value
        running_pnl = total_equity - self.initial_capital

        if signal == 1 and self.position is None:
            quantity = math.floor(self.capital / close)
            if quantity <= 0:
                logger.warning("Insufficient capital for entry at {ts}", ts=timestamp)
                return
            cost = quantity * close
            fee = cost * self.brokerage
            self.capital -= cost + fee
            self.position = {
                "entry_time": timestamp,
                "entry_price": close,
                "quantity": quantity,
                "cost_basis": cost,
            }
            logger.info("PAPER ENTRY at {ts}: {qty} shares @ {price}",
                        ts=timestamp, qty=quantity, price=close)
            print(f"[{timestamp}] SIGNAL=+1 BUY  {quantity} shares @ {close:.2f} | "
                  f"Capital: {self.capital:.2f}")

        elif signal == -1 and self.position is not None:
            exit_value = self.position["quantity"] * close
            fee = exit_value * self.brokerage
            pnl = exit_value - self.position["cost_basis"] - fee
            self.capital += exit_value
            self.trade_log.append({
                "entry_time": self.position["entry_time"],
                "entry_price": self.position["entry_price"],
                "exit_time": timestamp,
                "exit_price": close,
                "quantity": self.position["quantity"],
                "cost_basis": self.position["cost_basis"],
                "exit_value": exit_value,
                "brokerage": fee,
                "pnl": pnl,
                "capital": self.capital,
            })
            logger.info("PAPER EXIT at {ts}: qty {qty} @ {price}, pnl {pnl}",
                        ts=timestamp, qty=self.position["quantity"],
                        price=close, pnl=round(pnl, 2))
            print(f"[{timestamp}] SIGNAL=-1 SELL {self.position['quantity']} shares @ {close:.2f} | "
                  f"PnL: {pnl:.2f} | Capital: {self.capital:.2f}")
            self.position = None
            if len(self.trade_log) % 5 == 0:
                self._print_summary()
        else:
            print(f"[{timestamp}] SIGNAL={signal} No action | "
                  f"Equity: {total_equity:.2f} | Running P&L: {running_pnl:.2f}")

    def _print_summary(self):
        """Print a running summary of win rate, total P&L, and current position."""
        pnls = [t["pnl"] for t in self.trade_log]
        wins = sum(1 for p in pnls if p > 0)
        total = len(pnls)
        win_rate = (wins / total) * 100 if total else 0
        total_pnl = sum(pnls)
        pos_str = (
            f"Position: {self.position['quantity']} shares @ {self.position['entry_price']:.2f}"
            if self.position else "Position: None"
        )
        print(f"--- Summary ({total} trades) --- "
              f"Win%: {win_rate:.1f}% | Total PnL: {total_pnl:.2f} | {pos_str}")

    def run_loop(self):
        """Run the paper trading loop every 60s during market hours, Mon-Fri."""
        logger.info("Paper trader started. Running Mon-Fri 9:15-15:30 IST.")
        print("Paper trader running. Press Ctrl+C to stop and save results.")
        try:
            while True:
                now = datetime.now(IST)
                if now.weekday() >= 5:
                    logger.debug("Weekend, sleeping 1 hour")
                    time.sleep(3600)
                    continue
                minutes_since_midnight = now.hour * 60 + now.minute
                if minutes_since_midnight < MARKET_OPEN or minutes_since_midnight >= MARKET_CLOSE:
                    logger.debug("Outside market hours, sleeping 60s")
                    time.sleep(60)
                    continue
                self.run_once()
                time.sleep(60)
        except KeyboardInterrupt:
            self._save_and_exit()

    def _save_and_exit(self):
        """Save trade log to CSV on Ctrl+C and print final summary."""
        today = date.today().isoformat()
        path = f"results/paper_trades_{today}.csv"
        os.makedirs("results", exist_ok=True)
        if self.trade_log:
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.trade_log[0].keys())
                writer.writeheader()
                writer.writerows(self.trade_log)
            logger.info("Saved {n} trades to {path}", n=len(self.trade_log), path=path)
            print(f"\nTrades saved to {path}")
        total_pnl = sum(t["pnl"] for t in self.trade_log) if self.trade_log else 0
        print(f"Final Capital: {self.capital:.2f} | "
              f"Total PnL: {total_pnl:.2f} | Trades: {len(self.trade_log)}")
        print("Paper trader stopped.")