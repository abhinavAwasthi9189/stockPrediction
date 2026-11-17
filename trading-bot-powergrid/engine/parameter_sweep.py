"""Hyperparameter sweeps for trading strategies over train and validation data."""

from itertools import product

from loguru import logger

from metrics.analyzer import analyze_trades
from strategies.bollinger_breakout import BollingerBreakout
from strategies.zscore_reversion import ZScoreReversion
from strategies.vwap_reversion import VWAPReversion
from .backtester import Backtester

MIN_TRADES = 20
TOP_N = 10


def sweep_bollinger(train_df, val_df, capital, brokerage):
    strategy_cls = BollingerBreakout
    param_spec = ["bb_period", "bb_std"]
    combos = [(dict(zip(param_spec, vals)), *vals)
              for vals in product(range(10, 51, 5), [1.5, 2.0, 2.5, 3.0])]
    return _sweep(train_df, val_df, capital, brokerage, strategy_cls, combos, param_spec)


def sweep_zscore(train_df, val_df, capital, brokerage):
    strategy_cls = ZScoreReversion
    param_spec = ["lookback_period", "entry_z", "exit_z"]
    combos = [(dict(zip(param_spec, vals)), *vals)
              for vals in product(range(30, 101, 10), [-3.0, -2.5, -2.0, -1.5, -1.0], [-1.0, -0.5, 0.0])]
    return _sweep(train_df, val_df, capital, brokerage, strategy_cls, combos, param_spec)


def sweep_vwap(train_df, val_df, capital, brokerage):
    strategy_cls = VWAPReversion
    param_spec = ["lookback_period", "threshold_pct"]
    combos = [(dict(zip(param_spec, vals)), *vals)
              for vals in product(range(10, 51, 5), range(1, 11))]
    return _sweep(train_df, val_df, capital, brokerage, strategy_cls, combos, param_spec)


def _sweep(train_df, val_df, capital, brokerage, strategy_cls, combos, param_spec):
    """Run the shared tune-on-train, validate-on-test sweep and return results."""
    results = []
    for combo in combos:
        params = combo[0]
        train_metrics = _backtest_metrics(strategy_cls, params, train_df, capital, brokerage)
        if train_metrics is None:
            continue
        train_trades = train_metrics["total_trades"]
        train_pf = train_metrics["profit_factor"]
        if train_trades < MIN_TRADES or train_pf is None:
            logger.debug(
                "Skipping {strat} {params}: {trades} trades, pf {pf}",
                strat=strategy_cls.__name__,
                params=params,
                trades=train_trades,
                pf=train_pf,
            )
            continue
        results.append((params, train_metrics))

    logger.info(
        "Sweep for {strat}: {kept} combos passed train filter",
        strat=strategy_cls.__name__,
        kept=len(results),
    )

    results.sort(
        key=lambda r: r[1]["profit_factor"] if r[1]["profit_factor"] != float("inf") else float("inf"),
        reverse=True,
    )
    top_results = results[:TOP_N]

    output = []
    for params, train_metrics in top_results:
        val_metrics = _backtest_metrics(strategy_cls, params, val_df, capital, brokerage)
        if val_metrics is None:
            val_metrics = analyze_trades([], capital)
        entry = dict(zip(param_spec, params.values()))
        entry["train_pf"] = train_metrics["profit_factor"]
        entry["val_pf"] = val_metrics["profit_factor"]
        entry["train_win_rate"] = train_metrics["win_rate"]
        entry["val_win_rate"] = val_metrics["win_rate"]
        entry["train_trades"] = train_metrics["total_trades"]
        entry["val_trades"] = val_metrics["total_trades"]
        output.append(entry)
        logger.info(
            "Candidate {strat} {params}: train_pf {tpf} -> val_pf {vpf}",
            strat=strategy_cls.__name__,
            params=params,
            tpf=round(train_metrics["profit_factor"], 3),
            vpf=round(val_metrics["profit_factor"], 3),
        )
    return output


def _backtest_metrics(strategy_cls, params, df, capital, brokerage):
    """Compute trade metrics for one strategy and parameter combination."""
    try:
        strategy = strategy_cls(params)
        data = strategy.compute_signals(df)
        backtester = Backtester(strategy, data, capital, brokerage)
        backtester.run()
        return analyze_trades(backtester.get_trade_log(), capital)
    except Exception as exc:
        logger.warning("Backtest failed for {strat} {params}: {exc}",
                       strat=strategy_cls.__name__, params=params, exc=exc)
        return None


def print_sweep_results(results: list, strategy_name: str) -> None:
    """Print a formatted table of the top sweep results."""
    print(f"\n=== {strategy_name} Top {TOP_N} Results ===")
    if not results:
        print("No results to display.")
        return
    headers = list(results[0].keys())
    widths = [max(len(str(h)), max(len(str(r[h])) for r in results)) for h in headers]

    def fmt(value):
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(header_line)
    print("-" * len(header_line))
    for result in results:
        print("  ".join(fmt(result[h]).ljust(w) for h, w in zip(headers, widths)))
    print()