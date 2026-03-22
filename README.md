# Analyst Arena

Analyst Arena is a model-vs-model **backtest trading showdown**. Two agents trade the same ticker over the same 3-month historical window with strict no-lookahead rules.

## Product Flow

1. Pick ticker: `NVDA`, `AAPL`, or `GOOGL`
2. Start simulation for two agents
3. Each day:
   - agent sees only data available up to that date
   - agent returns `BUY` / `SELL` / `HOLD` with `size_pct`
   - trade executes at next trading day open
4. End of window:
   - compare final portfolio values
   - winner is objective (highest final value)
5. Persist match + leaderboard

## Core Rules

- Starting cash: `$100,000`
- Long-only, no leverage
- Cannot buy beyond available cash
- Cannot sell beyond held shares
- Default transaction costs: `0 bps` (configurable in engine)
- Execution rule: `next_open`

## Quick Start

```bash
cd analyst_arena
uv pip install -e .
```

### Run single match

```bash
python run_single_match.py hud_model gpt4o --ticker NVDA --months 3 --starting-cash 100000
```

### Run round robin

```bash
python run_round_robin.py --agents hud_model gpt4o claude grok --tickers NVDA AAPL GOOGL
```

### Run demo UI

```bash
streamlit run streamlit_app.py
```

## API Keys

Set the keys for agents you want to run:

- `HUD_API_KEY` for `hud_model`
- `OPENAI_API_KEY` for `gpt4o`
- `ANTHROPIC_API_KEY` for `claude`
- `XAI_API_KEY` for `grok`

Optional model overrides:

- `HUD_MODEL`
- `OPENAI_MODEL`
- `ANTHROPIC_MODEL`
- `GROK_MODEL`

## HUD Environment

`env.py` exposes tools/scenarios for historical decision-making:

- `get_historical_info(ticker, as_of_date)`
- `reason_to_trade(...)`
- `compute_portfolio_snapshot(...)`
- scenario `trade_decision_step`
- scenario `factor_weight_ranking`
- scenario `post_trade_reflection`
- scenario `historical_decision_step` (legacy compatibility)
- scenario `summarize_decision`
- scenario `backtest_showdown`

## Persistence

- `match_results.json`: full match history
- `leaderboard.json`: aggregate wins/losses and average performance
