"""Live trading engine using Zerodha Kite Connect API."""

import csv
import math
import os
import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from kiteconnect import KiteConnect
from kiteconnect.exceptions import TokenException
from loguru import logger

from config import BROKERAGE, STOCK_SYMBOL

IST = timezone(timedelta(hours=5, minutes=30))
MARKET_OPEN = 9 * 60 + 15
MARKET_CLOSE = 15 * 60 + 30
TRADE_START = MARKET_OPEN + 15
TRADE_END = MARKET_CLOSE - 15
DAILY_LOSS_LIMIT = 0.05
MAX_CONSECUTIVE_LOSSES = 3
PAPER_WEEKS = 2
KITE_SYMBOL = STOCK_SYMBOL.replace(".NS", "")
YFINANCE_SYMBOL = STOCK_SYMBOL


def _required_lookback(strategy) -> int:
    """Return the longest period parameter across strategy params, else a safe default."""
    values = []
    for key, value in strategy.get_params().items():
        if isinstance(value, (int, float)) and value > 0 and not isinstance(value, bool):
            if "period" in key.lower() or key.lower() == "std":
                values.append(int(value))
    return max(values) if values else 60


class LiveTrader:
    """Live trading engine that places real orders via Zerodha Kite Connect."""

    def __init__(self, strategy, capital: float, brokerage: float, api_key: str, access_token: str):
        self.strategy = strategy
        self.capital = capital
        self.brokerage = brokerage
        self.initial_capital = capital
        self.paper_mode = False
        self.position = None
        self.trade_log = []
        self.consecutive_losses = 0
        self.daily_start_capital = capital
        self.daily_pnl = 0.0
        self.stopped_for_day = False
        self.last_trade_date = None
        self.token_expired = False
        self.lookback = _required_lookback(strategy) + 50
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)
        logger.info("LiveTrader initialized for {sym}", sym=KITE_SYMBOL)

    def _get_quote(self) -> float:
        """Fetch the latest tradable price for the configured symbol from Kite."""
        instrument = f"NSE:{KITE_SYMBOL}"
        try:
            ltp_data = self.kite.ltp([instrument])
            return float(ltp_data[instrument]["last_price"])
        except TokenException as exc:
            self.token_expired = True
            logger.critical("Access token expired: {exc}", exc=exc)
            return 0.0

    def _fetch_candles(self, count=None):
        """Fetch recent 1-minute candles from yfinance for signal computation."""
        raw = yf.download(
            YFINANCE_SYMBOL,
            interval="1m",
            period="7d",
            progress=False,
            auto_adjust=False,
        )
        if raw is None or raw.empty:
            logger.warning("No candle data from yfinance")
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
        return raw.tail(count or self.lookback)

    def _place_order(self, transaction_type: str, price: float, quantity: int) -> bool:
        """Place or simulate an order depending on paper_mode; return success."""
        if self.paper_mode:
            logger.info("PAPER {ttype}: {qty} shares @ {price}",
                        ttype=transaction_type, qty=quantity, price=price)
            return True
        try:
            order_id = self.kite.place_order(
                tradingsymbol=KITE_SYMBOL,
                exchange="NSE",
                transaction_type=transaction_type,
                quantity=quantity,
                price=price,
                order_type="LIMIT",
                product="MIS",
                variety="regular",
            )
            logger.info("LIVE {ttype} order placed: {oid}",
                        ttype=transaction_type, oid=order_id)
            return True
        except TokenException as exc:
            self.token_expired = True
            logger.critical("Access token expired: {exc}", exc=exc)
            return False
        except Exception as exc:
            logger.exception("Failed to place {ttype} order: {exc}",
                             ttype=transaction_type, exc=exc)
            return False

    def _reset_daily_if_needed(self):
        """Reset daily safety counters when a new trading day begins."""
        today = datetime.now(IST).date()
        if self.last_trade_date is None:
            self.last_trade_date = today
            return
        if today != self.last_trade_date:
            self.last_trade_date = today
            self.stopped_for_day = False
            self.consecutive_losses = 0
            self.daily_start_capital = self.capital
            self.daily_pnl = 0.0
            logger.info("New trading day: daily safety counters reset")

    def _check_safety(self) -> bool:
        """Return False if trading should be skipped this tick due to safety limits."""
        if self.stopped_for_day:
            logger.debug("Stopped for the day: daily loss limit or consecutive loss limit hit")
            return False
        if self.daily_pnl <= -DAILY_LOSS_LIMIT * self.daily_start_capital:
            logger.warning("Daily loss {pct:.1f}% exceeds limit. Stopped for the day.",
                           pct=abs(self.daily_pnl / self.daily_start_capital) * 100)
            self.stopped_for_day = True
            return False
        if self.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
            logger.warning("{n} consecutive losses. Stopped for the day.",
                           n=self.consecutive_losses)
            self.stopped_for_day = True
            return False
        return True

    def _within_trading_hours(self) -> bool:
        """Return True only during the tradable window on a weekday."""
        now = datetime.now(IST)
        if now.weekday() >= 5:
            return False
        minutes = now.hour * 60 + now.minute
        return TRADE_START <= minutes < TRADE_END

    def run_once(self):
        """Fetch live price, compute signals, and execute one trade if warranted."""
        self._reset_daily_if_needed()
        if not self._check_safety():
            return

        price = self._get_quote()
        if self.token_expired or price <= 0:
            return
        candles = self._fetch_candles()
        if candles.empty:
            logger.warning("No candle data, skipping tick")
            return

        data = self.strategy.compute_signals(candles)
        signal = int(data.iloc[-1]["signal"])
        timestamp = datetime.now(IST)

        if signal == 1 and self.position is None:
            quantity = math.floor(self.capital / price)
            if quantity <= 0:
                logger.warning("Insufficient capital for entry")
                return
            cost = quantity * price
            fee = cost * self.brokerage
            if not self._place_order("BUY", price, quantity):
                return
            self.capital -= cost + fee
            self.position = {
                "entry_time": timestamp,
                "entry_price": price,
                "quantity": quantity,
                "cost_basis": cost,
            }
            logger.info("BUY {qty} @ {price} | Capital: {cap:.2f}",
                        qty=quantity, price=price, cap=self.capital)

        elif signal == -1 and self.position is not None:
            exit_value = self.position["quantity"] * price
            fee = exit_value * self.brokerage
            pnl = exit_value - self.position["cost_basis"] - fee
            if not self._place_order("SELL", price, self.position["quantity"]):
                return
            self.capital += exit_value
            self.trade_log.append({
                "entry_time": self.position["entry_time"],
                "entry_price": self.position["entry_price"],
                "exit_time": timestamp,
                "exit_price": price,
                "quantity": self.position["quantity"],
                "cost_basis": self.position["cost_basis"],
                "exit_value": exit_value,
                "brokerage": fee,
                "pnl": pnl,
                "capital": self.capital,
            })
            self.daily_pnl += pnl
            if pnl < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0
            logger.info("SELL {qty} @ {price} | PnL: {pnl:.2f} | Cap: {cap:.2f}",
                        qty=self.position["quantity"], price=price,
                        pnl=pnl, cap=self.capital)
            self.position = None

    def _run(self, end_time=None):
        """Core trading loop. Runs until end_time (if set) or until Ctrl+C."""
        try:
            while True:
                if end_time is not None and datetime.now(IST) >= end_time:
                    logger.info("Scheduled end time reached")
                    break
                if self.token_expired:
                    logger.error("Token expired, shutting down gracefully")
                    break
                if not self._within_trading_hours():
                    time.sleep(30)
                    continue
                self.run_once()
                if self.token_expired:
                    logger.error("Token expired, shutting down gracefully")
                    break
                time.sleep(60)
        except KeyboardInterrupt:
            pass
        finally:
            self._save_and_exit()

    def run_paper_first(self):
        """Run in paper mode for 2 weeks to verify strategy, then switch to live."""
        self.paper_mode = True
        end_time = datetime.now(IST) + timedelta(weeks=PAPER_WEEKS)
        logger.info("Paper mode activated for {w} weeks until {et}",
                    w=PAPER_WEEKS, et=end_time.isoformat())
        print(f"Paper mode: {PAPER_WEEKS} weeks starting {datetime.now(IST).isoformat()}")
        self._run(end_time=end_time)
        self.paper_mode = False
        logger.info("Paper period complete. Switch to live mode by calling run_loop().")
        print("Paper period complete. Ready for live trading.")

    def run_loop(self):
        """Run live trading loop until interrupted by Ctrl+C."""
        self.paper_mode = False
        logger.info("Live trading loop started")
        print("Live trading running. Press Ctrl+C to stop.")
        self._run(end_time=None)

    def _save_and_exit(self):
        """Save trade log to CSV on exit and print final summary."""
        today = date.today().isoformat()
        prefix = "paper" if self.paper_mode else "live"
        path = f"results/{prefix}_trades_{today}.csv"
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
        print("Trader stopped.")