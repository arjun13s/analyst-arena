"""
Analyst Arena - HUD environment for model-vs-model financial analyst debate.
V1: Minimal, deterministic, demo-friendly.
Uses hud init structure: env.py at root, Dockerfile.hud, hud dev --stdio.
"""

from __future__ import annotations

import uuid
from typing import Literal

from hud import Environment

from data import (
    get_company_packet as _get_company_packet,
    get_earnings_packet as _get_earnings_packet,
    get_financials as _get_financials,
    get_price_chart as _get_price_chart,
    get_recent_news as _get_recent_news,
    SUPPORTED_TICKERS,
)
from rubrics import score_thesis, score_pm_decision

# --- In-memory state (V1) ---
_state: dict = {
    "submissions": {},
    "rebuttals": {},
    "final_ratings": [],
}

env = Environment(
    "analyst-arena",
    instructions=(
        "Analyst Arena: A financial analyst debate environment. "
        "Agents form theses, rebut opponents, and get scored on reasoning quality. "
        "Use get_company_packet, get_financials, get_recent_news, get_price_chart for research. "
        "Use submit_thesis, rebut_thesis, submit_final_rating to record your analysis."
    ),
)


def _next_id(prefix: str = "sub") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# --- Tools ---


@env.tool()
def get_company_packet(ticker: str) -> dict:
    """
    Get company overview, business model, key metrics, and valuation snapshot.
    V1: NVDA only. Returns static mock data.
    """
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        return {"error": f"Ticker {ticker} not supported in V1. Use NVDA."}
    data = _get_company_packet(ticker)
    return data if data else {"error": "No data"}


@env.tool()
def get_recent_news(ticker: str) -> list[dict]:
    """
    Get recent company news and filings summary.
    V1: Returns static mock data.
    """
    ticker = ticker.upper()
    return _get_recent_news(ticker)


@env.tool()
def get_financials(ticker: str, period: str = "TTM") -> dict:
    """
    Get income statement, balance sheet, and cash flow highlights.
    V1: Static mock. Period parameter ignored.
    """
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        return {"error": f"Ticker {ticker} not supported in V1. Use NVDA."}
    data = _get_financials(ticker, period)
    return data if data else {"error": "No data"}


@env.tool()
def get_price_chart(ticker: str, timeframe: str = "1Y") -> dict:
    """
    Get chart summary (text, not image) for the ticker.
    V1: Returns static summary.
    """
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        return {"error": f"Ticker {ticker} not supported in V1. Use NVDA."}
    data = _get_price_chart(ticker, timeframe)
    return data if data else {"error": "No data"}


@env.tool()
def get_earnings_packet(ticker: str) -> dict:
    """
    Get the latest earnings packet (results, guidance, commentary).
    V1: NVDA only. Use for earnings_reaction scenario.
    """
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        return {"error": f"Ticker {ticker} not supported in V1. Use NVDA."}
    data = _get_earnings_packet(ticker)
    return data if data else {"error": "No data"}


@env.tool()
def submit_thesis(
    ticker: str,
    stance: Literal["bull", "bear"],
    thesis_text: str,
) -> dict:
    """
    Store your opening thesis. Returns submission_id for rebuttals.
    """
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        return {"error": f"Ticker {ticker} not supported in V1. Use NVDA."}
    sub_id = _next_id("sub")
    _state["submissions"][sub_id] = {
        "ticker": ticker,
        "stance": stance,
        "thesis_text": thesis_text,
    }
    return {"submission_id": sub_id, "status": "submitted"}


@env.tool()
def rebut_thesis(opponent_submission_id: str, rebuttal_text: str) -> dict:
    """
    Respond directly to the opposing case. References opponent's submission_id.
    """
    if opponent_submission_id not in _state["submissions"]:
        return {"error": f"Unknown submission_id: {opponent_submission_id}"}
    _state["rebuttals"][opponent_submission_id] = {"rebuttal_text": rebuttal_text}
    return {"status": "rebuttal_submitted", "opponent_id": opponent_submission_id}


@env.tool()
def submit_final_rating(
    ticker: str,
    rating: Literal["buy", "hold", "sell"],
    target_price: float,
    rationale: str,
) -> dict:
    """
    Store your final verdict (rating, target price, rationale).
    """
    ticker = ticker.upper()
    if ticker not in SUPPORTED_TICKERS:
        return {"error": f"Ticker {ticker} not supported in V1. Use NVDA."}
    _state["final_ratings"].append({
        "ticker": ticker,
        "rating": rating,
        "target_price": target_price,
        "rationale": rationale,
    })
    return {"status": "rating_submitted"}


# --- Scenarios ---


@env.scenario("earnings_reaction")
async def earnings_reaction(ticker: str = "NVDA"):
    """
    Agent receives earnings packet and must form a bull or bear thesis.
    Use get_earnings_packet, get_company_packet, get_financials, get_price_chart.
    Submit via submit_thesis.
    """
    packet = _get_earnings_packet(ticker)
    if not packet:
        yield "Ticker not supported. Use NVDA."
        yield 0.0
        return

    prompt = f"""You are a financial analyst. Here is the {ticker} earnings packet:

{packet}

Your task:
1. Use get_company_packet, get_financials, get_price_chart as needed for context.
2. Form a clear bull or bear thesis.
3. Submit your thesis via submit_thesis(ticker="{ticker}", stance="bull" or "bear", thesis_text="...").

Be specific. Identify the core driver. Tie evidence to your conclusion. Avoid generic commentary."""

    answer = yield prompt

    # Score based on submissions
    subs = [s for s in _state["submissions"].values() if s["ticker"] == ticker]
    if not subs:
        yield 0.0
        return
    latest = subs[-1]
    score_result = score_thesis(latest["thesis_text"], rebuttal_text=None)
    yield score_result.total_score / 100.0


