from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from run_tournament import DEFAULT_LEADERBOARD_PATH, DEFAULT_RESULTS_PATH, run_match


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a single Analyst Arena backtest showdown.")
    parser.add_argument("agent_a")
    parser.add_argument("agent_b")
    parser.add_argument("--ticker", default="NVDA")
    parser.add_argument("--months", type=int, default=3)
    parser.add_argument("--starting-cash", type=float, default=100000.0)
    parser.add_argument("--results-path", default=str(DEFAULT_RESULTS_PATH))
    parser.add_argument("--leaderboard-path", default=str(DEFAULT_LEADERBOARD_PATH))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_match(
        args.agent_a,
        args.agent_b,
        ticker=args.ticker,
        months=args.months,
        starting_cash=args.starting_cash,
        results_path=Path(args.results_path),
        leaderboard_path=Path(args.leaderboard_path),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
