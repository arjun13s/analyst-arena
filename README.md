# Analyst Arena

Analyst Arena is a model-vs-model **backtest trading showdown**. Two agents trade the same ticker over the same 3-month historical window with strict no-lookahead rules, 10 days to make the most amount of money.

## Product Flow

1. Pick ticker: `NVDA`, `AAPL`, or `GOOGL`
2. Start simulation for two agents
3. Each day:
   - agent sees only data available up to that date
   - agent returns `BUY` / `SELL` / `HOLD` with `size_pct` -- % of portfolio
   - trade executes at next trading day open
4. End of window:
   - compare final portfolio values
   - winner is objective (highest final value)
5. Persist match + leaderboard

## Core Rules

- Starting cash: `$100,000`
- Long-only, no leverage, or shorts
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

### Run API backend

```bash
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

### Run Figma frontend

Use the exported React app in `Frontend-figma` and point it to the API:

```bash
./start_dev.ps1
```

This opens two terminals and starts both backend and frontend.

Or run from repo root with npm:

```bash
npm run dev:all
```

Stop both services:

```bash
./stop_dev.ps1
```

Or:

```bash
npm run stop:all
```

Manual mode:

```bash
cd "Frontend-figma"
npm install
npm run dev
```

Set API base URL if needed:

```bash
# PowerShell
$env:VITE_API_BASE_URL="http://localhost:8000"
npm run dev
```

The frontend calls:

- `POST /api/match` for running HUD vs OpenAI simulation
- `GET /api/leaderboard` for leaderboard views

Default local URLs:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:4173`

## API Keys

Set the keys for agents you want to run:

- `HUD_API_KEY` for `hud_model`
- `OPENAI_API_KEY` for `gpt4o`
- `ANTHROPIC_API_KEY` for `claude`
- `XAI_API_KEY` for `grok`
  Currently only using GPT (only one I pay for)

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
- scenario `historical_decision_step` (legacy compatibility) -
- scenario `summarize_decision` (legacy compatbility) -
- scenario `backtest_showdown`(legacy compatbility) -
  All scenarios with '-' are no longer being used --> idea has been shifted.

## Persistence

- `match_results.json`: full match history
- `leaderboard.json`: aggregate wins/losses and average performance

## Eval Task Sets (Pre-Training)

Generate scenario task sets for evaluation before training:

```bash
python scripts/generate_eval_task_sets.py
```

Outputs:

- `task_sets/eval/v1/trade_decision_step.jsonl`
- `task_sets/eval/v1/factor_weight_ranking.jsonl`
- `task_sets/eval/v1/post_trade_reflection.jsonl`
- `task_sets/eval/v1/manifest.json`

You can control sampling density:

```bash
python scripts/generate_eval_task_sets.py --stride 2 --lookback-days 20
```
