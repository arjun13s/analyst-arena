from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Sequence

from analyst_arena.agents import AnthropicAgent, Agent, HUDModelAgent, OpenAIAgent
from analyst_arena.engine import MatchEngine, Tournament
from analyst_arena.storage import load_results, save_results


def build_agents() -> dict[str, Agent]:
    return {
        "gpt4o": OpenAIAgent(name="gpt4o", model="gpt-4o"),
        "claude": AnthropicAgent(name="claude", model="claude-3-7-sonnet-latest"),
        "hud_model": HUDModelAgent(name="hud_model", model="hud-placeholder"),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Analyst Arena tournaments.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_all = subparsers.add_parser("run-all", help="Run a full round robin tournament.")
    run_all.add_argument("--scenario", default="analyst_debate")
    run_all.add_argument("--results-path", default="results.json")

    single = subparsers.add_parser("single-match", help="Run a single head-to-head match.")
    single.add_argument("agent_a")
    single.add_argument("agent_b")
    single.add_argument("--scenario", default="analyst_debate")
    single.add_argument("--results-path", default="results.json")

    board = subparsers.add_parser("leaderboard", help="Print leaderboard from saved results.")
    board.add_argument("--results-path", default="results.json")

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    agents = build_agents()

    if args.command == "run-all":
        tournament = Tournament(agents=list(agents.values()))
        tournament.run_round_robin(scenario=args.scenario)
        save_results(tournament.results, args.results_path)
        print(format_leaderboard(tournament.leaderboard()))
        return 0

    if args.command == "single-match":
        match_engine = MatchEngine()
        result = match_engine.run_match(
            agent_a=agents[args.agent_a],
            agent_b=agents[args.agent_b],
            scenario=args.scenario,
        )
        existing = load_results(args.results_path)
        existing.append(result)
        save_results(existing, args.results_path)
        print(json.dumps(asdict(result), indent=2))
        return 0

    if args.command == "leaderboard":
        tournament = Tournament(agents=list(agents.values()))
        tournament.results = load_results(args.results_path)
        print(format_leaderboard(tournament.leaderboard()))
        return 0

    return 1


def format_leaderboard(rows: list[dict[str, str | int | float]]) -> str:
    header = "Agent        Wins   Losses   Avg Score"
    lines = [header, "-" * len(header)]
    for row in rows:
        lines.append(
            f"{str(row['agent']):<12} {int(row['wins']):<6} {int(row['losses']):<8} {float(row['avg_score']):.1f}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
