"""
Deterministic historical market data for Analyst Arena backtest showdown.

This module intentionally serves self-contained data to make no-lookahead
simulation deterministic and reproducible across environments.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from math import cos, sin
from typing import Any


SUPPORTED_TICKERS = ("NVDA", "AAPL", "GOOGL")
DEFAULT_BACKTEST_MONTHS = 1
BACKTEST_STEPS = 10
BACKTEST_POINTS = BACKTEST_STEPS + 1
WINDOW_START = date(2025, 1, 2)
WINDOW_END = date(2025, 3, 31)


TickerParams = dict[str, float]


_TICKER_CONFIG: dict[str, TickerParams] = {
    "NVDA": {"start": 132.0, "drift": 0.0021, "vol": 0.028, "volume": 52_000_000, "seed": 1.7},
    "AAPL": {"start": 198.0, "drift": 0.0009, "vol": 0.015, "volume": 71_000_000, "seed": 2.9},
    "GOOGL": {"start": 165.0, "drift": 0.0012, "vol": 0.017, "volume": 36_000_000, "seed": 4.1},
}


_COMPANY_CONTEXT: dict[str, dict[str, Any]] = {
    "NVDA": {
        "name": "NVIDIA Corporation",
        "company_overview": "GPU and accelerated computing leader with AI data-center concentration.",
        "business_model": "High-margin silicon and software stack monetized through enterprise AI demand.",
        "financial_context": {
            "revenue_growth_yoy": 0.62,
            "gross_margin": 0.73,
            "fcf_margin": 0.46,
        },
    },
    "AAPL": {
        "name": "Apple Inc.",
        "company_overview": "Consumer hardware + services ecosystem with durable cash generation.",
        "business_model": "Installed-base monetization through devices, subscriptions, and platform lock-in.",
        "financial_context": {
            "revenue_growth_yoy": 0.04,
            "gross_margin": 0.45,
            "fcf_margin": 0.28,
        },
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "company_overview": "Search/ads and cloud platform scaling with AI product integration.",
        "business_model": "Ad monetization + cloud subscriptions with data and distribution advantages.",
        "financial_context": {
            "revenue_growth_yoy": 0.11,
            "gross_margin": 0.58,
            "fcf_margin": 0.27,
        },
    },
}

_STOCK_ARCHETYPE: dict[str, str] = {
    "NVDA": "high_growth",
    "AAPL": "mature_quality",
    "GOOGL": "platform_growth",
}

_BASE_CANDIDATE_FACTORS: tuple[str, ...] = (
    "momentum_5d",
    "momentum_20d",
    "volatility_20d",
    "volume_trend_5d",
    "revenue_growth_yoy",
    "gross_margin",
    "fcf_margin",
    "valuation_vs_growth",
)


_EVENTS: dict[str, list[dict[str, Any]]] = {
    "NVDA": [
        {"date": "2025-01-27", "type": "news", "headline": "AI demand checks remain strong across hyperscalers."},
        {"date": "2025-02-26", "type": "earnings", "headline": "Revenue beat and guidance above consensus."},
        {"date": "2025-03-17", "type": "news", "headline": "Supply-chain note flags near-term GPU allocation tightness."},
    ],
    "AAPL": [
        {"date": "2025-01-30", "type": "news", "headline": "Services momentum offsets softer hardware mix."},
        {"date": "2025-02-21", "type": "news", "headline": "Regulatory headline pressure on app distribution persists."},
        {"date": "2025-03-12", "type": "news", "headline": "AI feature rollout cadence viewed as a catalyst."},
    ],
    "GOOGL": [
        {"date": "2025-01-24", "type": "news", "headline": "Cloud contract wins support growth visibility."},
        {"date": "2025-02-05", "type": "earnings", "headline": "Cloud margin expansion beats expectations."},
        {"date": "2025-03-10", "type": "news", "headline": "Ad-tech regulatory updates create headline volatility."},
    ],
}


def _is_business_day(day: date) -> bool:
    return day.weekday() < 5


def _business_days(start: date, end: date) -> list[date]:
    days: list[date] = []
    cursor = start
    while cursor <= end:
        if _is_business_day(cursor):
            days.append(cursor)
        cursor += timedelta(days=1)
    return days


def _safe_round(value: float, places: int = 2) -> float:
    return round(float(value), places)


def _generate_price_history(ticker: str) -> list[dict[str, Any]]:
    config = _TICKER_CONFIG[ticker]
    days = _business_days(WINDOW_START, WINDOW_END)
    candles: list[dict[str, Any]] = []
    prev_close = config["start"]

    for index, day in enumerate(days):
        cycle = index / 6.0
        trend = config["drift"] * (1 + 0.25 * sin(cycle * 0.8 + config["seed"]))
        noise = config["vol"] * sin(cycle + config["seed"]) * 0.35
        open_px = prev_close * (1.0 + config["vol"] * 0.08 * cos(cycle * 0.7 + config["seed"]))
        close_px = open_px * (1.0 + trend + noise)
        intraday_range = abs(config["vol"] * (0.55 + 0.25 * cos(cycle + config["seed"])))
        high_px = max(open_px, close_px) * (1.0 + intraday_range)
        low_px = min(open_px, close_px) * (1.0 - intraday_range)
        volume_mult = 1.0 + 0.25 * sin(cycle * 1.4 + config["seed"])
        volume = int(config["volume"] * max(0.45, volume_mult))

        candle = {
            "date": day.isoformat(),
            "open": _safe_round(open_px),
            "high": _safe_round(high_px),
            "low": _safe_round(low_px),
            "close": _safe_round(close_px),
            "volume": volume,
        }
        candles.append(candle)
        prev_close = close_px

    return candles


_PRICE_HISTORY: dict[str, list[dict[str, Any]]] = {
    ticker: _generate_price_history(ticker) for ticker in SUPPORTED_TICKERS
}


def _find_index_for_date(history: list[dict[str, Any]], as_of_date: date) -> int:
    idx = -1
    for i, row in enumerate(history):
        row_date = date.fromisoformat(str(row["date"]))
        if row_date <= as_of_date:
            idx = i
        else:
            break
    return idx


def _compute_summary_stats(history: list[dict[str, Any]]) -> dict[str, float]:
    if not history:
        return {
            "last_close": 0.0,
            "avg_volume_5d": 0.0,
            "return_5d_pct": 0.0,
            "return_20d_pct": 0.0,
            "volatility_20d_pct": 0.0,
        }

    closes = [float(item["close"]) for item in history]
    volumes = [float(item["volume"]) for item in history]
    last_close = closes[-1]

    def _pct_change(period: int) -> float:
        if len(closes) <= period:
            return 0.0
        base = closes[-(period + 1)]
        if base == 0:
            return 0.0
        return ((closes[-1] / base) - 1.0) * 100.0

    def _avg(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    returns_20d = []
    for i in range(max(1, len(closes) - 20), len(closes)):
        prev = closes[i - 1]
        returns_20d.append((closes[i] / prev - 1.0) * 100.0 if prev else 0.0)
    avg_ret = _avg(returns_20d)
    variance = _avg([(ret - avg_ret) ** 2 for ret in returns_20d]) if returns_20d else 0.0
    volatility = variance ** 0.5

    return {
        "last_close": _safe_round(last_close, 4),
        "avg_volume_5d": _safe_round(_avg(volumes[-5:]), 2),
        "return_5d_pct": _safe_round(_pct_change(5), 3),
        "return_20d_pct": _safe_round(_pct_change(20), 3),
        "volatility_20d_pct": _safe_round(volatility, 3),
    }


def _filter_events(ticker: str, as_of_date: date, lookback_days: int = 45) -> list[dict[str, Any]]:
    events = _EVENTS.get(ticker, [])
    window_start = as_of_date - timedelta(days=lookback_days)
    filtered: list[dict[str, Any]] = []
    for event in events:
        event_date = date.fromisoformat(str(event["date"]))
        if window_start <= event_date <= as_of_date:
            filtered.append(event)
    return filtered


def _normalize_ticker(ticker: str) -> str:
    normalized = str(ticker).upper().strip()
    if normalized not in SUPPORTED_TICKERS:
        raise ValueError(f"Unsupported ticker '{ticker}'. Use one of: {', '.join(SUPPORTED_TICKERS)}")
    return normalized


def _coerce_date(value: str | date | datetime | None, default: date) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return default


def get_price_history(ticker: str) -> list[dict[str, Any]]:
    normalized = _normalize_ticker(ticker)
    return [dict(item) for item in _PRICE_HISTORY[normalized]]


def _backtest_calendar_end_inclusive(start: date, months: int) -> date:
    """Last calendar day of the last month in a span of `months` months starting at `start`'s month."""
    months = max(1, int(months))
    y, m = start.year, start.month + months - 1
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    last_d = calendar.monthrange(y, m)[1]
    return date(y, m, last_d)


