"""Backtesting engine for signal-based trading strategies."""

import math

import pandas as pd
from loguru import logger


class Backtester:
    """Replay a strategy's signals over historical data and simulate trades with brokerage."""

    def __init__(self, strategy, data: pd.DataFrame, capital: float, brokerage: float):
        """Initialize the backtester with strategy, data, starting capital and brokerage."""
        self.strategy = strategy
        self.data = data
        self.initial_capital = capital
        self.capital = capital
        self.brokerage = brokerage
        self.trade_log = []
        self.position = None

    def run(self):
        """Simulate trades over each row of data in chronological order."""
        for row in self.data.itertuples():
            timestamp = row.Index
            close = row.close
            signal = row.signal

            if signal == 1 and self.position is None:
                quantity = math.floor(self.capital / close)
                if quantity <= 0:
                    logger.warning("Insufficient capital for entry at {ts}", ts=timestamp)
                    continue
                cost = quantity * close
                brokerage_fee = cost * self.brokerage
                self.capital -= cost
                self.capital -= brokerage_fee
                self.position = {
                    "entry_time": timestamp,
                    "entry_price": close,
                    "quantity": quantity,
                    "cost_basis": cost,
                }
                logger.info("Entry at {ts}: {qty} shares @ {price}",
                            ts=timestamp, qty=quantity, price=close)

            elif signal == -1 and self.position is not None:
                self._close_position(timestamp, close)

        if self.position is not None:
            last_row = self.data.iloc[-1]
            logger.info("Closing open position at last candle {ts}", ts=last_row.name)
            self._close_position(last_row.name, last_row.close)

    def _close_position(self, timestamp, close):
        """Close the open position, settle PnL, and record the trade."""
        position = self.position
        exit_value = position["quantity"] * close
        brokerage_fee = exit_value * self.brokerage
        pnl = exit_value - position["cost_basis"] - brokerage_fee
        self.capital += exit_value
        self.trade_log.append({
            "entry_time": position["entry_time"],
            "entry_price": position["entry_price"],
            "exit_time": timestamp,
            "exit_price": close,
            "quantity": position["quantity"],
            "cost_basis": position["cost_basis"],
            "exit_value": exit_value,
            "brokerage": brokerage_fee,
            "pnl": pnl,
            "capital": self.capital,
        })
        self.position = None
        logger.info("Exit at {ts}: qty {qty} @ {price}, pnl {pnl}",
                    ts=timestamp, qty=position["quantity"], price=close, pnl=round(pnl, 2))

    def get_trade_log(self) -> list:
        """Return the list of completed trades."""
        return self.trade_log

    def get_equity_curve(self) -> pd.DataFrame:
        """Return a DataFrame of capital after each completed trade."""
        if not self.trade_log:
            return pd.DataFrame(columns=["time", "capital"])
        return pd.DataFrame([
            {"time": trade["exit_time"], "capital": trade["capital"]}
            for trade in self.trade_log
        ])

    def get_running_capital(self) -> pd.Series:
        """Return capital value after each candle as a Series indexed by time."""
        cash = self.initial_capital
        position = None
        running = []

        for row in self.data.itertuples():
            close = row.close
            signal = row.signal

            if signal == 1 and position is None:
                quantity = math.floor(cash / close)
                if quantity > 0:
                    cost = quantity * close
                    cash -= cost + cost * self.brokerage
                    position = {"quantity": quantity, "cost_basis": cost}

            elif signal == -1 and position is not None:
                exit_value = position["quantity"] * close
                cash += exit_value - exit_value * self.brokerage
                position = None

            equity = cash + (position["quantity"] * close if position else 0)
            running.append(equity)

        return pd.Series(running, index=self.data.index, name="capital")