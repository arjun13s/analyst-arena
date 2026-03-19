from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from analyst_arena.agents.base import Agent, ScenarioResult
from analyst_arena.engine.scenarios import get_default_inputs
from analyst_arena.scoring.evaluator import evaluate_matchup


@dataclass(slots=True)
class MatchResult:
    agent_a: str
    agent_b: str
    score_a: float
    score_b: float
    winner: str
    details: dict[str, Any]


class MatchEngine:
    def run_match(
        self,
        agent_a: Agent,
        agent_b: Agent,
        scenario: str,
        inputs: dict[str, Any] | None = None,
    ) -> MatchResult:
        scenario_inputs = inputs or get_default_inputs(scenario)
        result_a = agent_a.run_scenario(scenario, dict(scenario_inputs))
        result_b = agent_b.run_scenario(scenario, dict(scenario_inputs))
        return self._build_result(
            agent_a=agent_a,
            agent_b=agent_b,
            scenario=scenario,
            inputs=scenario_inputs,
            result_a=result_a,
            result_b=result_b,
        )

    def _build_result(
        self,
        agent_a: Agent,
        agent_b: Agent,
        scenario: str,
        inputs: dict[str, Any],
        result_a: ScenarioResult,
        result_b: ScenarioResult,
    ) -> MatchResult:
        scored = evaluate_matchup(
            scenario_name=scenario,
            inputs=inputs,
            agent_a_name=agent_a.name,
            agent_b_name=agent_b.name,
            result_a=result_a,
            result_b=result_b,
        )
        return MatchResult(
            agent_a=agent_a.name,
            agent_b=agent_b.name,
            score_a=scored["score_a"],
            score_b=scored["score_b"],
            winner=scored["winner"],
            details={
                "scenario": scenario,
                "inputs": inputs,
                "agent_a_result": dict(result_a),
                "agent_b_result": dict(result_b),
                "agent_a_score": asdict(scored["thesis_score_a"]),
                "agent_b_score": asdict(scored["thesis_score_b"]),
                "pm_decision": scored["pm_decision"],
            },
        )
