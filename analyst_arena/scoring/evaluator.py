from __future__ import annotations

from typing import Any

from analyst_arena.agents.base import ScenarioResult
from rubrics import ThesisScore, score_pm_decision, score_thesis


def evaluate_matchup(
    scenario_name: str,
    inputs: dict[str, Any],
    agent_a_name: str,
    agent_b_name: str,
    result_a: ScenarioResult,
    result_b: ScenarioResult,
) -> dict[str, Any]:
    thesis_score_a = score_thesis(
        thesis_text=result_a.get("thesis_text", ""),
        rebuttal_text=result_a.get("rebuttal_text"),
    )
    thesis_score_b = score_thesis(
        thesis_text=result_b.get("thesis_text", ""),
        rebuttal_text=result_b.get("rebuttal_text"),
    )

    score_a = float(thesis_score_a.total_score)
    score_b = float(thesis_score_b.total_score)

    winner = _pick_winner(
        agent_a_name=agent_a_name,
        agent_b_name=agent_b_name,
        score_a=score_a,
        score_b=score_b,
    )
    pm_decision = score_pm_decision(
        thesis_a_text=result_a.get("thesis_text", ""),
        thesis_b_text=result_b.get("thesis_text", ""),
        winner=_winner_to_rating(winner, agent_a_name, agent_b_name),
        rationale=_winner_rationale(winner, agent_a_name, agent_b_name, scenario_name, score_a, score_b),
    )

    return {
        "scenario_name": scenario_name,
        "inputs": inputs,
        "score_a": score_a,
        "score_b": score_b,
        "winner": winner,
        "thesis_score_a": thesis_score_a,
        "thesis_score_b": thesis_score_b,
        "pm_decision": pm_decision,
    }


def _pick_winner(
    agent_a_name: str,
    agent_b_name: str,
    score_a: float,
    score_b: float,
) -> str:
    if score_a > score_b:
        return agent_a_name
    if score_b > score_a:
        return agent_b_name
    return "tie"


def _winner_to_rating(winner: str, agent_a_name: str, agent_b_name: str) -> str:
    if winner == agent_a_name:
        return "buy"
    if winner == agent_b_name:
        return "sell"
    return "hold"


def _winner_rationale(
    winner: str,
    agent_a_name: str,
    agent_b_name: str,
    scenario_name: str,
    score_a: float,
    score_b: float,
) -> str:
    if winner == "tie":
        return (
            f"{scenario_name}: both agents were evenly matched with scores "
            f"{score_a:.1f} and {score_b:.1f}."
        )
    loser = agent_b_name if winner == agent_a_name else agent_a_name
    return (
        f"{scenario_name}: {winner} outperformed {loser} based on thesis quality, financial reasoning, "
        f"and rebuttal effectiveness ({score_a:.1f} vs {score_b:.1f})."
    )
