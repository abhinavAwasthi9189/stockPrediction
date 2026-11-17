"""Unified CLI for the multi-bot trading umbrella.

Supervises every bot, checks which one has an actionable trade right now,
and executes the single best opportunity on a shared position.
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from env.config import BOT_DIRS
from env.supervisor import Supervisor


def cmd_fetch(args):
    from data.fetcher import fetch_daily, save_to_csv

    supervisor = Supervisor(mode="paper")
    for bot in supervisor.bots:
        df = fetch_daily(bot["symbol"])
        if df is not None:
            path = os.path.join(bot["path"], "results", "stock_daily.csv")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            save_to_csv(df, path)
    print("Done. Daily data refreshed for all bots.")


def cmd_check(args):
    supervisor = Supervisor(mode="paper")
    opportunities = supervisor.scan()
    if not opportunities:
        print("No actionable signals right now across any bot.")
        return
    for opp in opportunities:
        side = "BUY" if opp["signal"] == 1 else "SELL"
        print(f"[{opp['timestamp']}] {side} | {opp['bot']:>24} | "
              f"{opp['strategy']:<8} | {opp['symbol']:<14} @ {opp['close']:.2f}")


def cmd_paper(args):
    os.makedirs("results", exist_ok=True)
    Supervisor(mode="paper").run_loop()


def cmd_simulate(args):
    Supervisor(mode="paper").simulate(days=args.days)


def cmd_simulate_1m(args):
    Supervisor(mode="paper").simulate_intraday(day=args.date)


def cmd_live(args):
    os.makedirs("results", exist_ok=True)
    load_dotenv()
    api_key = os.getenv("ZERODHA_API_KEY")
    access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
    if not api_key or not access_token:
        print("ERROR: Set ZERODHA_API_KEY and ZERODHA_ACCESS_TOKEN in .env")
        sys.exit(1)
    Supervisor(mode="live", api_key=api_key, access_token=access_token).run_loop()


def main():
    parser = argparse.ArgumentParser(
        description="Multi-bot trading umbrella: runs all bots and trades the best signal"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser(
        "fetch", help="Fetch recent daily data for every bot into each bot's results dir")
    fetch_parser.set_defaults(func=cmd_fetch)

    check_parser = subparsers.add_parser(
        "check", help="Scan every bot for an actionable trade right now")
    check_parser.set_defaults(func=cmd_check)

    paper_parser = subparsers.add_parser(
        "paper", help="Run the supervised paper trading loop over all bots")
    paper_parser.set_defaults(func=cmd_paper)

    simulate_parser = subparsers.add_parser(
        "simulate", help="Replay the supervisor across all bots over the last N days of daily data")
    simulate_parser.add_argument("--days", type=int, default=90, help="Days of history (default 90)")
    simulate_parser.set_defaults(func=cmd_simulate)

    simulate_1m_parser = subparsers.add_parser(
        "simulate-1m", help="Replay the supervisor on 1-minute bars for one day shared by all bots")
    simulate_1m_parser.add_argument("--date", default=None,
                                    help="YYYY-MM-DD; defaults to the most recent shared day")
    simulate_1m_parser.set_defaults(func=cmd_simulate_1m)

    live_parser = subparsers.add_parser(
        "live", help="Run the supervised live trading loop over all bots via Kite Connect")
    live_parser.set_defaults(func=cmd_live)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()