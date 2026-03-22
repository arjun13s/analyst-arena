# Repo Assessment: Scenario Framework Extension

## Current scenario architecture

- HUD environment is defined in `env.py` using `@env.scenario(...)` and `@env.tool(...)`.
- Agent orchestration runs through:
  - `analyst_arena/integrations/client.py` (`HUDClient`)
  - `analyst_arena/engine/scenarios.py` (prompt builder)
  - `analyst_arena/engine/match.py` (backtest loop and per-step scenario calls)
- Typed schemas live in `analyst_arena/models/schemas.py` and are the canonical serialization contracts.
- Scenario scoring lives in `analyst_arena/scoring/scenario_eval.py`.

## Reuse and extension points used

- Reused historical data/no-lookahead primitives from `data.py`:
  - `get_historical_info`
  - `get_forward_return_pct`
  - `get_forward_window`
- Reused existing agent/provider abstraction and execution engine.
- Extended typed models rather than creating parallel DTOs.
- Extended existing scenario prompt/normalization path for consistent provider behavior.

## Migration decisions

- `trade_decision_step` is now the primary decision-quality scenario.
- `factor_weight_ranking` and `post_trade_reflection` are active training/eval scenarios.
- `historical_decision_step` remains only as a narrow backward-compatible wrapper.
- `summarize_decision` remains lightweight and non-core.

## Refactors made for consistency

- Added explicit schema types:
  - `FactorWeightRankingResult`
  - `PostTradeReflectionResult`
  - `ScenarioEvaluation`
- Added scenario enums for the three new scenarios.
- Extended `AgentBacktestResult` to persist decision/factor/reflection outputs and evaluations.
- Added deterministic evaluation functions tied to directional and process quality.
