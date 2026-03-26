from __future__ import annotations

import logging
import time
from typing import Any, TypedDict

from analyst_arena.integrations import HUDClient
from analyst_arena.models import Agent as AgentSpec

logger = logging.getLogger(__name__)

ScenarioInputs = dict[str, Any]

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0


def _scenario_response_looks_empty(scenario_name: str, result: dict[str, Any]) -> bool:
    """Trade scenarios use action/rationale; reflection/ranking use other required fields."""
    if scenario_name == "post_trade_reflection":
        return not (
            str(result.get("outcome_summary", "")).strip()
            or str(result.get("decision_quality", "")).strip()
        )
    if scenario_name == "factor_weight_ranking":
        return not (result.get("ranked_factors") or str(result.get("rationale", "")).strip())
    action = str(result.get("action", "HOLD")).upper()
    try:
        size = float(result.get("size_pct", 0.0))
    except (TypeError, ValueError):
        size = 0.0
    return action == "HOLD" and size == 0.0 and not str(result.get("rationale", "")).strip()


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
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = self.client.run_scenario(
                    scenario_name=scenario_name,
                    agent_name=self.name,
                    inputs=inputs,
                )
                if _scenario_response_looks_empty(scenario_name, result):
                    logger.warning(
                        "[%s] scenario=%s returned empty/default response (attempt %d/%d)",
                        self.name, scenario_name, attempt, MAX_RETRIES,
                    )
                return ScenarioResult(**result)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.error(
                    "[%s] scenario=%s failed (attempt %d/%d): %s",
                    self.name, scenario_name, attempt, MAX_RETRIES, exc,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_BASE ** attempt)

        logger.error(
            "[%s] scenario=%s exhausted all %d retries, returning HOLD fallback. Last error: %s",
            self.name, scenario_name, MAX_RETRIES, last_error,
        )
        return ScenarioResult(
            scenario_name=scenario_name,
            action="HOLD",
            size_pct=0.0,
            position_size=0.0,
            confidence=0.0,
            rationale=f"Fallback HOLD: API failed after {MAX_RETRIES} retries ({last_error})",
            metadata={"agent_name": self.name, "fallback": True, "error": str(last_error)},
        )

    def describe(self) -> AgentSpec:
        return AgentSpec(
            name=self.name,
            provider=self.provider,
            model_id=self.model_id or "unknown",
            display_name=self.display_name,
            metadata=dict(self.metadata),
        )
