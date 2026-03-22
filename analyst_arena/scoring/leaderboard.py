from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from analyst_arena.models import LeaderboardEntry, MatchResult


def build_leaderboard(results: list[MatchResult], agent_names: list[str] | None = None) -> list[LeaderboardEntry]:
    entries: dict[str, LeaderboardEntry] = {
        name: LeaderboardEntry(agent_name=name) for name in (agent_names or [])
    }
    totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"final_value_sum": 0.0, "return_sum": 0.0, "drawdown_sum": 0.0, "matches": 0.0}
    )

    for result in results:
        for agent_result in (result.agent_a_result, result.agent_b_result):
            agent_name = agent_result.agent.name
            entries.setdefault(agent_name, LeaderboardEntry(agent_name=agent_name))
            entry = entries[agent_name]
            entry.matches_played += 1
            if result.winner_agent_name == agent_name:
                entry.wins += 1
            elif result.winner_agent_name:
                entry.losses += 1
            else:
                entry.draws += 1

            totals[agent_name]["matches"] += 1
            totals[agent_name]["final_value_sum"] += float(agent_result.final_portfolio_value)
            totals[agent_name]["return_sum"] += float(agent_result.total_return_pct)
            totals[agent_name]["drawdown_sum"] += float(agent_result.max_drawdown_pct)

    now = datetime.now(timezone.utc)
    for agent_name, entry in entries.items():
        stats = totals.get(agent_name)
        matches = stats["matches"] if stats else 0.0
        if matches > 0:
            entry.avg_final_value = round(stats["final_value_sum"] / matches, 2)
            entry.avg_return_pct = round(stats["return_sum"] / matches, 3)
            entry.avg_max_drawdown_pct = round(stats["drawdown_sum"] / matches, 3)
            entry.win_rate = round(entry.wins / matches, 3)
        entry.last_updated = now

    leaderboard = list(entries.values())
    leaderboard.sort(
        key=lambda item: (-item.wins, -item.avg_final_value, -item.avg_return_pct, item.agent_name)
    )
    return leaderboard
