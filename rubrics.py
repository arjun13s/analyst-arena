from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from analyst_arena.models import AgentBacktestResult
from analyst_arena.scoring.evaluator import compute_match_winner


@dataclass(slots=True)
class BacktestScore:
    final_value: float
    total_return_pct: float
    max_drawdown_pct: float
    trade_count: int
    win_rate: float

    @property
    def display_metrics(self) -> dict[str, float]:
        return {
            "final_value": round(self.final_value, 2),
            "total_return_pct": round(self.total_return_pct, 3),
            "max_drawdown_pct": round(self.max_drawdown_pct, 3),
            "trade_count": float(self.trade_count),
            "win_rate": round(self.win_rate, 3),
        }


def score_backtest(result: AgentBacktestResult) -> BacktestScore:
    return BacktestScore(
        final_value=result.final_portfolio_value,
        total_return_pct=result.total_return_pct,
        max_drawdown_pct=result.max_drawdown_pct,
        trade_count=result.trade_count,
        win_rate=result.win_rate,
    )


def compare_backtests(agent_a_result: AgentBacktestResult, agent_b_result: AgentBacktestResult) -> dict[str, Any]:
    winner, loser, winner_value, loser_value, return_diff_pct, explanation = compute_match_winner(
        agent_a_result,
        agent_b_result,
    )
    return {
        "winner_agent_name": winner,
        "loser_agent_name": loser,
        "winner_final_value": winner_value,
        "loser_final_value": loser_value,
        "return_diff_pct": return_diff_pct,
        "winner_explanation": explanation,
        "trophy": True,
    }
