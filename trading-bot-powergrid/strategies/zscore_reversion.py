"""Z-Score Mean Reversion strategy.

Buy when z-score drops below entry_z (statistically oversold).
Sell when z-score rises above exit_z (returned toward mean).
"""

import pandas as pd

from .base import Strategy


class ZScoreReversion(Strategy):
    def __init__(self, params: dict):
        super().__init__(params)
        self.lookback_period = params.get("lookback_period", 50)
        self.entry_z = params.get("entry_z", -2.0)
        self.exit_z = params.get("exit_z", -0.5)

    def compute_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        rolling = df["close"].rolling(window=self.lookback_period)
        df["mean"] = rolling.mean().shift(1)
        df["std"] = rolling.std(ddof=0).shift(1)
        df["zscore"] = (df["close"] - df["mean"]) / df["std"]

        df["signal"] = 0
        in_position = False

        for i, row in df.iterrows():
            z = row["zscore"]
            if pd.isna(z):
                continue

            if not in_position:
                if z < self.entry_z:
                    df.loc[i, "signal"] = 1
                    in_position = True
            else:
                if z > self.exit_z:
                    df.loc[i, "signal"] = -1
                    in_position = False

        return df