@env.scenario("analyst_debate")
async def analyst_debate(ticker: str = "NVDA", assigned_side: Literal["bull", "bear"] = "bear"):
    """
    Agent argues one side against a mock opponent. Must rebut the opponent's thesis.
    """
    packet = _get_company_packet(ticker)
    if not packet:
        yield "Ticker not supported. Use NVDA."
        yield 0.0
        return

    # Mock opponent thesis (opposite side)
    opponent_side = "bull" if assigned_side == "bear" else "bear"
    mock_opponent_thesis = (
        f"The {opponent_side} case: NVIDIA's data center growth is sustainable. "
        "Operating leverage and software mix support margin expansion. "
        "Valuation is justified by AI TAM and recurring revenue visibility."
    )

    prompt = f"""You are the {assigned_side.upper()} analyst in a debate on {ticker}.

Your opponent ({opponent_side}) has argued:
"{mock_opponent_thesis}"

Your task:
1. Use get_company_packet, get_financials, get_price_chart, get_recent_news for research.
2. Submit your opening thesis via submit_thesis(ticker="{ticker}", stance="{assigned_side}", thesis_text="...").
3. Rebut the opponent. You need their submission_id - for this scenario, use "mock_opponent" as the opponent_submission_id and call rebut_thesis(opponent_submission_id="mock_opponent", rebuttal_text="...").

Attack the weakest part of their case. Use evidence from the packet."""

    # Pre-create mock opponent submission for rebuttal target
    _state["submissions"]["mock_opponent"] = {
        "ticker": ticker,
        "stance": opponent_side,
        "thesis_text": mock_opponent_thesis,
    }

    answer = yield prompt

    # Score
    subs = [s for s in _state["submissions"].values() if s["ticker"] == ticker and s["stance"] == assigned_side]
    rebuttals = _state["rebuttals"].get("mock_opponent", {})
    rebuttal_text = rebuttals.get("rebuttal_text", "") if isinstance(rebuttals, dict) else ""

    if not subs:
        yield 0.0
        return
    latest = subs[-1]
    score_result = score_thesis(latest["thesis_text"], rebuttal_text=rebuttal_text)
    yield score_result.total_score / 100.0


@env.scenario("thesis_revision")
async def thesis_revision(ticker: str = "NVDA"):
    """
    Agent updates view after new news drops. Must revise thesis and submit final rating.
    """
    news = _get_recent_news(ticker)
    packet = _get_company_packet(ticker)
    if not packet:
        yield "Ticker not supported. Use NVDA."
        yield 0.0
        return

    news_text = "\n".join(
        f"- {n['date']}: {n['headline']} — {n['summary']}" for n in news[:3]
    )

    prompt = f"""New news has dropped for {ticker}:

{news_text}

Your task:
1. Review the news and existing context (get_company_packet, get_financials, get_recent_news).
2. Revise your view. Submit a revised thesis via submit_thesis if your view changed.
3. Submit your final rating via submit_final_rating(ticker="{ticker}", rating="buy"|"hold"|"sell", target_price=<float>, rationale="...").

Be explicit about what changed and why."""

    answer = yield prompt

    # Score based on final ratings
    ratings = [r for r in _state["final_ratings"] if r["ticker"] == ticker]
    if not ratings:
        yield 0.0
        return
    latest = ratings[-1]
    # Simple heuristic: rationale length and structure
    rationale_len = len(latest["rationale"])
    score = min(1.0, 0.3 + rationale_len / 500)
    yield score


@env.scenario("pm_decision_round")
async def pm_decision_round(ticker: str = "NVDA"):
    """
    Judge/PM evaluates two theses and decides which was stronger.
    Agent receives both theses and must pick a winner with rationale.
    """
    subs = [s for s in _state["submissions"].values() if s["ticker"] == ticker]
    if len(subs) < 2:
        prompt = f"""Not enough submissions for {ticker}. Run earnings_reaction or analyst_debate first to create theses.
Current submissions: {len(subs)}"""
        yield prompt
        yield 0.0
        return

    thesis_a = subs[-2]
    thesis_b = subs[-1]

    prompt = f"""You are the PM/judge. Two analysts have submitted theses on {ticker}:

--- THESIS A ({thesis_a['stance'].upper()}) ---
{thesis_a['thesis_text']}

--- THESIS B ({thesis_b['stance'].upper()}) ---
{thesis_b['thesis_text']}

Your task: Decide which thesis was stronger. Use submit_final_rating to record your decision:
- rating: "buy" if Thesis A wins, "hold" if tie, "sell" if Thesis B wins (we use this as a proxy for winner)
- target_price: 1.0 for A, 0.5 for tie, 0.0 for B
- rationale: Explain why. Focus on thesis quality, evidence grounding, financial reasoning, valuation rigor.

Submit via submit_final_rating(ticker="{ticker}", rating="buy"|"hold"|"sell", target_price=1.0|0.5|0.0, rationale="...")."""

    answer = yield prompt

    # Score the judge's rationale
    ratings = [r for r in _state["final_ratings"] if r["ticker"] == ticker]
    if not ratings:
        yield 0.0
        return
    latest = ratings[-1]
    result = score_pm_decision(
        thesis_a["thesis_text"],
        thesis_b["thesis_text"],
        winner=latest["rating"],
        rationale=latest["rationale"],
    )
    # Reward for providing rationale
    rationale_score = min(1.0, len(latest["rationale"]) / 300)
    yield rationale_score
