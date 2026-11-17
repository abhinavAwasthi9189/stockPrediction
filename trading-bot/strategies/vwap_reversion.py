"""VWAP Reversion strategy.

Buy when price drops below VWAP by threshold% (volume-weighted average acts as anchor).
Sell when price returns to VWAP.
"""

import pandas as pd

from .base import Strategy


class VWAPReversion(Strategy):
    def __init__(self, params: dict):
        super().__init__(params)
        self.lookback_period = params.get("lookback_period", 20)
        self.threshold_pct = params.get("threshold_pct", 3)

    def compute_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["vwap_num"] = (df["close"] * df["volume"]).rolling(self.lookback_period).sum()
        df["vwap_den"] = df["volume"].rolling(self.lookback_period).sum()
        df["vwap"] = df["vwap_num"] / df["vwap_den"]
        df["lower_bound"] = df["vwap"] * (1 - self.threshold_pct / 100)

        df["signal"] = 0
        in_position = False

        for i, row in df.iterrows():
            if pd.isna(row["vwap"]) or pd.isna(row["lower_bound"]):
                continue

            if not in_position:
                if row["close"] < row["lower_bound"]:
                    df.loc[i, "signal"] = 1
                    in_position = True
            else:
                if row["close"] >= row["vwap"]:
                    df.loc[i, "signal"] = -1
                    in_position = False

        return df