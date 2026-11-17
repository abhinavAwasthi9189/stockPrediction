# Algorithmic Trading Bot

A Python algorithmic trading bot for the Indian stock market using Zerodha Kite Connect. Trades TATASTEEL on 1-minute candles with ₹500 capital, with backtesting, parameter sweeping, strategy comparison, paper trading, and live trading via Kite.

## Features

- **3 strategies**: EMA crossover, RSI mean reversion, Bollinger Band breakout
- **Backtesting engine**: trade simulation with brokerage fees, equity curve, running capital
- **Performance metrics**: win rate, profit factor, Sharpe ratio, drawdown, expectancy
- **Parameter sweeps**: tune on train split, validate on holdout, top-10 ranking
- **Paper trading**: simulated live trading on 1-minute candles via yfinance
- **Live trading**: real orders via Kite Connect with built-in safety limits
- **Logging**: loguru-based, no comments or emoji in source

## Project Structure

```
trading-bot/
├── config.py                  # All configuration constants
├── main.py                    # CLI entry point (argparse)
├── requirements.txt
├── .env.example               # Template for Zerodha credentials
├── INSTRUCTIONS.md            # Quick start guide
├── data/
│   └── fetcher.py             # yfinance download, train/val split, CSV I/O
├── strategies/
│   ├── base.py                # Strategy ABC
│   ├── ema_crossover.py       # EMA fast/slow cross signals
│   ├── rsi_reversion.py       # RSI oversold/overbought mean reversion
│   └── bollinger_breakout.py  # Bollinger band breakout
├── engine/
│   ├── backtester.py          # Historical trade simulation
│   ├── parameter_sweep.py     # Hyperparameter sweeps (ema/rsi/bollinger)
│   ├── paper_trader.py        # Simulated live trading on 1m candles
│   └── live_trader.py         # Kite Connect live orders + safety limits
└── metrics/
    └── analyzer.py            # Performance metrics and reports
```

## Install

```bash
pip install -r requirements.txt
```

## Configuration

All settings live in `config.py`:

| Setting | Value | Purpose |
| --- | --- | --- |
| `STOCK_SYMBOL` | `TATASTEEL.NS` | yfinance symbol (Kite symbol derived as `TATASTEEL`) |
| `INITIAL_CAPITAL` | `500` | Paper/live trading capital (₹) |
| `BACKTEST_CAPITAL` | `500000` | Backtest notional capital (₹) — ₹500 cannot buy 1 RELIANCE share |
| `BROKERAGE` | `0.0003` | 0.03% per order |
| `TIMEFRAME` | `1m` | Candle interval |
| `TRAIN_SPLIT` | `0.8` | Backtest train/validation split |
| `EMA_CONFIG` | `{fast: 20, slow: 50}` | EMA strategy defaults |
| `RSI_CONFIG` | `{period: 14, oversold: 30, overbought: 70}` | RSI strategy defaults |
| `BB_CONFIG` | `{period: 20, std_dev: 2}` | Bollinger strategy defaults |

## Usage

### 1. Fetch data

Downloads ~2 years of daily TATASTEEL data from yfinance and saves to `results/stock_daily.csv`.

```bash
python main.py fetch
```

### 2. Backtest

Run one strategy with default config params on the train split:

```bash
python main.py backtest --strategy ema       # or rsi, bollinger
```

### 3. Parameter sweep

Sweeps each strategy's hyperparameters (e.g. EMA fast 5–50, slow 20–200), keeps combinations with 20+ train trades, ranks top 10 by profit factor, validates them on the holdout split, saves full results to `results/sweep_{strategy}.csv`:

```bash
python main.py sweep --strategy ema          # or rsi, bollinger
```

### 4. Compare strategies

Backtests all three strategies with default params side by side:

```bash
python main.py compare
```

### 5. Paper trading

Simulated live trading on 1-minute candles (yfinance quotes), Mon–Fri 9:15–15:30 IST, logs trades to `results/paper_trades_{date}.csv`. Press Ctrl+C to save and exit.

```bash
python main.py paper                         # default: ema
python main.py paper --strategy rsi
```

### 6. Live trading (Zerodha Kite Connect)

> **Never go live without 2+ weeks of profitable paper trading first.**

```bash
cp .env.example .env
# edit .env with your real credentials
python main.py live                          # default: ema, live orders
python main.py live --paper-first            # 2 weeks paper mode first
python main.py live --strategy bollinger
```

Requires `ZERODHA_API_KEY` and `ZERODHA_ACCESS_TOKEN` in the environment (auto-loaded from `.env`). The access token expires daily at 6 AM IST — regenerate each morning.

## Live Trading Safety Limits

- Stops for the day after **3 consecutive losses**
- Stops for the day after **5% daily loss** against start-of-day capital
- No trading in the first 15 min (9:15–9:30) or last 15 min (3:15–3:30) of market hours
- `--paper-first` verifies the strategy in paper mode for 2 weeks before placing real orders

## Notes

- NSE allows only whole-share trading; ₹500 still cannot buy a large-cap share like RELIANCE (~₹1,320), hence the separate `BACKTEST_CAPITAL` for daily backtests. TATASTEEL (~₹150) is within smaller capital.
- yfinance provides only ~7 days of 1-minute data — backtests run on daily data; 1-minute data is used only by paper/live traders for real-time signals.
- CSV trade logs land in `results/` (auto-created): backtest/sweep outputs plus per-day paper/live trade logs.

## Disclaimer

This is educational software for algorithm experimentation. Trading involves real financial risk; at ₹500 capital, treat any loss as the cost of learning. Not financial advice.