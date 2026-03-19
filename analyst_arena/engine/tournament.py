from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations

from analyst_arena.agents.base import Agent
from analyst_arena.engine.match import MatchEngine, MatchResult


@dataclass(slots=True)
class LeaderboardEntry:
    agent: str
    wins: int
    losses: int
    avg_score: float


class Tournament:
    def __init__(self, agents: list[Agent], match_engine: MatchEngine | None = None) -> None:
        self.agents = agents
        self.results: list[MatchResult] = []
        self._match_engine = match_engine or MatchEngine()

    def run_round_robin(self, scenario: str = "analyst_debate") -> list[MatchResult]:
        for agent_a, agent_b in combinations(self.agents, 2):
            self.results.append(self._match_engine.run_match(agent_a, agent_b, scenario))
        return list(self.results)

    def run_single_match(
        self,
        agent_a: Agent,
        agent_b: Agent,
        scenario: str = "analyst_debate",
    ) -> MatchResult:
        result = self._match_engine.run_match(agent_a, agent_b, scenario)
        self.results.append(result)
        return result

    def leaderboard(self) -> list[dict[str, str | int | float]]:
        stats: dict[str, dict[str, float]] = {}
        for agent in self.agents:
            stats[agent.name] = {"wins": 0.0, "losses": 0.0, "total_score": 0.0, "matches": 0.0}

        for result in self.results:
            stats[result.agent_a]["total_score"] += result.score_a
            stats[result.agent_a]["matches"] += 1
            stats[result.agent_b]["total_score"] += result.score_b
            stats[result.agent_b]["matches"] += 1

            if result.winner == result.agent_a:
                stats[result.agent_a]["wins"] += 1
                stats[result.agent_b]["losses"] += 1
            elif result.winner == result.agent_b:
                stats[result.agent_b]["wins"] += 1
                stats[result.agent_a]["losses"] += 1

        leaderboard = [
            LeaderboardEntry(
                agent=agent_name,
                wins=int(values["wins"]),
                losses=int(values["losses"]),
                avg_score=round(values["total_score"] / values["matches"], 1) if values["matches"] else 0.0,
            )
            for agent_name, values in stats.items()
        ]
        leaderboard.sort(key=lambda item: (-item.wins, -item.avg_score, item.agent))
        return [asdict(entry) for entry in leaderboard]
