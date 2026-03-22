# Scoring Rubric: Decision-Quality Training Scenarios

## `trade_decision_step` (score in [0,1])

Weighted components:
- Directional correctness: `0.40`
- Confidence calibration: `0.20`
- Position sizing sensibility: `0.20`
- Factor relevance alignment: `0.15`
- Risk controls present: `0.05`

Design intent:
- Reward correct direction and calibrated conviction.
- Penalize overconfident wrong calls and oversized weak-edge trades.
- Require explicit risk/invalidation framing.

## `factor_weight_ranking` (score in [0,1])

Weighted components:
- Ranking alignment: `0.45`
- Weight quality: `0.35`
- Noise filtering: `0.10`
- Rationale consistency: `0.10`

Design intent:
- Emphasize selecting and weighting the right factors for context.
- Penalize context-insensitive weighting.
- Reduce reward for generic “everything matters” outputs.

## `post_trade_reflection` (score in [0,1], with penalty)

Weighted components:
- Decision-vs-outcome diagnosis: `0.25`
- Process judgment quality: `0.20`
- Confidence reassessment: `0.20`
- Sizing reassessment: `0.15`
- Learning value / actionable updates: `0.20`
- Hindsight-cheating penalty: `-0.20` max

Design intent:
- Teach robust process evaluation, not outcome worship.
- Reward concrete updates to improve next decision.
- Penalize hindsight certainty language.

## Calibration and noise notes

- Short-horizon labels are noisy; scoring blends direction, calibration, and process.
- Strong textual style does not materially improve reward without structured correctness.
- Reward is computed from typed outputs and bounded to `[0,1]`.
