from __future__ import annotations

from typing import Any

from analyst_arena.models import (
    ActionDecision,
    FactorWeightRankingResult,
    HistoricalInfoBundle,
    PostTradeReflectionResult,
    ScenarioEvaluation,
    TradeAction,
)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _soft_alignment(actual: float, target: float, tolerance: float = 0.2) -> float:
    """
    More forgiving alignment score.
    Full credit inside tolerance band, then linearly decays.
    """
    gap = abs(actual - target)
    if gap <= tolerance:
        return 1.0
    return _clamp01(1.0 - ((gap - tolerance) / max(1e-6, 1.0 - tolerance)))


def _normalize_action_from_return(forward_return_pct: float, neutral_band_pct: float = 1.0) -> TradeAction:
    if forward_return_pct > neutral_band_pct:
        return TradeAction.BUY
    if forward_return_pct < -neutral_band_pct:
        return TradeAction.SELL
    return TradeAction.HOLD


def _extract_factor_signal(bundle: HistoricalInfoBundle, forward_return_pct: float) -> dict[str, float]:
    stats = dict(bundle.summary_stats)
    fin = dict(bundle.financial_context)
    regime = str(bundle.market_regime).lower()
    archetype = str(bundle.stock_archetype).lower()

    ret_5d = float(stats.get("return_5d_pct", 0.0))
    ret_20d = float(stats.get("return_20d_pct", 0.0))
    vol_20 = float(stats.get("volatility_20d_pct", 0.0))
    rev_growth = float(fin.get("revenue_growth_yoy", 0.0))
    gross_margin = float(fin.get("gross_margin", 0.0))
    fcf_margin = float(fin.get("fcf_margin", 0.0))

    target: dict[str, float] = {
        "momentum_5d": min(1.0, abs(ret_5d) / 5.0),
        "momentum_20d": min(1.0, abs(ret_20d) / 8.0),
        "volatility_20d": min(1.0, vol_20 / 3.0),
        "volume_trend_5d": 0.35,
        "revenue_growth_yoy": min(1.0, max(0.0, rev_growth) / 0.35),
        "gross_margin": min(1.0, max(0.0, gross_margin) / 0.8),
        "fcf_margin": min(1.0, max(0.0, fcf_margin) / 0.6),
        "valuation_vs_growth": 0.45,
    }

    if forward_return_pct > 0:
        target["momentum_20d"] = min(1.0, target["momentum_20d"] + 0.15)
        target["revenue_growth_yoy"] = min(1.0, target["revenue_growth_yoy"] + 0.1)
    elif forward_return_pct < 0:
        target["volatility_20d"] = min(1.0, target["volatility_20d"] + 0.15)

    if regime in {"risk_on_trend"}:
        target["momentum_5d"] = min(1.0, target["momentum_5d"] + 0.15)
        target["momentum_20d"] = min(1.0, target["momentum_20d"] + 0.1)
    elif regime in {"risk_off_drawdown", "high_volatility"}:
        target["volatility_20d"] = min(1.0, target["volatility_20d"] + 0.1)

    if archetype in {"high_growth", "platform_growth"}:
        target["revenue_growth_yoy"] = min(1.0, target["revenue_growth_yoy"] + 0.1)
        target["fcf_margin"] = max(0.0, target["fcf_margin"] - 0.05)
    elif archetype in {"mature_quality"}:
        target["fcf_margin"] = min(1.0, target["fcf_margin"] + 0.15)
        target["gross_margin"] = min(1.0, target["gross_margin"] + 0.1)

    return target