def load_backtest_window(
    ticker: str,
    months: int = DEFAULT_BACKTEST_MONTHS,
) -> list[dict[str, Any]]:
    # Demo mode: fixed 10-step window (11 business-day points), chosen from a bullish segment.
    _ = months  # months is ignored; we always replay a short, deterministic window.
    history = get_price_history(ticker)
    if len(history) < BACKTEST_POINTS:
        raise ValueError(f"Not enough historical data for {ticker!r} for 10-step window.")

    # Pick the best 11-point slice by (1) highest total return then (2) most up days.
    best_start = 0
    best_score = (-10_000.0, -1)
    for start in range(0, len(history) - BACKTEST_POINTS + 1):
        window = history[start : start + BACKTEST_POINTS]
        first_close = float(window[0]["close"])
        last_close = float(window[-1]["close"])
        total_return = ((last_close / first_close) - 1.0) if first_close else -10_000.0
        up_days = 0
        for i in range(1, len(window)):
            if float(window[i]["close"]) >= float(window[i - 1]["close"]):
                up_days += 1
        score = (total_return, up_days)
        if score > best_score:
            best_score = score
            best_start = start

    sliced = history[best_start : best_start + BACKTEST_POINTS]
    return [dict(item) for item in sliced]


def get_historical_info(
    ticker: str,
    as_of_date: str | date | datetime,
    *,
    lookback_days: int = 20,
) -> dict[str, Any]:
    normalized = _normalize_ticker(ticker)
    history = _PRICE_HISTORY[normalized]
    as_of = _coerce_date(as_of_date, default=WINDOW_END)
    idx = _find_index_for_date(history, as_of)
    if idx < 0:
        raise ValueError(f"No historical data available for {normalized} on or before {as_of.isoformat()}")

    visible = history[: idx + 1]
    lookback = visible[-max(lookback_days, 1) :]
    context = _COMPANY_CONTEXT[normalized]
    stats = _compute_summary_stats(visible)

    return {
        "ticker": normalized,
        "as_of_date": visible[-1]["date"],
        "price_history": [dict(item) for item in lookback],
        "summary_stats": stats,
        # No news/events: keep decisions purely based on deterministic price + numeric context.
        "dated_events": [],
        "financial_context": dict(context["financial_context"]),
        "company_name": context["name"],
        "company_overview": context["company_overview"],
        "business_model": context["business_model"],
        "market_regime": get_market_regime_label(normalized, visible[-1]["date"]),
        "stock_archetype": get_stock_archetype(normalized),
        "candidate_factors": list(_BASE_CANDIDATE_FACTORS),
        "metadata": {
            "lookback_days": lookback_days,
            "visible_points": len(visible),
            "window_start": WINDOW_START.isoformat(),
            "window_end": WINDOW_END.isoformat(),
        },
    }


