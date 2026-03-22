from __future__ import annotations

import json
import re
from typing import Any

from analyst_arena.models import TradeAction


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_scenario_result(raw_response: str, scenario_name: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_response) if isinstance(raw_response, str) else dict(raw_response)
    except json.JSONDecodeError:
        payload = {}
        if isinstance(raw_response, str):
            # Models sometimes wrap JSON in prose or code fences.
            match = re.search(r"\{[\s\S]*\}", raw_response)
            if match:
                try:
                    candidate = json.loads(match.group(0))
                    if isinstance(candidate, dict):
                        payload = candidate
                except json.JSONDecodeError:
                    payload = {}
    if not isinstance(payload, dict):
        payload = {}

    metadata = dict(payload.get("metadata", {}))
    metadata["scenario_name"] = scenario_name

    action_value = str(payload.get("action", TradeAction.HOLD.value)).upper().strip()
    if action_value not in {item.value for item in TradeAction}:
        action_value = TradeAction.HOLD.value

    return {
        "scenario_name": scenario_name,
        "as_of_date": str(payload.get("as_of_date", "")).strip(),
        "action": action_value,
        "size_pct": max(0.0, min(1.0, _safe_float(payload.get("size_pct", 0.0), 0.0))),
        "position_size": max(0.0, min(1.0, _safe_float(payload.get("position_size", payload.get("size_pct", 0.0)), 0.0))),
        "horizon": str(payload.get("horizon", "short")).strip() or "short",
        "rationale": str(payload.get("rationale", "")).strip(),
        "confidence": max(0.0, min(1.0, _safe_float(payload.get("confidence", 0.0), 0.0))),
        "summary": str(payload.get("summary", payload.get("one_sentence_summary", ""))).strip(),
        "top_reasons": [str(item).strip() for item in payload.get("top_reasons", []) if str(item).strip()],
        "top_risks": [str(item).strip() for item in payload.get("top_risks", []) if str(item).strip()],
        "invalidation_condition": str(payload.get("invalidation_condition", "")).strip(),
        "factor_scores": {str(k): _safe_float(v, 0.0) for k, v in dict(payload.get("factor_scores", {})).items()},
        "ranked_factors": [str(item).strip() for item in payload.get("ranked_factors", []) if str(item).strip()],
        "factor_weights": {str(k): _safe_float(v, 0.0) for k, v in dict(payload.get("factor_weights", {})).items()},
        "decisive_metrics": [str(item).strip() for item in payload.get("decisive_metrics", []) if str(item).strip()],
        "noisy_metrics": [str(item).strip() for item in payload.get("noisy_metrics", []) if str(item).strip()],
        "stock_archetype": str(payload.get("stock_archetype", "")).strip(),
        "market_regime": str(payload.get("market_regime", "")).strip(),
        "decision_quality": str(payload.get("decision_quality", "")).strip(),
        "process_quality": str(payload.get("process_quality", "")).strip(),
        "luck_vs_skill": str(payload.get("luck_vs_skill", "")).strip(),
        "confidence_assessment": str(payload.get("confidence_assessment", "")).strip(),
        "size_assessment": str(payload.get("size_assessment", "")).strip(),
        "signals_helped": [str(item).strip() for item in payload.get("signals_helped", []) if str(item).strip()],
        "signals_misled": [str(item).strip() for item in payload.get("signals_misled", []) if str(item).strip()],
        "next_time_changes": [str(item).strip() for item in payload.get("next_time_changes", []) if str(item).strip()],
        "outcome_summary": str(payload.get("outcome_summary", "")).strip(),
        "hindsight_flags": [str(item).strip() for item in payload.get("hindsight_flags", []) if str(item).strip()],
        "raw_response": raw_response,
        "metadata": metadata,
    }