def evaluate_trade_decision_step(
    decision: ActionDecision,
    info_bundle: HistoricalInfoBundle,
    forward_return_pct: float,
) -> ScenarioEvaluation:
    expected_action = _normalize_action_from_return(forward_return_pct)
    # Lenient direction scoring: partial credit for adjacent mistakes.
    direction = 1.0 if decision.action == expected_action else 0.35
    if expected_action == TradeAction.HOLD and decision.action in {TradeAction.BUY, TradeAction.SELL}:
        direction = 0.45

    confidence_target = direction
    calibration_error = abs(float(decision.confidence) - confidence_target)
    calibration = _clamp01(1.0 - 0.7 * calibration_error)

    edge_strength = _clamp01(abs(forward_return_pct) / 5.0)
    if decision.action == TradeAction.HOLD:
        target_size = 0.0
    elif direction >= 1.0:
        target_size = 0.15 + 0.55 * edge_strength
    else:
        target_size = 0.05
    sizing = _soft_alignment(float(decision.size_pct), target_size, tolerance=0.2)

    factor_signal = _extract_factor_signal(info_bundle, forward_return_pct)
    expected_top = [name for name, score in sorted(factor_signal.items(), key=lambda kv: kv[1], reverse=True)[:3]]
    reason_text = " ".join(decision.top_reasons + [decision.rationale]).lower()
    factor_hits = sum(1 for factor in expected_top if factor.split("_")[0] in reason_text or factor in reason_text)
    factor_relevance = _clamp01((factor_hits + 0.5) / max(1, len(expected_top)))

    risk_awareness = 0.0
    if decision.top_risks:
        risk_awareness += 0.5
    if decision.invalidation_condition:
        risk_awareness += 0.5
    risk_awareness = _clamp01(risk_awareness)

    score = (
        0.34 * direction
        + 0.22 * calibration
        + 0.20 * sizing
        + 0.14 * factor_relevance
        + 0.10 * risk_awareness
    )
    # Base credit prevents overly harsh "glow score" collapse.
    score = 0.12 + 0.88 * score

    notes: list[str] = []
    if direction < 0.7:
        notes.append(f"Direction mismatch: expected {expected_action.value}.")
    if calibration < 0.3:
        notes.append("Confidence was poorly calibrated to realized direction.")
    if sizing < 0.3:
        notes.append("Position size was misaligned with estimated edge.")

    return ScenarioEvaluation(
        score=round(_clamp01(score), 4),
        components={
            "directional_correctness": round(direction, 4),
            "confidence_calibration": round(calibration, 4),
            "position_sizing": round(sizing, 4),
            "factor_relevance": round(factor_relevance, 4),
            "risk_controls": round(risk_awareness, 4),
        },
        notes=notes,
        metadata={
            "forward_return_pct": round(float(forward_return_pct), 4),
            "expected_action": expected_action.value,
        },
    )


def evaluate_factor_weight_ranking(
    ranking: FactorWeightRankingResult,
    info_bundle: HistoricalInfoBundle,
    forward_return_pct: float,
) -> ScenarioEvaluation:
    target = _extract_factor_signal(info_bundle, forward_return_pct)
    ranked_factors = ranking.ranked_factors
    top_expected = [name for name, _ in sorted(target.items(), key=lambda kv: kv[1], reverse=True)[:5]]
    overlap = len(set(ranked_factors[:5]) & set(top_expected))
    ranking_score = _clamp01((overlap + 1) / (max(1, len(top_expected)) + 1))

    weight_map = dict(ranking.factor_weights)
    if weight_map:
        weight_sum = sum(max(0.0, value) for value in weight_map.values())
        normalized = {name: (max(0.0, value) / weight_sum if weight_sum > 0 else 0.0) for name, value in weight_map.items()}
        target_total = sum(target.values()) or 1.0
        target_normalized = {name: (value / target_total) for name, value in target.items()}
        common_keys = set(normalized.keys()) | set(target_normalized.keys())
        l1_error = sum(abs(normalized.get(key, 0.0) - target_normalized.get(key, 0.0)) for key in common_keys) / 2.0
        weight_quality = _clamp01(1.0 - 0.75 * l1_error)
    else:
        weight_quality = 0.0

    low_signal = {name for name, value in target.items() if value < 0.35}
    noisy_detect = set(ranking.noisy_metrics)
    noise_score = _clamp01((len(noisy_detect & low_signal) + 0.5) / max(1, len(noisy_detect))) if noisy_detect else 0.45

    rationale_score = 0.0
    if ranking.rationale:
        rationale_score += 0.5
    if ranking.decisive_metrics:
        rationale_score += 0.5 * _clamp01(
            len(set(ranking.decisive_metrics) & set(ranked_factors[:5])) / max(1, len(ranking.decisive_metrics))
        )
    rationale_score = _clamp01(rationale_score)

    score = 0.42 * ranking_score + 0.30 * weight_quality + 0.12 * noise_score + 0.16 * rationale_score
    score = 0.10 + 0.90 * score
    notes: list[str] = []
    if ranking_score < 0.3:
        notes.append("Top-ranked factors did not match outcome-relevant factors.")
    if weight_quality < 0.3:
        notes.append("Factor weights were not context-sensitive.")

    return ScenarioEvaluation(
        score=round(_clamp01(score), 4),
        components={
            "ranking_alignment": round(ranking_score, 4),
            "weight_quality": round(weight_quality, 4),
            "noise_filtering": round(noise_score, 4),
            "rationale_consistency": round(rationale_score, 4),
        },
        notes=notes,
        metadata={"forward_return_pct": round(float(forward_return_pct), 4)},
    )


