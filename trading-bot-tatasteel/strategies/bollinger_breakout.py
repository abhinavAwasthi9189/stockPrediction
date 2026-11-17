"""Bollinger Band breakout strategy."""

import pandas as pd
import pandas_ta as ta

from .base import Strategy


class BollingerBreakout(Strategy):
    """Trade Bollinger Band breaks with a state machine for entry and exit signals."""

    def __init__(self, params: dict):
        """Initialize the strategy with period and std_dev parameters."""
        super().__init__(params)
        self.period = params.get("period", 20)
        self.std_dev = params.get("std_dev", 2)

    def compute_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add a signal column (1 long, -1 short, 0 flat) and return the DataFrame."""
        df = df.copy()
        bb = ta.bbands(
            df["close"],
            length=self.period,
            lower_std=self.std_dev,
            upper_std=self.std_dev,
        )
        df["bb_lower"] = bb[bb.columns[bb.columns.str.startswith("BBL_")][0]]
        df["bb_middle"] = bb[bb.columns[bb.columns.str.startswith("BBM_")][0]]
        df["bb_upper"] = bb[bb.columns[bb.columns.str.startswith("BBU_")][0]]

        df["signal"] = 0
        state = "none"

        for i, row in df.iterrows():
            close = row["close"]
            bb_lower = row["bb_lower"]
            bb_middle = row["bb_middle"]
            bb_upper = row["bb_upper"]
            if pd.isna(bb_lower) or pd.isna(bb_middle) or pd.isna(bb_upper):
                continue

            signal = 0
            if state == "none" and close <= bb_lower:
                signal = 1
                state = "long"
            elif state == "long" and close >= bb_middle:
                signal = -1
                state = "none"
            elif state == "none" and close >= bb_upper:
                signal = -1
                state = "short"
            elif state == "short" and close <= bb_middle:
                signal = 1
                state = "none"

            df.loc[i, "signal"] = signal

        return df