def get_info(ticker: str) -> dict[str, Any]:
    normalized = _normalize_ticker(ticker)
    history = _PRICE_HISTORY[normalized]
    latest = history[-1]
    context = _COMPANY_CONTEXT[normalized]
    return {
        "ticker": normalized,
        "company_name": context["name"],
        "company_overview": context["company_overview"],
        "business_model": context["business_model"],
        "price_history": [dict(item) for item in history],
        "summary_stats": _compute_summary_stats(history),
        "financial_context": dict(context["financial_context"]),
        # No news/events: keep decisions purely based on deterministic price + numeric context.
        "dated_events": [],
        "valuation_snapshot": {"price": float(latest["close"])},
        "stock_archetype": get_stock_archetype(normalized),
        "candidate_factors": list(_BASE_CANDIDATE_FACTORS),
        "metadata": {
            "window_start": WINDOW_START.isoformat(),
            "window_end": WINDOW_END.isoformat(),
            "points": len(history),
        },
    }


def get_company_packet(ticker: str) -> dict[str, Any]:
    info = get_info(ticker)
    return {
        "ticker": info["ticker"],
        "name": info["company_name"],
        "overview": info["company_overview"],
        "business_model": info["business_model"],
    }


def get_recent_news(ticker: str) -> list[dict[str, Any]]:
    _ = ticker
    # News/event data intentionally disabled for deterministic math-only decisions.
    return []


