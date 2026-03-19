from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from data import (
    get_company_packet,
    get_earnings_packet,
    get_financials,
    get_price_chart,
    get_recent_news,
)


DEFAULT_SCENARIO_INPUTS: dict[str, dict[str, Any]] = {
    "earnings_reaction": {"ticker": "NVDA"},
    "analyst_debate": {"ticker": "NVDA"},
    "thesis_revision": {"ticker": "NVDA"},
    "pm_decision_round": {"ticker": "NVDA"},
}


def get_default_inputs(scenario_name: str) -> dict[str, Any]:
    if scenario_name not in DEFAULT_SCENARIO_INPUTS:
        raise ValueError(f"Unsupported scenario: {scenario_name}")
    return deepcopy(DEFAULT_SCENARIO_INPUTS[scenario_name])


def build_prompt(scenario_name: str, inputs: dict[str, Any]) -> str:
    ticker = str(inputs.get("ticker", "NVDA")).upper()
    packet = get_company_packet(ticker)
    financials = get_financials(ticker, str(inputs.get("period", "TTM")))
    news = get_recent_news(ticker)
    price_chart = get_price_chart(ticker, str(inputs.get("timeframe", "1Y")))
    earnings = get_earnings_packet(ticker)

    scenario_brief = {
        "earnings_reaction": (
            "Produce an earnings reaction thesis using the earnings packet and supporting financial context."
        ),
        "analyst_debate": (
            "Produce a debate thesis and a rebuttal against the strongest counterargument."
        ),
        "thesis_revision": (
            "Revise the investment thesis after new information and provide a final rating."
        ),
        "pm_decision_round": (
            "Act as a PM-style analyst: provide a thesis, identify key risks, and give a final rating."
        ),
    }
    if scenario_name not in scenario_brief:
        raise ValueError(f"Unsupported scenario: {scenario_name}")

    payload = {
        "scenario": scenario_name,
        "inputs": inputs,
        "company_packet": packet,
        "financials": financials,
        "recent_news": news,
        "price_chart": price_chart,
        "earnings_packet": earnings,
    }

    return (
        "You are participating in Analyst Arena, a model-vs-model financial reasoning benchmark.\n"
        f"Task: {scenario_brief[scenario_name]}\n"
        "Use the provided market context and return only JSON with these keys:\n"
        '["thesis_text", "stance", "rebuttal_text", "rating", "target_price", "rationale", "metadata"]\n'
        'Valid stances: "bull" or "bear". Valid ratings: "buy", "hold", "sell".\n'
        "The thesis must be specific, evidence-based, and grounded in the supplied data.\n"
        f"Context:\n{json.dumps(payload, indent=2)}"
    )
