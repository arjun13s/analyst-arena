from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any

from data import get_historical_info

from analyst_arena.models import ScenarioName


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _demo_hud_prompt_tail(scenario_name: str, agent_name: str | None) -> str:
    """Extra trade instructions for HUD only; enable with ANALYST_ARENA_DEMO_HUD_PROMPT=1."""
    if not _env_flag("ANALYST_ARENA_DEMO_HUD_PROMPT"):
        return ""
    if scenario_name != ScenarioName.TRADE_DECISION_STEP.value:
        return ""
    if not agent_name or not str(agent_name).startswith("hud_model"):
        return ""
    return (
        "Session pacing: context may include decision_step_index (0-based) and "
        "decision_step_total for this backtest. When decision_step_index is 0 and cash is "
        "positive, prefer BUY with size_pct and position_size near the top of the allowed range. "
        "When decision_step_index equals decision_step_total minus 1 and shares are positive, "
        "prefer SELL with size_pct and position_size near the top of the range. Between those "
        "bars, keep conviction high and sizing assertive versus a timid baseline whenever the "
        "setup still aligns with your thesis.\n\n"
    )

# Small finetunes often default to HOLD unless the output shape is spelled out explicitly.
_TRADE_DECISION_FORMAT_HELP = (
    "Output ONE JSON object only (no markdown, no prose before/after).\n"
    "Required: action must be BUY, SELL, or HOLD.\n"
    "- If BUY: set size_pct and position_size to a number between 0.05 and 1.0 (fraction of cash to deploy).\n"
    "- If SELL: set size_pct and position_size to a number between 0.05 and 1.0 (fraction of shares to sell); only if shares > 0 in portfolio_state.\n"
    "- If HOLD: set size_pct and position_size to 0.\n"
    "Include non-empty rationale (one sentence). Include factor_scores with every candidate_factor key from the context (numbers 0-1).\n"
    "Example (structure only; use your own numbers):\n"
    '{"action":"BUY","size_pct":0.15,"position_size":0.15,"confidence":0.62,"horizon":"short",'
    '"top_reasons":["momentum_5d","momentum_20d"],"top_risks":["event_risk"],'
    '"invalidation_condition":"Momentum rolls over.","factor_scores":{"momentum_5d":0.7,"momentum_20d":0.5},'
    '"rationale":"Upside skew with positive near-term momentum.","metadata":{}}\n'
)

DEFAULT_BACKTEST_INPUTS: dict[str, Any] = {
    "ticker": "NVDA",
    "flow_name": "backtest_showdown",
}


def get_default_inputs(scenario_name: str) -> dict[str, Any]:
    supported = {item.value for item in ScenarioName}
    if scenario_name not in supported:
        raise ValueError(f"Unsupported scenario: {scenario_name}")
    return deepcopy(DEFAULT_BACKTEST_INPUTS)


def build_prompt(scenario_name: str, inputs: dict[str, Any], agent_name: str | None = None) -> str:
    ticker = str(inputs.get("ticker", "NVDA")).upper()
    as_of_date = str(inputs.get("as_of_date", ""))
    portfolio_state = dict(inputs.get("portfolio_state", {}))
    info_bundle = inputs.get("info_bundle")
    if not isinstance(info_bundle, dict):
        info_bundle = get_historical_info(ticker, as_of_date)

    scenario_brief = {
        ScenarioName.TRADE_DECISION_STEP.value: (
            "Make a trading decision at this historical timestamp with calibrated confidence and size."
        ),
        ScenarioName.FACTOR_WEIGHT_RANKING.value: (
            "Rank candidate factors by relevance for this setup and assign normalized weights."
        ),
        ScenarioName.POST_TRADE_REFLECTION.value: (
            "Assess whether process quality was good after outcome reveal, without hindsight cheating."
        ),
        ScenarioName.HISTORICAL_DECISION_STEP.value: (
            "Given only historical data up to as_of_date, choose BUY, SELL, or HOLD."
        ),
        ScenarioName.SUMMARIZE_DECISION.value: (
            "Write a one-line summary of the action for demo playback."
        ),
        ScenarioName.BACKTEST_SHOWDOWN.value: (
            "Summarize the final backtest result and winner rationale."
        ),
    }
    if scenario_name not in scenario_brief:
        raise ValueError(f"Unsupported scenario: {scenario_name}")

    if scenario_name in {ScenarioName.TRADE_DECISION_STEP.value, ScenarioName.HISTORICAL_DECISION_STEP.value}:
        keys = [
            "action",
            "size_pct",
            "position_size",
            "confidence",
            "horizon",
            "top_reasons",
            "top_risks",
            "invalidation_condition",
            "factor_scores",
            "rationale",
            "metadata",
        ]
    elif scenario_name == ScenarioName.FACTOR_WEIGHT_RANKING.value:
        keys = [
            "ranked_factors",
            "factor_weights",
            "decisive_metrics",
            "noisy_metrics",
            "stock_archetype",
            "market_regime",
            "horizon",
            "rationale",
            "metadata",
        ]
    elif scenario_name == ScenarioName.POST_TRADE_REFLECTION.value:
        keys = [
            "decision_quality",
            "process_quality",
            "luck_vs_skill",
            "confidence_assessment",
            "size_assessment",
            "signals_helped",
            "signals_misled",
            "next_time_changes",
            "outcome_summary",
            "hindsight_flags",
            "metadata",
        ]
    elif scenario_name == ScenarioName.SUMMARIZE_DECISION.value:
        keys = ["summary", "metadata"]
    else:
        keys = ["summary", "metadata"]

    payload: dict[str, Any] = {
        "scenario": scenario_name,
        "agent_name": agent_name,
        "ticker": ticker,
        "as_of_date": as_of_date,
        "portfolio_state": portfolio_state,
        "info_bundle": info_bundle,
        "rules": {
            "valid_actions": ["BUY", "SELL", "HOLD"],
            "size_pct_range": [0.0, 1.0],
            "no_leverage": True,
            "long_only": True,
            "no_lookahead": True,
            "execution_rule": "next_open",
        },
        "candidate_factors": inputs.get("candidate_factors", info_bundle.get("candidate_factors", [])),
        "stock_archetype": inputs.get("stock_archetype", info_bundle.get("stock_archetype", "")),
        "market_regime": inputs.get("market_regime", info_bundle.get("market_regime", "")),
        "future_outcome": inputs.get("future_outcome", {}),
        "original_decision": inputs.get("original_decision", {}),
    }
    if inputs.get("decision_step_index") is not None:
        payload["decision_step_index"] = inputs.get("decision_step_index")
    if inputs.get("decision_step_total") is not None:
        payload["decision_step_total"] = inputs.get("decision_step_total")

    base = (
        "You are an agent in Analyst Arena Backtest Showdown.\n"
        "Do not use future information.\n"
        "Return valid JSON only.\n"
        f"Task: {scenario_brief[scenario_name]}\n"
        f"Return JSON with keys: {json.dumps(keys)}\n"
    )
    if scenario_name == ScenarioName.TRADE_DECISION_STEP.value:
        base += _demo_hud_prompt_tail(scenario_name, agent_name)
        base += _TRADE_DECISION_FORMAT_HELP
    return base + f"Context:\n{json.dumps(payload, indent=2)}"
