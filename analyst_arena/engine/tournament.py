from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any

from analyst_arena.agents.base import Agent
from analyst_arena.engine.match import MatchEngine
from analyst_arena.models import LeaderboardEntry, MatchResult
from analyst_arena.scoring.leaderboard import build_leaderboard
from analyst_arena.storage.leaderboard import save_leaderboard
from analyst_arena.storage.results import load_results


class TournamentEngine:
    def __init__(
        self,
        agents: list[Agent],
        match_engine: MatchEngine | None = None,
        *,
        results_path: str | Path = "match_results.json",
        leaderboard_path: str | Path = "leaderboard.json",
    ) -> None:
        self.agents = agents
        self.results: list[MatchResult] = []
        self._match_engine = match_engine or MatchEngine(
            results_path=results_path,
            leaderboard_path=leaderboard_path,
        )
        self.results_path = Path(results_path)
        self.leaderboard_path = Path(leaderboard_path)

    def run_round_robin(
        self,
        *,
        ticker: str | None = "NVDA",
        tickers: list[str] | None = None,
        months: int = 3,
        starting_cash: float = 100000.0,
    ) -> list[MatchResult]:
        active_tickers = [item.upper() for item in (tickers or ([ticker] if ticker else []))]
        if not active_tickers:
            active_tickers = ["NVDA"]
        for agent_a, agent_b in combinations(self.agents, 2):
            for active_ticker in active_tickers:
                self.results.append(
                    self._match_engine.run_match(
                        [agent_a, agent_b],
                        ticker=active_ticker,
                        months=months,
                        starting_cash=starting_cash,
                    )
                )
        self._persist_leaderboard()
        return list(self.results)

    def run_single_match(
        self,
        agent_a: Agent,
        agent_b: Agent,
        *,
        ticker: str = "NVDA",
        months: int = 3,
        starting_cash: float = 100000.0,
    ) -> MatchResult:
        result = self._match_engine.run_match(
            [agent_a, agent_b],
            ticker=ticker,
            months=months,
            starting_cash=starting_cash,
        )
        self.results.append(result)
        self._persist_leaderboard()
        return result

    def leaderboard_entries(self) -> list[LeaderboardEntry]:
        loaded_results = load_results(self.results_path)
        combined = loaded_results if loaded_results else self.results
        return build_leaderboard(combined, [agent.name for agent in self.agents])

    def leaderboard(self) -> list[dict[str, Any]]:
        return [entry.to_dict() for entry in self.leaderboard_entries()]

    def _persist_leaderboard(self) -> None:
        save_leaderboard(self.leaderboard_entries(), self.leaderboard_path)


class Tournament(TournamentEngine):
    pass
