# Algorithmic Trading Bot — Instructions

## Install

```bash
pip install -r requirements.txt
```

## Get API Keys

1. Sign up at https://developers.kite.trade
2. Create an app to get your API key
3. Complete the login flow to generate an access token
4. Copy `.env.example` to `.env` and fill in your credentials
5. The access token expires daily at 6 AM — regenerate each morning via the login flow

## Commands

| Command                                              | Description                              |
| ---------------------------------------------------- | ---------------------------------------- |
| `python main.py fetch`                               | Download historical data from yfinance   |
| `python main.py backtest --strategy ema`             | Backtest a strategy (ema/rsi/bollinger)  |
| `python main.py sweep --strategy ema`                | Hyperparameter sweep for a strategy      |
| `python main.py compare`                             | Compare all strategies side-by-side      |
| `python main.py paper`                               | Run paper trader (simulated, uses yfinance quotes) |
| `python main.py live`                                | Run live trader (real orders via Kite)   |

## Safety

- **Never commit `.env`.** It contains your API credentials.
- Only go live after **2+ weeks of profitable paper trading**.
- At ₹500 capital you can afford to lose it — **do not add more funds** until the strategy is proven over a longer period.
- The live trader includes automatic safeguards: stops after 3 consecutive losses or 5% daily drawdown.