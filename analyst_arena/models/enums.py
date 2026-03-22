from __future__ import annotations

from enum import StrEnum


class ScenarioName(StrEnum):
    TRADE_DECISION_STEP = "trade_decision_step"
    FACTOR_WEIGHT_RANKING = "factor_weight_ranking"
    POST_TRADE_REFLECTION = "post_trade_reflection"
    HISTORICAL_DECISION_STEP = "historical_decision_step"
    SUMMARIZE_DECISION = "summarize_decision"
    BACKTEST_SHOWDOWN = "backtest_showdown"


class TradeAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class ExecutionRule(StrEnum):
    NEXT_OPEN = "next_open"


class MatchOutcome(StrEnum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
