from __future__ import annotations

import unittest
from datetime import date

from data import get_historical_info

from analyst_arena.models import (
    ActionDecision,
    FactorWeightRankingResult,
    HistoricalInfoBundle,
    PostTradeReflectionResult,
    TradeAction,
)
from analyst_arena.scoring.scenario_eval import (
    evaluate_factor_weight_ranking,
    evaluate_post_trade_reflection,
    evaluate_trade_decision_step,
)


class ScenarioEvalTests(unittest.TestCase):
    @staticmethod
    def _bundle() -> HistoricalInfoBundle:
        payload = get_historical_info("NVDA", "2025-02-14", lookback_days=20)
        return HistoricalInfoBundle.from_dict(payload)

    def test_trade_decision_correctness_scores_higher(self) -> None:
        bundle = self._bundle()
        forward_return_pct = 4.5
        good = ActionDecision(
            as_of_date=bundle.as_of_date,
            action=TradeAction.BUY,
            size_pct=0.4,
            position_size=0.4,
            horizon="short",
            rationale="Momentum and growth are supportive.",
            confidence=0.8,
            top_reasons=["momentum_20d", "revenue_growth_yoy"],
            top_risks=["event_risk"],
            invalidation_condition="Trend breaks.",
        )
        bad = ActionDecision(
            as_of_date=bundle.as_of_date,
            action=TradeAction.SELL,
            size_pct=0.6,
            position_size=0.6,
            horizon="short",
            rationale="No strong rationale.",
            confidence=0.9,
            top_reasons=["unknown_factor"],
            top_risks=[],
            invalidation_condition="",
        )
        self.assertGreater(
            evaluate_trade_decision_step(good, bundle, forward_return_pct).score,
            evaluate_trade_decision_step(bad, bundle, forward_return_pct).score,
        )

    def test_factor_weight_alignment_scores_higher(self) -> None:
        bundle = self._bundle()
        forward_return_pct = 3.2
        aligned = FactorWeightRankingResult(
            as_of_date=bundle.as_of_date,
            ranked_factors=["momentum_20d", "momentum_5d", "revenue_growth_yoy"],
            factor_weights={"momentum_20d": 0.5, "momentum_5d": 0.3, "revenue_growth_yoy": 0.2},
            decisive_metrics=["momentum_20d"],
            noisy_metrics=["valuation_vs_growth"],
            rationale="Momentum and growth lead this setup.",
            horizon="short",
            stock_archetype=bundle.stock_archetype,
            market_regime=bundle.market_regime,
        )
        misaligned = FactorWeightRankingResult(
            as_of_date=bundle.as_of_date,
            ranked_factors=["valuation_vs_growth", "event_risk"],
            factor_weights={"valuation_vs_growth": 0.9, "event_risk": 0.1},
            decisive_metrics=["valuation_vs_growth"],
            noisy_metrics=[],
            rationale="Valuation dominates.",
            horizon="short",
            stock_archetype=bundle.stock_archetype,
            market_regime=bundle.market_regime,
        )
        self.assertGreater(
            evaluate_factor_weight_ranking(aligned, bundle, forward_return_pct).score,
            evaluate_factor_weight_ranking(misaligned, bundle, forward_return_pct).score,
        )

    def test_reflection_hindsight_penalty_applies(self) -> None:
        decision = ActionDecision(
            as_of_date=date(2025, 2, 14),
            action=TradeAction.BUY,
            size_pct=0.3,
            position_size=0.3,
            horizon="short",
            rationale="Momentum setup",
            confidence=0.8,
        )
        clean = PostTradeReflectionResult(
            as_of_date=decision.as_of_date,
            decision_quality="good",
            process_quality="good",
            luck_vs_skill="skill",
            confidence_assessment="appropriate confidence for observed edge",
            size_assessment="appropriate",
            signals_helped=["momentum_20d"],
            signals_misled=["event_risk"],
            next_time_changes=["trim before event clusters"],
            outcome_summary="Outcome aligned with setup under volatility.",
            hindsight_flags=[],
        )
        hindsight = PostTradeReflectionResult(
            as_of_date=decision.as_of_date,
            decision_quality="good",
            process_quality="good",
            luck_vs_skill="skill",
            confidence_assessment="appropriate confidence for observed edge",
            size_assessment="appropriate",
            signals_helped=["momentum_20d"],
            signals_misled=["event_risk"],
            next_time_changes=["trim before event clusters"],
            outcome_summary="It was obvious and guaranteed this would happen.",
            hindsight_flags=["always obvious"],
        )
        clean_score = evaluate_post_trade_reflection(clean, decision, 3.0).score
        hindsight_score = evaluate_post_trade_reflection(hindsight, decision, 3.0).score
        self.assertGreater(clean_score, hindsight_score)


if __name__ == "__main__":
    unittest.main()
