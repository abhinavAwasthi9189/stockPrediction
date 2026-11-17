"""Command-line interface for the algorithmic trading bot."""

import argparse
import os
import sys

from dotenv import load_dotenv
from loguru import logger

from config import (
    STOCK_SYMBOL, INITIAL_CAPITAL, BACKTEST_CAPITAL, BROKERAGE, TRAIN_SPLIT,
    BB_CONFIG, ZSCORE_CONFIG, VWAP_CONFIG,
)
from data.fetcher import fetch_daily, split_data, save_to_csv, load_from_csv
from engine.backtester import Backtester
from engine.paper_trader import PaperTrader
from engine.live_trader import LiveTrader
from engine.parameter_sweep import sweep_bollinger, sweep_zscore, sweep_vwap, print_sweep_results
from metrics.analyzer import analyze_trades, print_report, compare_strategies
from strategies.bollinger_breakout import BollingerBreakout
from strategies.zscore_reversion import ZScoreReversion
from strategies.vwap_reversion import VWAPReversion

STRATEGY_MAP = {
    "bollinger": BollingerBreakout,
    "zscore": ZScoreReversion,
    "vwap": VWAPReversion,
}

CONFIG_MAP = {
    "bollinger": BB_CONFIG,
    "zscore": ZSCORE_CONFIG,
    "vwap": VWAP_CONFIG,
}

SWEEP_MAP = {
    "bollinger": sweep_bollinger,
    "zscore": sweep_zscore,
    "vwap": sweep_vwap,
}


def cmd_fetch(args):
    os.makedirs("results", exist_ok=True)
    df = fetch_daily(STOCK_SYMBOL)
    if df is not None:
        save_to_csv(df, "results/stock_daily.csv")
    print("Done. Check results/ for logs.")


def cmd_backtest(args):
    os.makedirs("results", exist_ok=True)
    strategy_cls = STRATEGY_MAP[args.strategy]
    params = CONFIG_MAP[args.strategy]
    df = load_from_csv("results/stock_daily.csv")
    if df is None:
        logger.error("No data found. Run 'python main.py fetch' first.")
        return
    train_df, val_df = split_data(df, TRAIN_SPLIT)
    strategy = strategy_cls(params)
    data = strategy.compute_signals(train_df)
    backtester = Backtester(strategy, data, BACKTEST_CAPITAL, BROKERAGE)
    backtester.run()
    metrics = analyze_trades(backtester.get_trade_log(), BACKTEST_CAPITAL)
    print_report(metrics)
    print("Done. Check results/ for logs.")


def cmd_sweep(args):
    os.makedirs("results", exist_ok=True)
    sweep_fn = SWEEP_MAP[args.strategy]
    df = load_from_csv("results/stock_daily.csv")
    if df is None:
        logger.error("No data found. Run 'python main.py fetch' first.")
        return
    train_df, val_df = split_data(df, TRAIN_SPLIT)
    results = sweep_fn(train_df, val_df, BACKTEST_CAPITAL, BROKERAGE)
    print_sweep_results(results, args.strategy.upper())
    if results:
        import pandas as pd
        pd.DataFrame(results).to_csv(f"results/sweep_{args.strategy}.csv", index=False)
        logger.info("Saved sweep results to results/sweep_{name}.csv", name=args.strategy)
    print("Done. Check results/ for logs.")


def cmd_paper(args):
    os.makedirs("results", exist_ok=True)
    strategy = STRATEGY_MAP[args.strategy](CONFIG_MAP[args.strategy])
    trader = PaperTrader(strategy, INITIAL_CAPITAL, BROKERAGE)
    trader.run_loop()


def cmd_live(args):
    os.makedirs("results", exist_ok=True)
    load_dotenv()
    api_key = os.getenv("ZERODHA_API_KEY")
    access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
    if not api_key or not access_token:
        logger.error("Missing ZERODHA_API_KEY or ZERODHA_ACCESS_TOKEN in .env")
        print("ERROR: Set ZERODHA_API_KEY and ZERODHA_ACCESS_TOKEN in .env")
        sys.exit(1)
    strategy = STRATEGY_MAP[args.strategy](CONFIG_MAP[args.strategy])
    trader = LiveTrader(strategy, INITIAL_CAPITAL, BROKERAGE, api_key, access_token)
    trader.run_paper_first() if args.paper_first else trader.run_loop()


def cmd_compare(args):
    os.makedirs("results", exist_ok=True)
    df = load_from_csv("results/stock_daily.csv")
    if df is None:
        logger.error("No data found. Run 'python main.py fetch' first.")
        return
    train_df, val_df = split_data(df, TRAIN_SPLIT)
    all_metrics = {}
    for name, cls in STRATEGY_MAP.items():
        params = CONFIG_MAP[name]
        strategy = cls(params)
        data = strategy.compute_signals(train_df)
        backtester = Backtester(strategy, data, BACKTEST_CAPITAL, BROKERAGE)
        backtester.run()
        metrics = analyze_trades(backtester.get_trade_log(), BACKTEST_CAPITAL)
        all_metrics[name.upper()] = metrics
    compare_strategies(all_metrics)
    print("Done. Check results/ for logs.")


def main():
    parser = argparse.ArgumentParser(description="Algorithmic Trading Bot CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    strategies = list(STRATEGY_MAP.keys())

    fetch_parser = subparsers.add_parser("fetch", help="Fetch historical data from yfinance")
    fetch_parser.set_defaults(func=cmd_fetch)

    backtest_parser = subparsers.add_parser("backtest", help="Run a strategy backtest")
    backtest_parser.add_argument("--strategy", required=True, choices=strategies)
    backtest_parser.set_defaults(func=cmd_backtest)

    sweep_parser = subparsers.add_parser("sweep", help="Run a hyperparameter sweep")
    sweep_parser.add_argument("--strategy", required=True, choices=list(SWEEP_MAP.keys()))
    sweep_parser.set_defaults(func=cmd_sweep)

    compare_parser = subparsers.add_parser("compare", help="Compare all strategies side-by-side")
    compare_parser.set_defaults(func=cmd_compare)

    paper_parser = subparsers.add_parser("paper", help="Run paper trader (simulated, yfinance quotes)")
    paper_parser.add_argument("--strategy", default="bollinger", choices=strategies)
    paper_parser.set_defaults(func=cmd_paper)

    live_parser = subparsers.add_parser("live", help="Run live trader via Kite Connect")
    live_parser.add_argument("--strategy", default="bollinger", choices=strategies)
    live_parser.add_argument("--paper-first", action="store_true",
                             help="Run in paper mode for 2 weeks before switching to live")
    live_parser.set_defaults(func=cmd_live)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()