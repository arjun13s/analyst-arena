from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Sequence

from analyst_arena.agents import Agent, build_default_agents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
from analyst_arena.engine import MatchEngine, TournamentEngine
from analyst_arena.models import AgentBacktestResult, MatchResult
from analyst_arena.scoring.leaderboard import build_leaderboard
from analyst_arena.storage.leaderboard import load_leaderboard, save_leaderboard
from analyst_arena.storage.results import load_results


DEFAULT_RESULTS_PATH = Path("match_results.json")
DEFAULT_LEADERBOARD_PATH = Path("leaderboard.json")
DEFAULT_TICKERS = ["NVDA", "AAPL", "GOOGL"]
DEFAULT_AGENT_NAMES = ["hud_model", "gpt4o"]


def build_agents() -> dict[str, Agent]:
    return build_default_agents()


def _resolve_agents(registry: dict[str, Agent], names: Sequence[str]) -> list[Agent]:
    missing = [name for name in names if name not in registry]
    if missing:
        raise KeyError(f"Unknown agent(s): {', '.join(missing)}")
    return [registry[name] for name in names]


AGENT_ACCENT_COLORS: dict[str, str] = {
    "hud_model": "#00E5CC",
    "gpt4o": "#10A37F",
    "claude": "#D97706",
    "grok": "#1D9BF0",
}

DEFAULT_ACCENT = "#8888AA"


def _agent_result_payload(result: AgentBacktestResult, winner_name: str) -> dict[str, Any]:
    return {
        "name": result.agent.name,
        "display_name": result.agent.display_name or result.agent.name,
        "provider": result.agent.provider,
        "model_id": result.agent.model_id,
        "accent_color": AGENT_ACCENT_COLORS.get(result.agent.name, DEFAULT_ACCENT),
        "initial_cash": round(result.initial_cash, 2),
        "final_portfolio_value": round(result.final_portfolio_value, 2),
        "total_return_pct": round(result.total_return_pct, 3),
        "max_drawdown_pct": round(result.max_drawdown_pct, 3),
        "trade_count": result.trade_count,
        "win_rate": round(result.win_rate, 3),
        "elapsed_seconds": result.elapsed_seconds,
        "winner": result.agent.name == winner_name,
        "portfolio_state": result.portfolio_state.to_dict(),
        "equity_curve": [point.to_dict() for point in result.equity_curve],
        "trade_log": [trade.to_dict() for trade in result.trade_log],
        "decisions": [decision.to_dict() for decision in result.decisions],
        "summaries": list(result.summaries),
        "metadata": dict(result.metadata),
    }


def flatten_match_result(match_result: MatchResult) -> dict[str, Any]:
    agent_a = _agent_result_payload(match_result.agent_a_result, match_result.winner_agent_name)
    agent_b = _agent_result_payload(match_result.agent_b_result, match_result.winner_agent_name)
    loser_name = (
        match_result.agent_b_result.agent.name
        if match_result.winner_agent_name == match_result.agent_a_result.agent.name
        else match_result.agent_a_result.agent.name
    )
    winner_display = (
        match_result.agent_a_result.agent.display_name
        if match_result.winner_agent_name == match_result.agent_a_result.agent.name
        else match_result.agent_b_result.agent.display_name
    ) or match_result.winner_agent_name
    loser_display = (
        match_result.agent_b_result.agent.display_name
        if loser_name == match_result.agent_b_result.agent.name
        else match_result.agent_a_result.agent.display_name
    ) or loser_name

    curve_a = agent_a["equity_curve"]
    curve_b = agent_b["equity_curve"]
    num_frames = max(len(curve_a), len(curve_b))
    initial = match_result.config.starting_cash

    simulation_frames: list[dict[str, Any]] = []
    for i in range(num_frames):
        pt_a = curve_a[i] if i < len(curve_a) else curve_a[-1] if curve_a else {}
        pt_b = curve_b[i] if i < len(curve_b) else curve_b[-1] if curve_b else {}
        val_a = float(pt_a.get("total_equity", initial))
        val_b = float(pt_b.get("total_equity", initial))
        simulation_frames.append({
            "frame": i,
            "date": pt_a.get("date") or pt_b.get("date", ""),
            "agent_a_equity": round(val_a, 2),
            "agent_b_equity": round(val_b, 2),
            "agent_a_return_pct": round(((val_a / initial) - 1.0) * 100.0, 3) if initial else 0.0,
            "agent_b_return_pct": round(((val_b / initial) - 1.0) * 100.0, 3) if initial else 0.0,
        })

    def _build_trades_timeline(trade_log: list[dict[str, Any]], agent_label: str) -> list[dict[str, Any]]:
        entries = []
        for trade in trade_log:
            action = trade.get("action", "HOLD")
            if action == "HOLD":
                continue
            entries.append({
                "agent": agent_label,
                "date": trade.get("date", ""),
                "action": action,
                "shares": trade.get("shares", 0),
                "price": trade.get("execution_price", 0),
                "notional": trade.get("notional", 0),
                "rationale": trade.get("rationale", ""),
            })
        return entries

    trades_a = _build_trades_timeline(agent_a["trade_log"], agent_a["display_name"])
    trades_b = _build_trades_timeline(agent_b["trade_log"], agent_b["display_name"])
    trades_timeline = sorted(trades_a + trades_b, key=lambda t: t["date"])

    return {
        "match_id": match_result.match_id,
        "ticker": match_result.ticker,
        "start_date": match_result.start_date.isoformat(),
        "end_date": match_result.end_date.isoformat(),
        "initial_cash": round(initial, 2),
        "total_frames": num_frames,
        "agent_a": agent_a,
        "agent_b": agent_b,
        "simulation_frames": simulation_frames,
        "trades_timeline": trades_timeline,
        "winner": match_result.winner_agent_name,
        "loser": loser_name,
        "winner_display_name": winner_display,
        "loser_display_name": loser_display,
        "winner_final_value": round(match_result.winner_final_value, 2),
        "loser_final_value": round(match_result.loser_final_value, 2),
        "return_diff_pct": round(match_result.return_diff_pct, 3),
        "trophy": match_result.trophy,
        "reasoning": match_result.winner_explanation,
        "config": match_result.config.to_dict(),
        "raw": match_result.to_dict(),
    }


