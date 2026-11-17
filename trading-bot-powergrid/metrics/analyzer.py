"""Trade performance metrics and reporting."""

import math

import pandas as pd


def analyze_trades(trade_log: list, initial_capital: float) -> dict:
    """Compute performance metrics from a list of completed trades."""
    if not trade_log:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "profit_factor": 0.0,
            "total_pnl": 0.0,
            "final_capital": initial_capital,
            "return_pct": 0.0,
            "sharpe_ratio": 0.0,
            "avg_holding_period": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "expectancy": 0.0,
            "max_drawdown": 0.0,
        }

    pnls = [trade["pnl"] for trade in trade_log]
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p <= 0]

    total_pnl = sum(pnls)
    gross_profit = sum(winners)
    gross_loss = abs(sum(losers))
    profit_factor = float("inf") if gross_loss == 0 else gross_profit / gross_loss

    trade_returns = [p / initial_capital for p in pnls]
    mean_ret = sum(trade_returns) / len(trade_returns)
    std_ret = _std(trade_returns)
    sharpe_ratio = 0 if std_ret == 0 else (mean_ret / std_ret) * math.sqrt(252)

    holding_periods = []
    for trade in trade_log:
        entry = trade["entry_time"]
        exit_time = trade["exit_time"]
        if hasattr(entry, "tzinfo") or hasattr(exit_time, "tzinfo"):
            holding = (exit_time - entry).total_seconds() / 60
        else:
            holding = 0.0
        holding_periods.append(holding)
    avg_holding = sum(holding_periods) / len(holding_periods)

    final_capital = initial_capital + total_pnl
    return_pct = (total_pnl / initial_capital) * 100 if initial_capital else 0.0

    return {
        "total_trades": len(trade_log),
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "win_rate": (len(winners) / len(trade_log)) * 100,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "total_pnl": total_pnl,
        "final_capital": final_capital,
        "return_pct": return_pct,
        "sharpe_ratio": sharpe_ratio,
        "avg_holding_period": avg_holding,
        "avg_win": _avg(winners),
        "avg_loss": _avg(losers),
        "expectancy": total_pnl / len(trade_log),
        "max_drawdown": 0.0,
    }


def calculate_max_drawdown(equity_series: pd.Series) -> float:
    """Return the maximum drawdown of an equity series as a percentage."""
    if equity_series is None or equity_series.empty:
        return 0.0
    running_max = equity_series.cummax()
    drawdown = (running_max - equity_series) / running_max
    return float(drawdown.max() * 100)


def print_report(metrics: dict) -> None:
    """Print a formatted performance report for a strategy."""
    line = "=" * 50
    print(line)
    print("========== Strategy Performance Report ==========")
    print(f"Total Trades:          {metrics['total_trades']}")
    print(f"Win Rate:              {metrics['win_rate']:.1f}%")
    print(f"Profit Factor:         {metrics['profit_factor']:.2f}")
    print(f"Total P&L:             ₹ {metrics['total_pnl']:.2f}")
    print(f"Return:                {metrics['return_pct']:.2f}%")
    print(f"Max Drawdown:          {metrics['max_drawdown']:.2f}%")
    print(f"Sharpe Ratio:          {metrics['sharpe_ratio']:.2f}")
    print(f"Avg Holding:           {metrics['avg_holding_period']:.1f} min")
    print(f"Expectancy/Trade:      ₹ {metrics['expectancy']:.2f}")
    print(line)


def compare_strategies(results: dict) -> None:
    """Print a side-by-side comparison table of strategy metrics."""
    headers = ["Strategy", "Win%", "PF", "Total P&L", "Sharpe", "MaxDD%"]
    widths = [14, 7, 7, 12, 8, 8]

    def row(values):
        return "  ".join(str(v).rjust(w) for v, w in zip(values, widths))

    print(row(headers))
    print("-" * sum(widths) + "--" * (len(widths) - 1))
    for name, m in results.items():
        print(row([
            name[:14],
            f"{m['win_rate']:.1f}",
            f"{m['profit_factor']:.2f}",
            f"{m['total_pnl']:.2f}",
            f"{m['sharpe_ratio']:.2f}",
            f"{m['max_drawdown']:.2f}",
        ]))


def _std(values: list) -> float:
    """Return the sample standard deviation of a list; 0 for single or empty lists."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))


def _avg(values: list) -> float:
    """Return the average of a list; 0 for empty lists."""
    return sum(values) / len(values) if values else 0.0