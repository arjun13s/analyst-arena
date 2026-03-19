# Analyst Arena

Model-vs-model financial analyst debate demo for HUD. Different models compete on the same stock; a judge scores who performed better.

**V1 scope:** Minimal, deterministic, demo-friendly. Single ticker (NVDA), static mock data.

## Quick Start

### 1. Install

```bash
cd analyst_arena
pip install -e .
# or
uv pip install -e .
```

### 2. Run locally with HUD

From the repo root:

```bash
hud dev env:env
```

Or with hot-reload:

```bash
hud dev env:env -w env.py -w data.py -w rubrics.py
```

This starts the MCP server at `http://localhost:8765/mcp`.

### 3. Connect Cursor via MCP

In Cursor → Settings → MCP, add:

```json
{
  "mcpServers": {
    "analyst-arena": {
      "url": "http://localhost:8765/mcp"
    }
  }
}
```

Restart Cursor or reload MCP. Your agent can now call the Analyst Arena tools.

### 4. Deploy to HUD

**Prerequisites:** Get an API key at [hud.ai/settings](https://hud.ai/settings), then:

```bash
hud set HUD_API_KEY=your-api-key
```

**Deploy from the `analyst_arena` directory:**

```bash
cd analyst_arena
hud deploy .
```

This will:
1. Package your project (respects `.dockerignore`)
2. Build remotely on HUD's infrastructure
3. Deploy to the platform
4. Create `.hud/deploy.json` to link future rebuilds

**Rebuild:** Run `hud deploy .` again; the version auto-increments (0.1.0 → 0.1.1).

**GitHub auto-deploy (recommended for teams):**
1. Push your repo to GitHub
2. Go to [hud.ai](https://hud.ai) → New → Environment
3. Connect the repo and install the HUD GitHub App
4. Rebuilds run automatically on every push

## Tools

| Tool | Description |
|------|-------------|
| `get_company_packet(ticker)` | Overview, business model, key metrics, valuation |
| `get_recent_news(ticker)` | Recent news and filings summary |
| `get_financials(ticker, period)` | Income statement, balance sheet, cash flow |
| `get_price_chart(ticker, timeframe)` | Chart summary (text) |
| `get_earnings_packet(ticker)` | Latest earnings results and guidance |
| `submit_thesis(ticker, stance, thesis_text)` | Store opening thesis |
| `rebut_thesis(opponent_submission_id, rebuttal_text)` | Rebut opposing case |
| `submit_final_rating(ticker, rating, target_price, rationale)` | Store final verdict |

## Scenarios

| Scenario | Description |
|----------|-------------|
| `earnings_reaction` | Agent gets earnings packet, forms bull/bear thesis |
| `analyst_debate` | Agent argues one side vs mock opponent, must rebut |
| `thesis_revision` | Agent revises view after new news, submits final rating |
| `pm_decision_round` | Judge evaluates two theses, picks winner |

## Scoring

Base: 100 points across 7 categories (thesis quality, evidence grounding, financial reasoning, valuation rigor, risk recognition, rebuttal strength, calibration). Penalties for hallucination, inconsistency, genericness. V1 uses heuristic scoring; replace with LLM judge for production.

## File Structure

```
analyst-arena/           # Repo root (hud init style)
├── env.py               # Environment, tools, scenarios
├── data.py              # Static mock data (NVDA)
├── rubrics.py           # Scoring helper
├── Dockerfile.hud       # Container config (uses hud dev --stdio)
├── pyproject.toml
└── README.md
```
