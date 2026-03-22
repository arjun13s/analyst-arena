from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from analyst_arena.agents import build_default_agents
from analyst_arena.engine import TournamentEngine

from run_tournament import (
    DEFAULT_AGENT_NAMES,
    DEFAULT_LEADERBOARD_PATH,
    DEFAULT_RESULTS_PATH,
    format_leaderboard,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Analyst Arena round robin backtests.")
    parser.add_argument("--agents", nargs="*", default=DEFAULT_AGENT_NAMES)
    parser.add_argument("--tickers", nargs="*", default=["NVDA", "AAPL", "GOOGL"])
    parser.add_argument("--months", type=int, default=3)
    parser.add_argument("--starting-cash", type=float, default=100000.0)
    parser.add_argument("--results-path", default=str(DEFAULT_RESULTS_PATH))
    parser.add_argument("--leaderboard-path", default=str(DEFAULT_LEADERBOARD_PATH))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    registry = build_default_agents()
    selected_agents = [registry[name] for name in args.agents]
    tournament = TournamentEngine(
        agents=selected_agents,
        results_path=Path(args.results_path),
        leaderboard_path=Path(args.leaderboard_path),
    )
    tournament.run_round_robin(
        tickers=args.tickers,
        months=args.months,
        starting_cash=args.starting_cash,
    )
    print(format_leaderboard(tournament.leaderboard()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
