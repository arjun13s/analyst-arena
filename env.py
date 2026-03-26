from __future__ import annotations

import json
from datetime import date
from typing import Any

from hud import Environment

from analyst_arena.models import (
    ActionDecision,
    FactorWeightRankingResult,
    HistoricalInfoBundle,
    PostTradeReflectionResult,
)
from analyst_arena.scoring.scenario_eval import (
    evaluate_factor_weight_ranking,
    evaluate_post_trade_reflection,
    evaluate_trade_decision_step,
    evaluation_to_reward,
)
from analyst_arena.storage.leaderboard import load_leaderboard
from data import (
    SUPPORTED_TICKERS,
    get_candidate_factors,
    get_company_packet as _get_company_packet,
    get_earnings_packet as _get_earnings_packet,
    get_financials as _get_financials,
    get_forward_return_pct,
    get_forward_window,
    get_historical_info as _get_historical_info,
    get_info as _get_info,
    get_market_regime_label,
    get_price_chart as _get_price_chart,
    get_recent_news as _get_recent_news,
    get_stock_archetype,
)


env = Environment(
    "analyst-arena",
    instructions=(
        "Analyst Arena is a no-lookahead trading-judgment training environment. "
        "Optimize for decision quality under uncertainty: direction, calibration, sizing, factor relevance, and process quality. "
        "Return structured JSON only."
    ),
)

CURATED_TICKERS = tuple(SUPPORTED_TICKERS)


def _normalize_ticker(ticker: str) -> str:
    normalized = ticker.upper().strip()
    if normalized not in SUPPORTED_TICKERS:
        raise ValueError(f"Unsupported ticker '{ticker}'. Use one of: {', '.join(SUPPORTED_TICKERS)}")
    return normalized


def _parse_json_answer(answer: Any) -> dict[str, Any]:
    if isinstance(answer, dict):
        return dict(answer)
    if not isinstance(answer, str):
        return {"content": str(answer)}

    text = answer.strip()

    # Try direct parse first
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return dict(payload)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    import re
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        try:
            payload = json.loads(fence_match.group(1).strip())
            if isinstance(payload, dict):
                return dict(payload)
        except json.JSONDecodeError:
            pass

    # Extract the first { ... } block from surrounding prose
    brace_start = text.find("{")
    if brace_start != -1:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        payload = json.loads(text[brace_start : i + 1])
                        if isinstance(payload, dict):
                            return dict(payload)
                    except json.JSONDecodeError:
                        pass
                    break

    return {"content": text}


def _reward_for_keys(answer: Any, required_keys: tuple[str, ...]) -> float:
    payload = _parse_json_answer(answer)
    present = sum(1 for key in required_keys if payload.get(key) not in (None, "", [], {}))
    return round(max(0.0, min(1.0, present / max(1, len(required_keys)))), 4)


def _coerce_horizon_days(horizon: str) -> int:
    normalized = (horizon or "short").lower().strip()
    if normalized == "medium":
        return 20
    if normalized == "long":
        return 40
    return 5


def _normalize_size_fields(
    payload: dict[str, Any],
    portfolio_state: dict[str, Any],
    info_bundle: dict[str, Any],
) -> dict[str, Any]:
    """
    Normalize decision sizing so scenario outputs remain fraction-based.
    If the model accidentally returns share counts (>1), convert to fraction:
      - BUY: shares * price / cash
      - SELL: shares / current_shares
    """
    normalized = dict(payload)
    raw_size = payload.get("size_pct", payload.get("position_size", 0.0))
    try:
        numeric_size = float(raw_size)
    except (TypeError, ValueError):
        numeric_size = 0.0

    # Already a valid fraction.
    if 0.0 <= numeric_size <= 1.0:
        normalized["size_pct"] = numeric_size
        normalized["position_size"] = numeric_size
        return normalized

    action = str(payload.get("action", "HOLD")).upper()
    summary = dict(info_bundle.get("summary_stats", {}))
    last_close = float(summary.get("last_close", 0.0))
    cash = float(portfolio_state.get("cash", 0.0))
    held_shares = float(portfolio_state.get("shares", 0.0))

    fraction = 0.0
    if action == "BUY":
        # Interpret numeric_size as share count and map to cash deployment fraction.
        fraction = ((numeric_size * last_close) / cash) if (last_close > 0 and cash > 0) else 0.0
    elif action == "SELL":
        # Interpret numeric_size as share count and map to share reduction fraction.
        fraction = (numeric_size / held_shares) if held_shares > 0 else 0.0

    fraction = max(0.0, min(1.0, fraction))
    normalized["size_pct"] = fraction
    normalized["position_size"] = fraction
    metadata = dict(normalized.get("metadata", {}))
    metadata["size_normalized_from_shares"] = numeric_size
    normalized["metadata"] = metadata
    return normalized


