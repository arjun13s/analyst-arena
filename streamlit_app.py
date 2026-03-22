from __future__ import annotations

import os
import time
import inspect
from typing import Any

import streamlit as st

from analyst_arena.agents import build_default_agents
from data import SUPPORTED_TICKERS, get_info
from run_tournament import get_leaderboard as backend_get_leaderboard
from run_tournament import run_match as backend_run_match


MIN_THINKING_SECONDS = 3.5
SCREEN_STOCK = "stock"
SCREEN_SIM = "sim"
SCREEN_RESULT = "result"
DEFAULT_AGENT_A = "hud_model"
DEFAULT_AGENT_B = "gpt4o"


@st.cache_data(show_spinner=False)
def load_stock_info(ticker: str) -> dict[str, Any]:
    return get_info(ticker)


@st.cache_data(show_spinner=False)
def load_leaderboard() -> list[dict[str, Any]]:
    return backend_get_leaderboard()


def _agent_registry() -> dict[str, Any]:
    return build_default_agents()


def _ensure_state() -> None:
    st.session_state.setdefault("screen", SCREEN_STOCK)
    st.session_state.setdefault("ticker", SUPPORTED_TICKERS[0])
    st.session_state.setdefault("agent_a", DEFAULT_AGENT_A)
    st.session_state.setdefault("agent_b", DEFAULT_AGENT_B)
    st.session_state.setdefault("last_result", None)


def _has_key_for_agent(agent_name: str) -> bool:
    mapping = {
        "hud_model": "HUD_API_KEY",
        "gpt4o": "OPENAI_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
        "grok": "XAI_API_KEY",
    }
    if agent_name.startswith("hud_"):
        return bool(os.getenv("HUD_API_KEY"))
    key_name = mapping.get(agent_name)
    if key_name is None:
        return True
    return bool(os.getenv(key_name))


def _run_match_safe(agent_a: str, agent_b: str, ticker: str) -> dict[str, Any]:
    """Handle both new and legacy run_match signatures during local dev."""
    params = inspect.signature(backend_run_match).parameters
    kwargs: dict[str, Any] = {"ticker": ticker, "starting_cash": 100000.0}
    if "months" in params:
        kwargs["months"] = 3
    return backend_run_match(agent_a, agent_b, **kwargs)


def _render_header() -> None:
    st.set_page_config(page_title="Analyst Arena Backtest", page_icon="chart_with_upwards_trend", layout="wide")
    st.title("Analyst Arena: Backtest Showdown")
    st.caption("Objective winner by final portfolio value over the same 3-month window.")


def _render_stock_screen() -> None:
    st.subheader("1) Select Stock")
    ticker = st.selectbox("Ticker", list(SUPPORTED_TICKERS), index=list(SUPPORTED_TICKERS).index(st.session_state.ticker))
    st.session_state.ticker = ticker
    info = load_stock_info(ticker)
    st.info(info.get("company_overview", ""))
    if st.button("Continue", type="primary", use_container_width=True):
        st.session_state.screen = SCREEN_SIM


def _render_agent_card(agent_name: str) -> None:
    agent = _agent_registry()[agent_name]
    available = _has_key_for_agent(agent_name)
    model_label = getattr(agent, "model_id", None) or getattr(agent, "model", None) or "unknown"
    container = st.container(border=True)
    with container:
        st.markdown(f"### {agent.display_name or agent.name}")
        st.caption(f"{agent.provider} | {model_label}")
        st.markdown("Key status: configured" if available else "Key status: missing API key")


def _render_sim_screen() -> None:
    st.subheader("2) Configure Contestants")
    registry = _agent_registry()
    names = list(registry.keys())

    if st.session_state.agent_a not in names:
        st.session_state.agent_a = names[0]
    if st.session_state.agent_b not in names or st.session_state.agent_b == st.session_state.agent_a:
        st.session_state.agent_b = names[1] if len(names) > 1 else names[0]

    agent_a = st.selectbox("Agent A", names, index=names.index(st.session_state.agent_a))
    agent_b_options = [name for name in names if name != agent_a]
    agent_b_default = st.session_state.agent_b if st.session_state.agent_b in agent_b_options else agent_b_options[0]
    agent_b = st.selectbox("Agent B", agent_b_options, index=agent_b_options.index(agent_b_default))
    st.session_state.agent_a = agent_a
    st.session_state.agent_b = agent_b

    cols = st.columns(2)
    with cols[0]:
        _render_agent_card(agent_a)
    with cols[1]:
        _render_agent_card(agent_b)

    if st.button("Start 3-Month Simulation", type="primary", use_container_width=True):
        try:
            with st.spinner(f"Running objective backtest for {st.session_state.ticker}..."):
                start = time.perf_counter()
                result = _run_match_safe(agent_a, agent_b, ticker=st.session_state.ticker)
                elapsed = time.perf_counter() - start
                if elapsed < MIN_THINKING_SECONDS:
                    time.sleep(MIN_THINKING_SECONDS - elapsed)
            st.session_state.last_result = result
            st.cache_data.clear()
            st.session_state.screen = SCREEN_RESULT
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    if st.button("Back to Stock Selection", use_container_width=True):
        st.session_state.screen = SCREEN_STOCK


def _render_result_screen() -> None:
    result = st.session_state.last_result
    if not result:
        st.warning("No simulation result yet.")
        return

    ticker = result["ticker"]
    st.markdown(f"# Trophy: {result['winner_display_name']}")
    st.success(result["reasoning"])
    st.caption(f"{ticker} | {result['start_date']} to {result['end_date']}")

    metrics = st.columns(3)
    metrics[0].metric("Winner Final Value", f"${float(result['winner_final_value']):,.2f}")
    metrics[1].metric("Loser Final Value", f"${float(result['loser_final_value']):,.2f}")
    metrics[2].metric("Return Difference", f"{float(result['return_diff_pct']):.3f}%")

    left, right = st.columns(2)
    for col, key in ((left, "agent_a"), (right, "agent_b")):
        with col:
            agent = result[key]
            st.markdown(f"### {agent['display_name']}")
            st.metric("Final Portfolio", f"${float(agent['final_portfolio_value']):,.2f}")
            st.metric("Total Return", f"{float(agent['total_return_pct']):.3f}%")
            st.metric("Max Drawdown", f"{float(agent['max_drawdown_pct']):.3f}%")
            st.metric("Trade Count", int(agent["trade_count"]))
            st.caption(f"Win Rate (closed sells): {float(agent['win_rate']):.1%}")
            with st.expander("Decision summaries"):
                st.write(agent.get("summaries", []))
            with st.expander("Trade log"):
                st.json(agent.get("trade_log", []), expanded=False)

    st.markdown("## Leaderboard")
    rows = load_leaderboard()
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No matches recorded yet.")

    actions = st.columns(2)
    if actions[0].button("Run Another Match", use_container_width=True):
        st.session_state.screen = SCREEN_SIM
    if actions[1].button("Pick Another Stock", use_container_width=True):
        st.session_state.screen = SCREEN_STOCK


def main() -> None:
    _ensure_state()
    _render_header()

    screen = st.session_state.screen
    if screen == SCREEN_STOCK:
        _render_stock_screen()
    elif screen == SCREEN_SIM:
        _render_sim_screen()
    else:
        _render_result_screen()


if __name__ == "__main__":
    main()
