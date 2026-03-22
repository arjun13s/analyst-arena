from __future__ import annotations

from analyst_arena.models import AgentBacktestResult, MatchOutcome


def compute_match_winner(
    agent_a_result: AgentBacktestResult,
    agent_b_result: AgentBacktestResult,
) -> tuple[str, str, float, float, float, str]:
    a_value = float(agent_a_result.final_portfolio_value)
    b_value = float(agent_b_result.final_portfolio_value)
    a_return = float(agent_a_result.total_return_pct)
    b_return = float(agent_b_result.total_return_pct)
    a_dd = float(agent_a_result.max_drawdown_pct)
    b_dd = float(agent_b_result.max_drawdown_pct)
    epsilon = 1e-6

    if abs(a_value - b_value) > epsilon:
        winner, loser = (
            (agent_a_result.agent.name, agent_b_result.agent.name)
            if a_value > b_value
            else (agent_b_result.agent.name, agent_a_result.agent.name)
        )
    elif abs(a_return - b_return) > epsilon:
        winner, loser = (
            (agent_a_result.agent.name, agent_b_result.agent.name)
            if a_return > b_return
            else (agent_b_result.agent.name, agent_a_result.agent.name)
        )
    elif abs(a_dd - b_dd) > epsilon:
        winner, loser = (
            (agent_a_result.agent.name, agent_b_result.agent.name)
            if a_dd < b_dd
            else (agent_b_result.agent.name, agent_a_result.agent.name)
        )
    else:
        winner, loser = sorted([agent_a_result.agent.name, agent_b_result.agent.name])

    if winner == agent_a_result.agent.name:
        winner_value, loser_value = a_value, b_value
    else:
        winner_value, loser_value = b_value, a_value

    return_diff_pct = ((winner_value / loser_value - 1.0) * 100.0) if loser_value else 0.0
    explanation = (
        f"Winner: {winner} finished at ${winner_value:,.2f} versus ${loser_value:,.2f} over the backtest window."
    )
    return winner, loser, round(winner_value, 2), round(loser_value, 2), round(return_diff_pct, 3), explanation


def outcome_for_agent(agent_name: str, winner_agent_name: str) -> MatchOutcome:
    if not winner_agent_name:
        return MatchOutcome.DRAW
    return MatchOutcome.WIN if agent_name == winner_agent_name else MatchOutcome.LOSS