def get_financials(ticker: str, period: str = "TTM") -> dict[str, Any]:
    _ = period
    info = get_info(ticker)
    return {
        "ticker": info["ticker"],
        "period": "TTM",
        "context": info["financial_context"],
    }


def get_price_chart(ticker: str, timeframe: str = "10D") -> dict[str, Any]:
    _ = timeframe
    history = get_price_history(ticker)
    closes = [float(item["close"]) for item in history]
    return {
        "ticker": _normalize_ticker(ticker),
        "timeframe": "10D",
        "summary": f"{len(history)} business-day candles from {history[0]['date']} to {history[-1]['date']}.",
        "high": max(closes),
        "low": min(closes),
        "current": closes[-1],
    }


def get_earnings_packet(ticker: str) -> dict[str, Any]:
    normalized = _normalize_ticker(ticker)
    earnings_events = [event for event in _EVENTS.get(normalized, []) if event.get("type") == "earnings"]
    latest = earnings_events[-1] if earnings_events else {"date": WINDOW_START.isoformat(), "headline": "No earnings event"}
    return {
        "ticker": normalized,
        "release_date": latest["date"],
        "headline": latest["headline"],
        "results": dict(_COMPANY_CONTEXT[normalized]["financial_context"]),
    }


def get_stock_archetype(ticker: str) -> str:
    normalized = _normalize_ticker(ticker)
    return _STOCK_ARCHETYPE.get(normalized, "unknown")


def get_candidate_factors(ticker: str) -> list[str]:
    _ = _normalize_ticker(ticker)
    return list(_BASE_CANDIDATE_FACTORS)


def get_market_regime_label(ticker: str, as_of_date: str | date | datetime) -> str:
    normalized = _normalize_ticker(ticker)
    history = _PRICE_HISTORY[normalized]
    as_of = _coerce_date(as_of_date, default=WINDOW_END)
    idx = _find_index_for_date(history, as_of)
    if idx < 0:
        return "range_bound"
    visible = history[: idx + 1]
    stats = _compute_summary_stats(visible)
    ret_20 = float(stats.get("return_20d_pct", 0.0))
    vol_20 = float(stats.get("volatility_20d_pct", 0.0))
    if vol_20 >= 2.0:
        return "high_volatility"
    if ret_20 >= 5.0:
        return "risk_on_trend"
    if ret_20 <= -5.0:
        return "risk_off_drawdown"
    return "range_bound"


def get_forward_window(
    ticker: str,
    as_of_date: str | date | datetime,
    horizon_days: int = 5,
) -> list[dict[str, Any]]:
    normalized = _normalize_ticker(ticker)
    history = _PRICE_HISTORY[normalized]
    as_of = _coerce_date(as_of_date, default=WINDOW_END)
    idx = _find_index_for_date(history, as_of)
    if idx < 0 or idx >= len(history) - 1:
        return []
    start = idx + 1
    end = min(len(history), start + max(1, horizon_days))
    return [dict(item) for item in history[start:end]]


def get_forward_return_pct(
    ticker: str,
    as_of_date: str | date | datetime,
    horizon_days: int = 5,
) -> float:
    normalized = _normalize_ticker(ticker)
    history = _PRICE_HISTORY[normalized]
    as_of = _coerce_date(as_of_date, default=WINDOW_END)
    idx = _find_index_for_date(history, as_of)
    if idx < 0 or idx >= len(history) - 1:
        return 0.0
    forward_window = get_forward_window(normalized, as_of, horizon_days=horizon_days)
    if not forward_window:
        return 0.0
    start_price = float(history[idx]["close"])
    end_price = float(forward_window[-1]["close"])
    if start_price == 0:
        return 0.0
    return round(((end_price / start_price) - 1.0) * 100.0, 4)
