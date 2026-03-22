from __future__ import annotations

import json
import unittest
from datetime import date

from data import SUPPORTED_TICKERS, get_forward_window, get_historical_info, get_price_history

from analyst_arena.engine.scenarios import build_prompt
from analyst_arena.models import ScenarioName


class NoLookaheadTests(unittest.TestCase):
    def test_historical_info_is_capped_at_as_of_date(self) -> None:
        for ticker in SUPPORTED_TICKERS:
            history = get_price_history(ticker)
            as_of = history[len(history) // 2]["date"]
            bundle = get_historical_info(ticker, as_of)

            max_price_date = max(item["date"] for item in bundle["price_history"])
            self.assertLessEqual(max_price_date, as_of)

            for event in bundle["dated_events"]:
                self.assertLessEqual(event["date"], as_of)

            forward = get_forward_window(ticker, as_of, horizon_days=5)
            if forward:
                self.assertGreater(forward[0]["date"], as_of)

    def test_trade_prompt_does_not_include_future_outcome_by_default(self) -> None:
        ticker = "NVDA"
        as_of = date(2025, 2, 14).isoformat()
        prompt = build_prompt(
            ScenarioName.TRADE_DECISION_STEP.value,
            {"ticker": ticker, "as_of_date": as_of, "portfolio_state": {"cash": 100000.0, "shares": 0.0}},
            agent_name="qa_agent",
        )
        context = json.loads(prompt.split("Context:\n", 1)[1])
        self.assertIn("future_outcome", context)
        self.assertEqual(context["future_outcome"], {})


if __name__ == "__main__":
    unittest.main()
