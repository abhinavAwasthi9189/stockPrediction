"""Data fetching and loading utilities."""

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from loguru import logger

COLUMNS = ["datetime", "open", "high", "low", "close", "volume"]


def fetch_daily(symbol, start_date=None, end_date=None):
    """Fetch daily OHLCV data from yfinance and return it as a DataFrame indexed by datetime."""
    if start_date is None:
        start_date = datetime.now() - timedelta(days=730)
    if end_date is None:
        end_date = datetime.now()
    try:
        raw = yf.download(
            symbol,
            start=start_date,
            end=end_date,
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
    except Exception as exc:
        logger.exception("Failed to download data for {symbol}: {exc}", symbol=symbol, exc=exc)
        return None
    if raw is None or raw.empty:
        logger.error("No data returned for {symbol}", symbol=symbol)
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw.columns = [str(col).lower() for col in raw.columns]
    raw = raw.reset_index()
    if "Date" in raw.columns:
        raw = raw.rename(columns={"Date": "datetime"})
    raw = raw[COLUMNS]
    raw["datetime"] = pd.to_datetime(raw["datetime"])
    raw = raw.set_index("datetime")
    logger.info(
        "Fetched {rows} daily rows for {symbol} from {start} to {end}",
        rows=len(raw),
        symbol=symbol,
        start=raw.index.min(),
        end=raw.index.max(),
    )
    return raw


def split_data(df, train_ratio=0.8):
    """Split a DataFrame by date into train and validation sets; return (train_df, val_df)."""
    if df is None or df.empty:
        logger.warning("Cannot split empty DataFrame")
        return None, None
    df = df.sort_index()
    split_idx = int(len(df) * train_ratio)
    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]
    if train_df.empty or val_df.empty:
        logger.warning("Split produced empty train or validation set")
        return None, None
    print(
        f"Train: {train_df.index.min()} to {train_df.index.max()} ({len(train_df)} rows)"
    )
    print(
        f"Validation: {val_df.index.min()} to {val_df.index.max()} ({len(val_df)} rows)"
    )
    logger.info("Split complete: {train_rows} train, {val_rows} validation rows",
                train_rows=len(train_df), val_rows=len(val_df))
    return train_df, val_df


def save_to_csv(df, path):
    """Save a DataFrame to a CSV file preserving the datetime index; return None on failure."""
    if df is None or df.empty:
        logger.warning("Nothing to save to {path}", path=path)
        return None
    try:
        df.to_csv(path)
    except Exception as exc:
        logger.exception("Failed to save CSV to {path}: {exc}", path=path, exc=exc)
        return None
    logger.info("Saved {rows} rows to {path}", rows=len(df), path=path)
    return df


def load_from_csv(path):
    """Load a CSV file into a DataFrame and restore the datetime index; return None on failure."""
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        logger.exception("Failed to load CSV from {path}: {exc}", path=path, exc=exc)
        return None
    if df is None or df.empty:
        logger.error("No data loaded from {path}", path=path)
        return None
    if "datetime" not in df.columns:
        logger.error("Missing 'datetime' column in {path}", path=path)
        return None
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime")
    logger.info("Loaded {rows} rows from {path}", rows=len(df), path=path)
    return df