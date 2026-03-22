from __future__ import annotations

from analyst_arena.models import AgentBacktestResult
from analyst_arena.scoring.evaluator import compute_match_winner


def objective_winner(agent_a_result: AgentBacktestResult, agent_b_result: AgentBacktestResult) -> dict[str, object]:
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


def judge_showdown(*args, **kwargs) -> dict[str, object]:
    return objective_winner(*args, **kwargs)


def judge_debate(*args, **kwargs) -> dict[str, object]:
    return objective_winner(*args, **kwargs)