def _normalize_reflection_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Align reflection outputs with scorer-expected vocab to avoid silent score loss.
    """
    normalized = dict(payload)

    def _norm_text(value: Any) -> str:
        return str(value or "").strip().lower().replace("_", " ").replace("-", " ")

    # decision_quality: scorer rewards good/mixed/bad(+strong/weak aliases)
    dq = _norm_text(normalized.get("decision_quality", ""))
    if dq in {"neutral"}:
        normalized["decision_quality"] = "mixed"
    elif dq in {"strong", "good", "mixed", "bad", "weak"}:
        normalized["decision_quality"] = dq

    # process_quality: prompt/model may emit numeric or alternate labels; scorer expects text buckets.
    pq_raw = normalized.get("process_quality", "")
    pq_num: float | None = None
    try:
        pq_num = float(pq_raw)
    except (TypeError, ValueError):
        pq_num = None
    if pq_num is not None:
        normalized["process_quality"] = "good" if pq_num >= 0.67 else "mixed" if pq_num >= 0.4 else "weak"
    else:
        pq = _norm_text(pq_raw)
        if pq in {"poor", "low", "weak"}:
            normalized["process_quality"] = "weak"
        elif pq in {"ok", "average", "neutral"}:
            normalized["process_quality"] = "mixed"
        elif pq in {"good", "strong", "mixed", "bad", "weak"}:
            normalized["process_quality"] = pq

    # confidence_assessment: scorer looks for calibrated/appropriate/reasonable or over/underconfident language.
    ca = _norm_text(normalized.get("confidence_assessment", ""))
    if ca in {"well calibrated", "wellcalibrated"}:
        normalized["confidence_assessment"] = "calibrated"
    elif ca in {"too high", "high", "overconfident"}:
        normalized["confidence_assessment"] = "overconfident"
    elif ca in {"too low", "low", "underconfident"}:
        normalized["confidence_assessment"] = "underconfident"

    # size_assessment: scorer checks for tokens "too large"/"too small" (with spaces).
    sa = _norm_text(normalized.get("size_assessment", ""))
    if sa in {"too large", "oversized"}:
        normalized["size_assessment"] = "too large"
    elif sa in {"too small", "undersized"}:
        normalized["size_assessment"] = "too small"
    elif sa in {"appropriate", "reasonable", "right sized", "right-sized"}:
        normalized["size_assessment"] = "appropriate"

    return normalized


def _build_bundle(ticker: str, as_of_date: str, lookback_days: int = 20) -> dict[str, Any]:
    bundle = _get_historical_info(_normalize_ticker(ticker), as_of_date, lookback_days=lookback_days)
    if not bundle.get("candidate_factors"):
        bundle["candidate_factors"] = get_candidate_factors(ticker)
    if not bundle.get("stock_archetype"):
        bundle["stock_archetype"] = get_stock_archetype(ticker)
    if not bundle.get("market_regime"):
        bundle["market_regime"] = get_market_regime_label(ticker, bundle["as_of_date"])
    return bundle


@env.tool()
def get_info(ticker: str) -> dict[str, Any]:
    return _get_info(_normalize_ticker(ticker))


@env.tool()
def get_historical_info(ticker: str, as_of_date: str, lookback_days: int = 20) -> dict[str, Any]:
    return _build_bundle(_normalize_ticker(ticker), as_of_date, lookback_days=lookback_days)


@env.tool()
def get_company_packet(ticker: str) -> dict[str, Any]:
    return _get_company_packet(_normalize_ticker(ticker))


@env.tool()
def get_recent_news(ticker: str, as_of_date: str | None = None) -> list[dict[str, Any]]:
    from datetime import date as _date
    all_news = _get_recent_news(_normalize_ticker(ticker))
    if as_of_date:
        cutoff = _date.fromisoformat(as_of_date)
        return [n for n in all_news if _date.fromisoformat(str(n["date"])) <= cutoff]
    return all_news


@env.tool()
def get_financials(ticker: str, period: str = "TTM") -> dict[str, Any]:
    return _get_financials(_normalize_ticker(ticker), period=period)


@env.tool()
def get_price_chart(ticker: str, timeframe: str = "3M") -> dict[str, Any]:
    return _get_price_chart(_normalize_ticker(ticker), timeframe=timeframe)


@env.tool()
def get_earnings_packet(ticker: str) -> dict[str, Any]:
    return _get_earnings_packet(_normalize_ticker(ticker))


@env.tool()
def reason_to_trade(
    ticker: str,
    as_of_date: str,
    portfolio_state: dict[str, Any],
    lookback_days: int = 20,
) -> dict[str, Any]:
    bundle = _build_bundle(ticker, as_of_date, lookback_days=lookback_days)
    stats = bundle.get("summary_stats", {})
    ret_5d = float(stats.get("return_5d_pct", 0.0))
    ret_20d = float(stats.get("return_20d_pct", 0.0))
    cash = float(portfolio_state.get("cash", 0.0))
    shares = float(portfolio_state.get("shares", 0.0))

    if ret_5d > 2.0 and cash > 1.0:
        action, size_pct = "BUY", 0.2
        rationale = "Recent momentum is positive and cash is available."
    elif ret_20d < -2.0 and shares > 0:
        action, size_pct = "SELL", 0.3
        rationale = "Trend deterioration suggests reducing exposure."
    else:
        action, size_pct = "HOLD", 0.0
        rationale = "Signal quality is mixed and edge is weak."

    return {
        "as_of_date": bundle["as_of_date"],
        "action": action,
        "size_pct": size_pct,
        "position_size": size_pct,
        "confidence": 0.62,
        "horizon": "short",
        "top_reasons": ["momentum_5d", "momentum_20d"],
        "top_risks": ["event_risk"],
        "invalidation_condition": "If 5-day momentum flips negative and volatility spikes.",
        "factor_scores": {
            "momentum_5d": max(0.0, min(1.0, abs(ret_5d) / 5.0)),
            "momentum_20d": max(0.0, min(1.0, abs(ret_20d) / 8.0)),
        },
        "rationale": rationale,
    }


@env.tool()
def summarize_position(decision: dict[str, Any]) -> dict[str, Any]:
    action = str(decision.get("action", "HOLD")).upper()
    size_pct = float(decision.get("size_pct", decision.get("position_size", 0.0)))
    rationale = str(decision.get("rationale", "No rationale provided")).strip()
    summary = f"{action} {size_pct:.0%} allocation decision. {rationale}"
    return {"summary": summary}


@env.tool()
def compute_portfolio_snapshot(cash: float, shares: float, current_price: float) -> dict[str, Any]:
    market_value = shares * current_price
    total_equity = cash + market_value
    return {
        "cash": round(cash, 4),
        "shares": round(shares, 8),
        "market_value": round(market_value, 4),
        "total_equity": round(total_equity, 4),
        "last_price": round(current_price, 4),
    }


@env.tool()
def get_leaderboard(limit: int = 10) -> list[dict[str, Any]]:
    entries = load_leaderboard()[: max(limit, 0)]
    return [entry.to_dict() for entry in entries]


@env.scenario("trade_decision_step")
async def trade_decision_step(
    ticker: str = "NVDA",
    as_of_date: str | None = None,
    portfolio_state: dict[str, Any] | None = None,
    lookback_days: int = 20,
):
    portfolio_state = portfolio_state or {"cash": 100000.0, "shares": 0.0}
    as_of = as_of_date or date.today().isoformat()
    bundle = _build_bundle(ticker, as_of, lookback_days=lookback_days)
    prompt = (
        f"You are trading {ticker.upper()} at {as_of}.\n"
        f"Portfolio: {json.dumps(portfolio_state)}\n\n"
        "Use the available tools to research this stock before deciding. You should:\n"
        f"1. Call get_historical_info(ticker=\"{ticker.upper()}\", as_of_date=\"{as_of}\", lookback_days={lookback_days}) for price history and stats\n"
        f"2. Call get_recent_news(ticker=\"{ticker.upper()}\", as_of_date=\"{as_of}\") for events up to this date\n"
        f"3. Call get_financials(ticker=\"{ticker.upper()}\") for fundamental data\n"
        "4. Use any other tools you think are helpful\n\n"
        "After researching, return ONLY a single JSON object (no markdown, no commentary) with these keys:\n"
        "action, confidence, position_size, size_pct, horizon, top_reasons, top_risks, "
        "invalidation_condition, factor_scores, rationale.\n"
        "Rules:\n"
        "- action: BUY, SELL, or HOLD\n"
        "- confidence: float 0 to 1 (how sure you are)\n"
        "- size_pct / position_size: float 0 to 1 fraction only (never return raw share count)\n"
        "- horizon: short, medium, or long\n"
        "- top_reasons: list of 2-4 factor names from candidate_factors that support your action\n"
        "- top_risks: list of 1-3 risk factors\n"
        "- invalidation_condition: one sentence describing when this trade thesis breaks\n"
        "- factor_scores: dict mapping each candidate factor to a relevance score 0-1\n"
        "- rationale: one concise sentence explaining the trade\n"
        "IMPORTANT: Do NOT use any information after this date. Do NOT output reasoning outside the JSON.\n"
    )
    answer = yield prompt
    payload = _parse_json_answer(answer)
    payload = _normalize_size_fields(payload, portfolio_state, bundle)
    decision = ActionDecision.from_dict(payload, default_as_of_date=date.fromisoformat(bundle["as_of_date"]))
    forward_return_pct = get_forward_return_pct(
        ticker,
        bundle["as_of_date"],
        horizon_days=_coerce_horizon_days(decision.horizon),
    )
    evaluation = evaluate_trade_decision_step(decision, HistoricalInfoBundle.from_dict(bundle), forward_return_pct)
    yield evaluation_to_reward(evaluation)


@env.scenario("factor_weight_ranking")
async def factor_weight_ranking(
    ticker: str = "NVDA",
    as_of_date: str | None = None,
    horizon: str = "short",
    lookback_days: int = 20,
):
    as_of = as_of_date or date.today().isoformat()
    bundle = _build_bundle(ticker, as_of, lookback_days=lookback_days)
    prompt = (
        f"Rank the most relevant factors for trading {ticker.upper()} at {as_of} on a {horizon} horizon.\n\n"
        "Use the available tools to research before ranking. You should:\n"
        f"1. Call get_historical_info(ticker=\"{ticker.upper()}\", as_of_date=\"{as_of}\", lookback_days={lookback_days}) for price history, stats, and candidate_factors\n"
        f"2. Call get_recent_news(ticker=\"{ticker.upper()}\", as_of_date=\"{as_of}\") for events\n"
        f"3. Call get_financials(ticker=\"{ticker.upper()}\") for fundamentals\n"
        "4. Use any other tools you think are helpful\n\n"
        "After researching, return ONLY a single JSON object (no markdown, no commentary) with these keys:\n"
        "ranked_factors, factor_weights, decisive_metrics, noisy_metrics, stock_archetype, "
        "market_regime, horizon, rationale.\n"
        "Rules:\n"
        "- ranked_factors: list of factor names from candidate_factors, ordered by importance (most important first)\n"
        "- factor_weights: dict mapping each candidate factor to a non-negative weight (should sum roughly to 1)\n"
        "- decisive_metrics: list of 2-4 factors that matter most in the current regime/archetype\n"
        "- noisy_metrics: list of 1-3 factors that are unreliable right now\n"
        "- stock_archetype: string label for the stock type\n"
        "- market_regime: string label for current market condition\n"
        "- horizon: short, medium, or long\n"
        "- rationale: one concise sentence explaining the ranking logic\n"
        "Scoring optimization hints (follow these unless data strongly contradicts):\n"
        "- Include ALL candidate_factors in both ranked_factors and factor_weights.\n"
        "- Normalize factor_weights to sum to 1.0 exactly.\n"
        "- In risk_on_trend: prioritize momentum_5d, momentum_20d, revenue_growth_yoy.\n"
        "- In risk_off_drawdown/high_volatility: prioritize event_risk and volatility_20d.\n"
        "- In range_bound: keep a balanced mix; avoid over-weighting momentum_20d when return_20d is near zero.\n"
        "- For high_growth/platform_growth archetypes: keep revenue_growth_yoy and fcf_margin in top half.\n"
        "- For mature_quality archetypes: keep gross_margin and fcf_margin in top half.\n"
        "- Mark low-signal factors as noisy_metrics; common low-signal candidates are volume_trend_5d and event_risk when no recent events.\n"
        "- If uncertain, use this neutral fallback order: momentum_5d, gross_margin, revenue_growth_yoy, fcf_margin, valuation_vs_growth, momentum_20d, volatility_20d, volume_trend_5d, event_risk.\n"
        "IMPORTANT: Do NOT output reasoning, analysis, or explanation outside the JSON.\n"
    )
    answer = yield prompt
    payload = _parse_json_answer(answer)
    payload.setdefault("as_of_date", bundle["as_of_date"])
    payload.setdefault("horizon", horizon)
    payload.setdefault("stock_archetype", bundle["stock_archetype"])
    payload.setdefault("market_regime", bundle["market_regime"])
    ranking = FactorWeightRankingResult.from_dict(payload, default_as_of_date=date.fromisoformat(bundle["as_of_date"]))
    forward_return_pct = get_forward_return_pct(
        ticker,
        bundle["as_of_date"],
        horizon_days=_coerce_horizon_days(horizon),
    )
    evaluation = evaluate_factor_weight_ranking(ranking, HistoricalInfoBundle.from_dict(bundle), forward_return_pct)
    yield evaluation_to_reward(evaluation)


@env.scenario("post_trade_reflection")
async def post_trade_reflection(
    ticker: str = "NVDA",
    as_of_date: str | None = None,
    original_decision: dict[str, Any] | None = None,
    future_outcome: dict[str, Any] | None = None,
    lookback_days: int = 20,
):
    as_of = as_of_date or date.today().isoformat()
    bundle = _build_bundle(ticker, as_of, lookback_days=lookback_days)
    decision_payload = dict(original_decision or reason_to_trade(ticker, bundle["as_of_date"], {"cash": 100000.0, "shares": 0.0}))
    decision = ActionDecision.from_dict(decision_payload, default_as_of_date=date.fromisoformat(bundle["as_of_date"]))
    horizon_days = _coerce_horizon_days(decision.horizon)
    outcome = dict(future_outcome or {})
    outcome.setdefault("forward_return_pct", get_forward_return_pct(ticker, bundle["as_of_date"], horizon_days=horizon_days))
    outcome.setdefault("forward_path", get_forward_window(ticker, bundle["as_of_date"], horizon_days=horizon_days))
    outcome.setdefault("benchmark_return_pct", 0.0)

    prompt = (
        f"Reflect on a trade made on {ticker.upper()} at {as_of}. Separate process quality from outcome luck.\n\n"
        f"Original decision:\n{json.dumps(decision.to_dict(), indent=2)}\n\n"
        f"Revealed outcome:\n{json.dumps(outcome, indent=2)}\n\n"
        "You may use tools to look up context about what was happening at decision time:\n"
        f"- Call get_historical_info(ticker=\"{ticker.upper()}\", as_of_date=\"{as_of}\", lookback_days={lookback_days}) for the price/stats context the trader had\n"
        f"- Call get_recent_news(ticker=\"{ticker.upper()}\", as_of_date=\"{as_of}\") for events known at the time\n"
        "- Use any other tools you think are helpful\n\n"
        "After reviewing, return ONLY a single JSON object (no markdown, no commentary) with these keys:\n"
        "decision_quality, process_quality, luck_vs_skill, confidence_assessment, size_assessment, "
        "signals_helped, signals_misled, next_time_changes, outcome_summary, hindsight_flags.\n"
        "Rules:\n"
        "- decision_quality: string, one of 'good', 'mixed', 'bad'\n"
        "- process_quality: string, one of 'good', 'mixed', 'weak'\n"
        "- luck_vs_skill: string, one of 'mostly_luck', 'mixed', 'mostly_skill'\n"
        "- confidence_assessment: string, one of 'calibrated', 'overconfident', 'underconfident'\n"
        "- size_assessment: string, one of 'appropriate', 'too large', 'too small'\n"
        "- signals_helped: list of 1-3 factor names that correctly predicted the outcome\n"
        "- signals_misled: list of 0-3 factor names that pointed the wrong way\n"
        "- next_time_changes: list of 1-3 concrete adjustments for future trades\n"
        "- outcome_summary: one concise sentence summarizing what happened\n"
        "- hindsight_flags: list of 0-3 statements where you might be rationalizing from hindsight\n"
        "IMPORTANT: Do NOT claim certainty from hindsight. Avoid words like 'obvious', 'always', 'should have known', 'guaranteed'. Do NOT output reasoning outside the JSON.\n"
    )
    answer = yield prompt
    payload = _parse_json_answer(answer)
    payload = _normalize_reflection_payload(payload)
    payload.setdefault("as_of_date", bundle["as_of_date"])
    reflection = PostTradeReflectionResult.from_dict(payload, default_as_of_date=date.fromisoformat(bundle["as_of_date"]))
    evaluation = evaluate_post_trade_reflection(reflection, decision, float(outcome["forward_return_pct"]))
    yield evaluation_to_reward(evaluation)


@env.scenario("historical_decision_step")
async def historical_decision_step(
    ticker: str = "NVDA",
    as_of_date: str | None = None,
    portfolio_state: dict[str, Any] | None = None,
):
    portfolio_state = portfolio_state or {"cash": 100000.0, "shares": 0.0}
    as_of = as_of_date or date.today().isoformat()
    bundle = _build_bundle(ticker, as_of, lookback_days=20)
    prompt = (
        f"Legacy compatibility decision for {ticker.upper()} at {bundle['as_of_date']}.\n"
        "Return JSON keys: action, size_pct, confidence, rationale.\n"
        f"Portfolio:\n{json.dumps(portfolio_state, indent=2)}\n"
        f"Historical bundle:\n{json.dumps(bundle, indent=2)}"
    )
    answer = yield prompt
    payload = _parse_json_answer(answer)
    decision = ActionDecision.from_dict(payload, default_as_of_date=date.fromisoformat(bundle["as_of_date"]))
    forward_return_pct = get_forward_return_pct(ticker, bundle["as_of_date"], horizon_days=5)
    evaluation = evaluate_trade_decision_step(decision, HistoricalInfoBundle.from_dict(bundle), forward_return_pct)
    # Keep this scenario narrow and backward compatible.
    yield evaluation_to_reward(evaluation) * 0.9


@env.scenario("summarize_decision")
async def summarize_decision(decision: dict[str, Any] | None = None):
    prompt = (
        "Summarize the decision in one sentence for demo playback.\n"
        "Return JSON only with key: summary.\n"
        f"Decision:\n{json.dumps(decision or {}, indent=2)}"
    )
    answer = yield prompt
    yield _reward_for_keys(answer, ("summary",))


@env.scenario("backtest_showdown")
async def backtest_showdown(match_result: dict[str, Any] | None = None):
    prompt = (
        "Summarize the backtest showdown result and explain the winner in one short paragraph.\n"
        "Return JSON only with key: summary.\n"
        f"Match result:\n{json.dumps(match_result or {}, indent=2)}"
    )
    answer = yield prompt
    yield _reward_for_keys(answer, ("summary",))


__all__ = ["env"]
