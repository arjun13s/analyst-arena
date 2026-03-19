from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, TypedDict

import streamlit as st

from analyst_arena.engine import MatchEngine, Tournament
from analyst_arena.storage import load_results, save_results
from run_tournament import build_agents


RESULTS_PATH = Path("results.json")
SCENARIOS = [
    "earnings_reaction",
    "analyst_debate",
    "thesis_revision",
    "pm_decision_round",
]


class AgentPanelData(TypedDict):
    name: str
    thesis: str
    score: float
    breakdown: dict[str, Any]


class MatchViewData(TypedDict):
    agent_a: AgentPanelData
    agent_b: AgentPanelData
    winner: str
    reasoning: str
    scenario: str
    raw: dict[str, Any]


def run_match(agent_a_name: str, agent_b_name: str, scenario: str) -> MatchViewData:
    agents = build_agents()
    match_engine = MatchEngine()
    result = match_engine.run_match(
        agent_a=agents[agent_a_name],
        agent_b=agents[agent_b_name],
        scenario=scenario,
    )

    existing_results = load_results(RESULTS_PATH)
    existing_results.append(result)
    save_results(existing_results, RESULTS_PATH)
    st.cache_data.clear()

    payload = asdict(result)
    details = payload["details"]
    return {
        "agent_a": {
            "name": payload["agent_a"],
            "thesis": details["agent_a_result"]["thesis_text"],
            "score": payload["score_a"],
            "breakdown": details["agent_a_score"],
        },
        "agent_b": {
            "name": payload["agent_b"],
            "thesis": details["agent_b_result"]["thesis_text"],
            "score": payload["score_b"],
            "breakdown": details["agent_b_score"],
        },
        "winner": payload["winner"],
        "reasoning": details["pm_decision"]["rationale"],
        "scenario": details["scenario"],
        "raw": payload,
    }


@st.cache_data(show_spinner=False)
def get_leaderboard() -> list[dict[str, Any]]:
    agents = list(build_agents().values())
    tournament = Tournament(agents=agents)
    tournament.results = load_results(RESULTS_PATH)
    return tournament.leaderboard()


def render_sidebar_controls() -> tuple[str, str, str]:
    st.sidebar.header("Run Match")
    agent_names = list(build_agents().keys())
    agent_a = st.sidebar.selectbox("Agent A", agent_names, index=0)
    default_b = 1 if len(agent_names) > 1 else 0
    agent_b = st.sidebar.selectbox("Agent B", agent_names, index=default_b)
    scenario = st.sidebar.selectbox("Scenario", SCENARIOS, index=1)
    return agent_a, agent_b, scenario


def render_header() -> None:
    st.set_page_config(page_title="Analyst Arena", page_icon="📈", layout="wide")
    st.title("Analyst Arena")
    st.caption("Model-vs-model financial reasoning benchmark")


def render_match_controls(agent_a: str, agent_b: str, scenario: str) -> None:
    st.subheader("Run Match")
    controls = st.columns([1, 1, 1, 1, 1])
    controls[0].markdown(f"**Agent A:** `{agent_a}`")
    controls[1].markdown(f"**Agent B:** `{agent_b}`")
    controls[2].markdown(f"**Scenario:** `{scenario}`")

    if controls[3].button("Run Match", type="primary", use_container_width=True):
        with st.spinner("Running Analyst Arena match..."):
            st.session_state["last_result"] = run_match(agent_a, agent_b, scenario)

    if controls[4].button("Run Multiple Matches", use_container_width=True):
        with st.spinner("Running a short batch..."):
            latest: MatchViewData | None = None
            for _ in range(3):
                latest = run_match(agent_a, agent_b, scenario)
            if latest is not None:
                st.session_state["last_result"] = latest


def render_agent_panel(title: str, agent_data: AgentPanelData) -> None:
    st.markdown(f"### {title}: {agent_data['name']}")
    score_columns = st.columns(2)
    score_columns[0].metric("Score", f"{agent_data['score']:.1f}")
    breakdown = agent_data["breakdown"]
    score_columns[1].metric(
        "Hallucinations",
        str(breakdown.get("hallucination_count", 0)),
    )
    st.markdown("**Thesis**")
    st.markdown(agent_data["thesis"] or "_No thesis returned._")
    st.markdown("**Score Breakdown**")
    st.json(breakdown, expanded=False)


def render_match_result(result: MatchViewData | None) -> None:
    st.subheader("Match Output")
    if result is None:
        st.info("Run a match to view side-by-side debate output.")
        return

    left, right = st.columns(2)
    with left:
        render_agent_panel("Agent A", result["agent_a"])
    with right:
        render_agent_panel("Agent B", result["agent_b"])

    winner = result["winner"]
    winner_label = "🤝 Tie" if winner == "tie" else f"🏆 Winner: {winner}"
    st.markdown("---")
    st.markdown(f"## {winner_label}")

    metrics = st.columns(3)
    metrics[0].metric("Scenario", result["scenario"])
    metrics[1].metric("Agent A Score", f"{result['agent_a']['score']:.1f}")
    metrics[2].metric("Agent B Score", f"{result['agent_b']['score']:.1f}")

    st.markdown("**Judge Reasoning**")
    st.markdown(result["reasoning"] or "_No reasoning returned._")

    with st.expander("Structured Match Result"):
        st.json(result["raw"], expanded=False)


def render_leaderboard() -> None:
    st.subheader("Leaderboard")
    rows = get_leaderboard()
    st.table(rows)


def main() -> None:
    render_header()
    if "last_result" not in st.session_state:
        st.session_state["last_result"] = None

    agent_a, agent_b, scenario = render_sidebar_controls()
    render_match_controls(agent_a, agent_b, scenario)
    render_match_result(st.session_state.get("last_result"))
    render_leaderboard()


if __name__ == "__main__":
    main()
