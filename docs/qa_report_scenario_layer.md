# QA Review: Trading Judgment Scenario Layer

## Scope reviewed

- Scenario definitions and reward logic in `env.py`
- Scenario prompt contracts in `analyst_arena/engine/scenarios.py`
- Typed schemas in `analyst_arena/models/schemas.py`
- Parsing/normalization in `analyst_arena/integrations/response.py`
- Evaluation logic in `analyst_arena/scoring/scenario_eval.py`
- Engine integration in `analyst_arena/engine/match.py`
- Historical data/no-lookahead helpers in `data.py`

## What was built

- Added active scenarios:
  - `trade_decision_step`
  - `factor_weight_ranking`
  - `post_trade_reflection`
- Extended typed output contracts for decision, factor ranking, and reflection.
- Added scenario evaluation functions aligned with decision quality.
- Wired scenarios into backtest engine for per-step capture and evaluation.
- Kept `historical_decision_step` as backward-compatible narrow wrapper.

## QA findings and fixes applied

1. Context scoring bug fixed:
- `scenario_eval._extract_factor_signal` now reads `market_regime` and `stock_archetype` from typed bundle fields (not metadata fallback).

2. Reflection process scoring tightened:
- `process_quality` is now evaluated relative to whether the original action was directionally correct, reducing easy reward gaming.

## Does this train better buy/sell judgment?

Yes, materially better than a narrative-only flow:
- Core reward now depends on directional and sizing/calibration behavior.
- Factor selection is separately trained and scored.
- Reflection trains process quality after outcome reveal.

## Leakage risk review

Current active path:
- `trade_decision_step`: no future data in prompt/context.
- `factor_weight_ranking`: no future data in prompt/context.
- `post_trade_reflection`: receives future outcome by design.

Leakage watchpoints:
- Ensure `future_outcome` is never passed to decision/ranking scenario calls.
- Ensure `get_historical_info` remains sliced at `as_of_date`.

## Reward-hacking risk review

Potential vectors:
- Stuffing long rationale text without real structure.
- Vague reflection language that avoids concrete self-critique.

Current mitigations:
- Structured JSON keys are required and parsed.
- Scores prioritize objective components over prose length.
- Hindsight-language penalty included.

## Fragile assumptions

- Outcome-relevant factor proxy is heuristic and deterministic; may underfit real market structure.
- Short horizon directional labels are noisy.
- Reflection language analysis is lexical and can be improved with stronger validators.

## Recommended next tests

1. Schema robustness tests for malformed JSON and missing fields.
2. No-lookahead tests asserting scenario inputs never contain forward windows before reflection phase.
3. Calibration stress tests on extreme confidence/size outputs.
4. Sensitivity tests by ticker archetype and regime transitions.