def evaluate_post_trade_reflection(
    reflection: PostTradeReflectionResult,
    decision: ActionDecision,
    forward_return_pct: float,
) -> ScenarioEvaluation:
    expected_action = _normalize_action_from_return(forward_return_pct)
    was_correct = decision.action == expected_action

    label = reflection.decision_quality.lower()
    if was_correct:
        decision_label_score = 1.0 if label in {"good", "strong"} else 0.7 if label == "mixed" else 0.35
    else:
        decision_label_score = 1.0 if label in {"bad", "weak"} else 0.7 if label == "mixed" else 0.35

    confidence_level = float(decision.confidence)
    calibration_good = (was_correct and confidence_level >= 0.55) or ((not was_correct) and confidence_level <= 0.55)
    confidence_text = reflection.confidence_assessment.lower()
    if calibration_good:
        confidence_score = 1.0 if any(token in confidence_text for token in ("appropriate", "calibrated", "reasonable")) else 0.75
    else:
        confidence_score = 1.0 if any(token in confidence_text for token in ("too high", "too low", "overconfident", "underconfident")) else 0.45

    size_level = float(decision.size_pct)
    edge_strength = _clamp01(abs(forward_return_pct) / 5.0)
    ideal_size = 0.0 if expected_action == TradeAction.HOLD else (0.15 + 0.55 * edge_strength)
    size_gap = abs(size_level - ideal_size)
    size_text = reflection.size_assessment.lower()
    if size_gap <= 0.25:
        size_score = 1.0 if any(token in size_text for token in ("appropriate", "reasonable", "right-sized")) else 0.75
    else:
        size_score = 1.0 if any(token in size_text for token in ("too large", "too small", "oversized", "undersized")) else 0.45

    process_quality = reflection.process_quality.lower()
    if was_correct:
        process_score = 1.0 if process_quality in {"good", "strong"} else 0.75 if process_quality == "mixed" else 0.45
    else:
        process_score = 1.0 if process_quality in {"bad", "weak"} else 0.75 if process_quality == "mixed" else 0.45
    learning_score = _clamp01(
        (1.0 if reflection.next_time_changes else 0.0) * 0.6
        + (1.0 if reflection.signals_misled else 0.0) * 0.2
        + (1.0 if reflection.signals_helped else 0.0) * 0.2
    )

    hindsight_penalty = 0.0
    hindsight_text = (reflection.outcome_summary + " " + " ".join(reflection.hindsight_flags)).lower()
    if any(token in hindsight_text for token in ("obvious", "always", "should have known", "guaranteed")):
        hindsight_penalty = 0.1

    score = (
        0.25 * decision_label_score
        + 0.2 * process_score
        + 0.2 * confidence_score
        + 0.15 * size_score
        + 0.2 * learning_score
        - hindsight_penalty
    )
    score = 0.10 + 0.90 * score

    notes: list[str] = []
    if hindsight_penalty > 0:
        notes.append("Potential hindsight-cheating language detected.")
    if learning_score < 0.5:
        notes.append("Reflection lacks actionable improvement signals.")

    return ScenarioEvaluation(
        score=round(_clamp01(score), 4),
        components={
            "decision_vs_outcome": round(decision_label_score, 4),
            "process_judgment": round(process_score, 4),
            "confidence_adjustment": round(confidence_score, 4),
            "size_adjustment": round(size_score, 4),
            "learning_value": round(learning_score, 4),
            "hindsight_penalty": round(hindsight_penalty, 4),
        },
        notes=notes,
        metadata={
            "forward_return_pct": round(float(forward_return_pct), 4),
            "expected_action": expected_action.value,
            "actual_action": decision.action.value,
        },
    )


def evaluation_to_reward(evaluation: ScenarioEvaluation) -> float:
    return round(_clamp01(evaluation.score), 4)