def run_match(
    agent_a_name: str,
    agent_b_name: str,
    ticker: str = "NVDA",
    *,
    months: int = 1,
    starting_cash: float = 100000.0,
    results_path: str | Path = DEFAULT_RESULTS_PATH,
    leaderboard_path: str | Path = DEFAULT_LEADERBOARD_PATH,
) -> dict[str, Any]:
    registry = build_agents()
    engine = MatchEngine(
        results_path=results_path,
        leaderboard_path=leaderboard_path,
        starting_cash=starting_cash,
    )
    result = engine.run_match(
        [registry[agent_a_name], registry[agent_b_name]],
        ticker=ticker,
        months=months,
        starting_cash=starting_cash,
    )
    return flatten_match_result(result)


def get_leaderboard(
    *,
    results_path: str | Path = DEFAULT_RESULTS_PATH,
    leaderboard_path: str | Path = DEFAULT_LEADERBOARD_PATH,
) -> list[dict[str, Any]]:
    entries = load_leaderboard(leaderboard_path)
    if entries:
        return [entry.to_dict() for entry in entries]

    results = load_results(results_path)
    if not results:
        return []

    agent_names = sorted({name for result in results for name in result.agent_names})
    leaderboard = build_leaderboard(results, agent_names)
    save_leaderboard(leaderboard, leaderboard_path)
    return [entry.to_dict() for entry in leaderboard]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Analyst Arena backtest tournaments.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_all = subparsers.add_parser("run-all", help="Run a full round robin tournament.")
    run_all.add_argument("--agents", nargs="*", default=DEFAULT_AGENT_NAMES)
    run_all.add_argument("--tickers", nargs="*", default=DEFAULT_TICKERS)
    run_all.add_argument("--months", type=int, default=1)
    run_all.add_argument("--starting-cash", type=float, default=100000.0)
    run_all.add_argument("--results-path", default=str(DEFAULT_RESULTS_PATH))
    run_all.add_argument("--leaderboard-path", default=str(DEFAULT_LEADERBOARD_PATH))

    single = subparsers.add_parser("single-match", help="Run a single head-to-head backtest.")
    single.add_argument("agent_a")
    single.add_argument("agent_b")
    single.add_argument("--ticker", default="NVDA")
    single.add_argument("--months", type=int, default=1)
    single.add_argument("--starting-cash", type=float, default=100000.0)
    single.add_argument("--results-path", default=str(DEFAULT_RESULTS_PATH))
    single.add_argument("--leaderboard-path", default=str(DEFAULT_LEADERBOARD_PATH))

    board = subparsers.add_parser("leaderboard", help="Print leaderboard from saved results.")
    board.add_argument("--results-path", default=str(DEFAULT_RESULTS_PATH))
    board.add_argument("--leaderboard-path", default=str(DEFAULT_LEADERBOARD_PATH))

    return parser.parse_args(argv)


def format_leaderboard(rows: list[dict[str, Any]]) -> str:
    header = (
        f"{'Agent':<14} {'Wins':>5} {'Losses':>7} {'Avg Final':>12} "
        f"{'Avg Return%':>12} {'Win Rate':>9}"
    )
    lines = [header, "-" * len(header)]
    for row in rows:
        lines.append(
            f"{str(row.get('agent_name', row.get('agent', ''))):<14} "
            f"{int(row.get('wins', 0)):>5} {int(row.get('losses', 0)):>7} "
            f"{float(row.get('avg_final_value', 0.0)):>12.2f} "
            f"{float(row.get('avg_return_pct', 0.0)):>12.3f} "
            f"{float(row.get('win_rate', 0.0)):>8.1%}"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    registry = build_agents()

    if args.command == "run-all":
        selected_agents = _resolve_agents(registry, args.agents)
        engine = TournamentEngine(
            agents=selected_agents,
            results_path=args.results_path,
            leaderboard_path=args.leaderboard_path,
        )
        results = engine.run_round_robin(
            tickers=args.tickers,
            months=args.months,
            starting_cash=args.starting_cash,
        )
        print(f"Completed {len(results)} matches.")
        print(format_leaderboard(engine.leaderboard()))
        return 0

    if args.command == "single-match":
        result = run_match(
            args.agent_a,
            args.agent_b,
            ticker=args.ticker,
            months=args.months,
            starting_cash=args.starting_cash,
            results_path=args.results_path,
            leaderboard_path=args.leaderboard_path,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "leaderboard":
        rows = get_leaderboard(
            results_path=args.results_path,
            leaderboard_path=args.leaderboard_path,
        )
        print(format_leaderboard(rows))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
