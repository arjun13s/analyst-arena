from __future__ import annotations

from typing import Any, TypedDict

from analyst_arena.integrations import HUDClient
from analyst_arena.models import Agent as AgentSpec


ScenarioInputs = dict[str, Any]


class ScenarioResult(TypedDict, total=False):
    scenario_name: str
    as_of_date: str
    action: str
    size_pct: float
    position_size: float
    horizon: str
    rationale: str
    confidence: float
    summary: str
    top_reasons: list[str]
    top_risks: list[str]
    invalidation_condition: str
    factor_scores: dict[str, float]
    ranked_factors: list[str]
    factor_weights: dict[str, float]
    decisive_metrics: list[str]
    noisy_metrics: list[str]
    stock_archetype: str
    market_regime: str
    decision_quality: str
    process_quality: str
    luck_vs_skill: str
    confidence_assessment: str
    size_assessment: str
    signals_helped: list[str]
    signals_misled: list[str]
    next_time_changes: list[str]
    outcome_summary: str
    hindsight_flags: list[str]
    raw_response: str
    metadata: dict[str, Any]


class Agent:
    def __init__(
        self,
        name: str,
        client: HUDClient,
        *,
        model: str | None = None,
        provider: str | None = None,
        display_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.client = client
        self.model = model
        self.model_id = model
        self.provider = provider or "unknown"
        self.display_name = display_name or name
        self.metadata = metadata or {}

    def run_scenario(self, scenario_name: str, inputs: ScenarioInputs) -> ScenarioResult:
        result = self.client.run_scenario(
            scenario_name=scenario_name,
            agent_name=self.name,
            inputs=inputs,
        )
        return ScenarioResult(**result)

    def describe(self) -> AgentSpec:
        return AgentSpec(
            name=self.name,
            provider=self.provider,
            model_id=self.model_id or "unknown",
            display_name=self.display_name,
            metadata=dict(self.metadata),
        )
