# Scenario Design Spec: Trading Judgment Layer

## 1) `trade_decision_step`

### Purpose
Train the model to make a real timestamped buy/sell/hold decision with calibrated confidence, sizing, and risk controls.

### Input schema (logical)
- `ticker: str`
- `as_of_date: str`
- `portfolio_state: {cash: float, shares: float, ...}`
- `info_bundle: HistoricalInfoBundle`
  - contains only data visible up to `as_of_date`
  - includes price history slice, summary stats, dated events, factor context

### Output schema
- `action: BUY | SELL | HOLD`
- `confidence: float [0,1]`
- `position_size: float [0,1]`
- `size_pct: float [0,1]`
- `horizon: short | medium | long`
- `top_reasons: list[str]`
- `top_risks: list[str]`
- `invalidation_condition: str`
- `factor_scores: dict[str, float]`
- `rationale: str`

### Evaluation logic
- Directional correctness vs realized forward return sign.
- Confidence calibration vs realized direction.
- Position sizing alignment vs estimated edge strength.
- Relevance of stated reasons to context/outcome-relevant factors.
- Presence of risk controls (`top_risks`, invalidation condition).

### Anti-leakage / anti-reward-hacking
- No future outcome is included in scenario input.
- Reward is structured-field and outcome-linked; verbose prose alone is not rewarded.

## 2) `factor_weight_ranking`

### Purpose
Teach contextual factor selection and weighting by regime/archetype/horizon.

### Input schema (logical)
- `ticker: str`
- `as_of_date: str`
- `horizon: str`
- `portfolio_state: dict`
- `info_bundle: HistoricalInfoBundle`
- `candidate_factors: list[str]`
- `stock_archetype: str`
- `market_regime: str`

### Output schema
- `ranked_factors: list[str]`
- `factor_weights: dict[str, float]`
- `decisive_metrics: list[str]`
- `noisy_metrics: list[str]`
- `stock_archetype: str`
- `market_regime: str`
- `horizon: str`
- `rationale: str`

### Evaluation logic
- Top-rank alignment to outcome-relevant factor set.
- Weight quality by distance to target normalized relevance profile.
- Noise filtering quality (identifying lower-signal factors).
- Rationale consistency with ranked decisive factors.

### Anti-leakage / anti-reward-hacking
- Inputs are capped to `as_of_date`.
- Weights/ranking are scored numerically against objective profiles.
- Generic prose without coherent ranking/weights gets low score.

## 3) `post_trade_reflection`

### Purpose
Train process-quality learning after outcome reveal and separate luck from skill.

### Input schema (logical)
- `ticker: str`
- `as_of_date: str`
- `original_decision: ActionDecision`
- `future_outcome: {forward_return_pct, forward_path, benchmark_return_pct}`
- `info_bundle`: original decision-time context

### Output schema
- `decision_quality: str`
- `process_quality: str`
- `luck_vs_skill: str`
- `confidence_assessment: str`
- `size_assessment: str`
- `signals_helped: list[str]`
- `signals_misled: list[str]`
- `next_time_changes: list[str]`
- `outcome_summary: str`
- `hindsight_flags: list[str]`

### Evaluation logic
- Correctness of decision-quality label relative to realized outcome.
- Process-quality diagnosis consistency.
- Confidence and sizing reassessment quality.
- Learning value from concrete next-step improvements.
- Hindsight-cheating penalty for deterministic hindsight language.

### Anti-leakage / anti-reward-hacking
- Reflection is the only scenario allowed to use revealed future path.
- Scoring rewards actionable process diagnosis, not polished narration.
