"""Abstract base class for trading strategies."""

from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """Base class all strategies must subclass."""

    def __init__(self, params: dict):
        """Initialize the strategy with its parameters."""
        self.params = params

    @abstractmethod
    def compute_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add a signal column to the DataFrame and return it."""
        pass

    def get_name(self) -> str:
        """Return the strategy class name."""
        return self.__class__.__name__

    def get_params(self) -> dict:
        """Return the strategy parameters."""
        return self.params