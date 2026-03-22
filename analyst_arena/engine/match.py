from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from analyst_arena.agents.base import Agent
from analyst_arena.models import (
    ActionDecision,
    AgentBacktestResult,
    EquityPoint,
    ExecutedTrade,
    FactorWeightRankingResult,
    HistoricalInfoBundle,
    MatchConfig,
    MatchResult,
    PostTradeReflectionResult,
    PortfolioState,
    ScenarioName,
    ScenarioEvaluation,
    TradeAction,
)
from analyst_arena.scoring.evaluator import compute_match_winner
from analyst_arena.scoring.leaderboard import build_leaderboard
from analyst_arena.scoring.scenario_eval import (
    evaluate_factor_weight_ranking,
    evaluate_post_trade_reflection,
    evaluate_trade_decision_step,
)
from analyst_arena.storage.leaderboard import save_leaderboard
from analyst_arena.storage.results import append_result, load_results
from data import get_forward_return_pct, get_forward_window, get_historical_info, load_backtest_window


class MatchEngine:
    def __init__(
        self,
        *,
        results_path: str | Path = "match_results.json",
        leaderboard_path: str | Path = "leaderboard.json",
        starting_cash: float = 100000.0,
        transaction_cost_bps: float = 0.0,
        decision_lookback_days: int = 20,
        include_summaries: bool = False,
    ) -> None:
        self.results_path = Path(results_path)
        self.leaderboard_path = Path(leaderboard_path)
        self.starting_cash = float(starting_cash)
        self.transaction_cost_bps = float(transaction_cost_bps)
        self.decision_lookback_days = int(decision_lookback_days)
        self.include_summaries = include_summaries

    def load_backtest_window(self, ticker: str, months: int = 3) -> list[dict[str, Any]]:
        window = load_backtest_window(ticker, months=months)
        if len(window) < 2:
            raise ValueError(f"Not enough historical data for {ticker}. Need at least 2 rows.")
        return window

    def prepare_backtest_match(
        self,
        ticker: str,
        agent_a: Agent,
        agent_b: Agent,
        starting_cash: float = 100000.0,
    ) -> MatchConfig:
        window = self.load_backtest_window(ticker, months=3)
        return MatchConfig(
            match_id=f"match_{uuid.uuid4().hex[:12]}",
            ticker=ticker.upper(),
            start_date=date.fromisoformat(str(window[0]["date"])),
            end_date=date.fromisoformat(str(window[-1]["date"])),
            starting_cash=float(starting_cash),
            transaction_cost_bps=self.transaction_cost_bps,
            decision_lookback_days=self.decision_lookback_days,
            agent_a=agent_a.describe(),
            agent_b=agent_b.describe(),
            metadata={"timesteps": len(window)},
        )

    def run_agent_step(
        self,
        agent: Agent,
        ticker: str,
        as_of_date: str,
        portfolio_state: PortfolioState,
    ) -> tuple[HistoricalInfoBundle, ActionDecision, FactorWeightRankingResult, str]:
        info_payload = get_historical_info(
            ticker,
            as_of_date,
            lookback_days=self.decision_lookback_days,
        )
        info_payload["portfolio_context"] = portfolio_state.to_dict()
        info_bundle = HistoricalInfoBundle.from_dict(info_payload)

        raw_decision = agent.run_scenario(
            ScenarioName.TRADE_DECISION_STEP.value,
            {
                "ticker": ticker,
                "as_of_date": info_bundle.as_of_date.isoformat(),
                "portfolio_state": portfolio_state.to_dict(),
                "info_bundle": info_bundle.to_dict(),
            },
        )
        decision = ActionDecision.from_dict(raw_decision, default_as_of_date=info_bundle.as_of_date)

        raw_factors = agent.run_scenario(
            ScenarioName.FACTOR_WEIGHT_RANKING.value,
            {
                "ticker": ticker,
                "as_of_date": info_bundle.as_of_date.isoformat(),
                "portfolio_state": portfolio_state.to_dict(),
                "info_bundle": info_bundle.to_dict(),
                "candidate_factors": list(info_bundle.candidate_factors),
                "stock_archetype": info_bundle.stock_archetype,
                "market_regime": info_bundle.market_regime,
                "horizon": decision.horizon,
            },
        )
        factor_ranking = FactorWeightRankingResult.from_dict(raw_factors, default_as_of_date=info_bundle.as_of_date)

        summary = ""
        if self.include_summaries:
            summary_payload = agent.run_scenario(
                ScenarioName.SUMMARIZE_DECISION.value,
                {
                    "ticker": ticker,
                    "as_of_date": info_bundle.as_of_date.isoformat(),
                    "decision": decision.to_dict(),
                    "portfolio_state": portfolio_state.to_dict(),
                },
            )
            summary = str(summary_payload.get("summary", "")).strip()

        return info_bundle, decision, factor_ranking, summary

    def execute_trade(
        self,
        action_result: ActionDecision,
        next_execution_price: float,
        portfolio_state: PortfolioState,
        execution_date: date,
    ) -> tuple[PortfolioState, ExecutedTrade | None]:
        price = max(0.0001, float(next_execution_price))
        state = portfolio_state
        fee_rate = max(0.0, self.transaction_cost_bps) / 10000.0
        trade: ExecutedTrade | None = None

        if action_result.action == TradeAction.BUY and state.cash > 0.0 and action_result.size_pct > 0.0:
            notional = state.cash * action_result.size_pct
            fee = notional * fee_rate
            spendable = max(0.0, notional - fee)
            shares = spendable / price
            if shares > 0.0:
                new_cash = state.cash - notional
                new_shares = state.shares + shares
                state = PortfolioState(
                    cash=round(new_cash, 4),
                    shares=round(new_shares, 8),
                    market_value=0.0,
                    total_equity=0.0,
                    last_price=price,
                )
                trade = ExecutedTrade(
                    date=execution_date,
                    action=TradeAction.BUY,
                    shares=round(shares, 8),
                    execution_price=round(price, 4),
                    notional=round(notional, 4),
                    fees=round(fee, 4),
                    rationale=action_result.rationale,
                    confidence=action_result.confidence,
                    metadata={"size_pct": action_result.size_pct},
                )

        elif action_result.action == TradeAction.SELL and state.shares > 0.0 and action_result.size_pct > 0.0:
            shares = min(state.shares, state.shares * action_result.size_pct)
            notional = shares * price
            fee = notional * fee_rate
            proceeds = max(0.0, notional - fee)
            if shares > 0.0:
                new_cash = state.cash + proceeds
                new_shares = state.shares - shares
                state = PortfolioState(
                    cash=round(new_cash, 4),
                    shares=round(max(0.0, new_shares), 8),
                    market_value=0.0,
                    total_equity=0.0,
                    last_price=price,
                )
                trade = ExecutedTrade(
                    date=execution_date,
                    action=TradeAction.SELL,
                    shares=round(shares, 8),
                    execution_price=round(price, 4),
                    notional=round(notional, 4),
                    fees=round(fee, 4),
                    rationale=action_result.rationale,
                    confidence=action_result.confidence,
                    metadata={"size_pct": action_result.size_pct},
                )

        return state.mark_to_market(price), trade

    def run_single_agent_backtest(
        self,
        agent: Agent,
        ticker: str,
        window: list[dict[str, Any]],
        match_config: MatchConfig,
    ) -> AgentBacktestResult:
        start_ts = perf_counter()
        initial_price = float(window[0]["close"])
        portfolio_state = PortfolioState.starting(match_config.starting_cash, initial_price)
        equity_curve: list[EquityPoint] = [
            EquityPoint(
                date=date.fromisoformat(str(window[0]["date"])),
                cash=portfolio_state.cash,
                shares=portfolio_state.shares,
                price=initial_price,
                total_equity=portfolio_state.total_equity,
            )
        ]
        trade_log: list[ExecutedTrade] = []
        decisions: list[ActionDecision] = []
        factor_rankings: list[FactorWeightRankingResult] = []
        reflections: list[PostTradeReflectionResult] = []
        decision_evaluations: list[ScenarioEvaluation] = []
        factor_evaluations: list[ScenarioEvaluation] = []
        reflection_evaluations: list[ScenarioEvaluation] = []
        summaries: list[str] = []

        for idx in range(len(window) - 1):
            current = window[idx]
            nxt = window[idx + 1]
            info_bundle, decision, factor_ranking, summary = self.run_agent_step(
                agent,
                ticker,
                as_of_date=str(current["date"]),
                portfolio_state=portfolio_state.mark_to_market(float(current["close"])),
            )
            decisions.append(decision)
            factor_rankings.append(factor_ranking)
            if summary:
                summaries.append(summary)

            forward_return_pct = get_forward_return_pct(
                ticker,
                current["date"],
                horizon_days=5 if decision.horizon == "short" else 20,
            )
            decision_eval = evaluate_trade_decision_step(decision, info_bundle, forward_return_pct)
            factor_eval = evaluate_factor_weight_ranking(factor_ranking, info_bundle, forward_return_pct)
            decision_evaluations.append(decision_eval)
            factor_evaluations.append(factor_eval)

            execution_date = date.fromisoformat(str(nxt["date"]))
            portfolio_state, trade = self.execute_trade(
                decision,
                next_execution_price=float(nxt["open"]),
                portfolio_state=portfolio_state,
                execution_date=execution_date,
            )
            portfolio_state = portfolio_state.mark_to_market(float(nxt["close"]))
            if trade is not None:
                trade_log.append(trade)

            reflection_payload = agent.run_scenario(
                ScenarioName.POST_TRADE_REFLECTION.value,
                {
                    "ticker": ticker,
                    "as_of_date": str(current["date"]),
                    "info_bundle": info_bundle.to_dict(),
                    "original_decision": decision.to_dict(),
                    "future_outcome": {
                        "forward_return_pct": forward_return_pct,
                        "forward_path": get_forward_window(
                            ticker,
                            current["date"],
                            horizon_days=5 if decision.horizon == "short" else 20,
                        ),
                        "benchmark_return_pct": 0.0,
                    },
                },
            )
            reflection = PostTradeReflectionResult.from_dict(
                reflection_payload,
                default_as_of_date=date.fromisoformat(str(current["date"])),
            )
            reflection_eval = evaluate_post_trade_reflection(reflection, decision, forward_return_pct)
            reflections.append(reflection)
            reflection_evaluations.append(reflection_eval)

            equity_curve.append(
                EquityPoint(
                    date=execution_date,
                    cash=portfolio_state.cash,
                    shares=portfolio_state.shares,
                    price=float(nxt["close"]),
                    total_equity=portfolio_state.total_equity,
                )
            )

        final_value = portfolio_state.total_equity
        total_return_pct = ((final_value / match_config.starting_cash) - 1.0) * 100.0 if match_config.starting_cash else 0.0
        max_drawdown_pct = self._compute_max_drawdown(equity_curve)
        win_rate = self._compute_trade_win_rate(trade_log)

        return AgentBacktestResult(
            agent=agent.describe(),
            ticker=ticker.upper(),
            start_date=match_config.start_date,
            end_date=match_config.end_date,
            initial_cash=match_config.starting_cash,
            final_portfolio_value=round(final_value, 4),
            total_return_pct=round(total_return_pct, 4),
            max_drawdown_pct=max_drawdown_pct,
            trade_count=len(trade_log),
            win_rate=round(win_rate, 4),
            portfolio_state=portfolio_state,
            trade_log=trade_log,
            equity_curve=equity_curve,
            decisions=decisions,
            factor_rankings=factor_rankings,
            reflections=reflections,
            decision_evaluations=decision_evaluations,
            factor_evaluations=factor_evaluations,
            reflection_evaluations=reflection_evaluations,
            summaries=summaries,
            elapsed_seconds=round(perf_counter() - start_ts, 3),
            metadata={
                "steps": len(window) - 1,
                "lookback_days": self.decision_lookback_days,
            },
        )

    def run_head_to_head_backtest(
        self,
        agent_a: Agent,
        agent_b: Agent,
        ticker: str,
        window: list[dict[str, Any]],
        match_config: MatchConfig,
    ) -> tuple[AgentBacktestResult, AgentBacktestResult]:
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(self.run_single_agent_backtest, agent_a, ticker, window, match_config)
            future_b = executor.submit(self.run_single_agent_backtest, agent_b, ticker, window, match_config)
            return future_a.result(), future_b.result()

    def persist_match_result(self, match_result: MatchResult) -> None:
        append_result(match_result, self.results_path)

    def update_leaderboard(self, match_result: MatchResult) -> list[dict[str, Any]]:
        results = load_results(self.results_path)
        agent_names = [match_result.agent_a_result.agent.name, match_result.agent_b_result.agent.name]
        entries = build_leaderboard(results, agent_names)
        save_leaderboard(entries, self.leaderboard_path)
        return [entry.to_dict() for entry in entries]

    def run_match(
        self,
        agents: list[Agent],
        ticker: str = "NVDA",
        months: int = 3,
        starting_cash: float | None = None,
    ) -> MatchResult:
        if len(agents) != 2:
            raise ValueError("Backtest showdown requires exactly 2 agents.")
        if agents[0].name == agents[1].name:
            raise ValueError("Backtest showdown requires two distinct agents.")

        initial_cash = self.starting_cash if starting_cash is None else float(starting_cash)
        window = self.load_backtest_window(ticker, months=months)
        match_config = self.prepare_backtest_match(ticker, agents[0], agents[1], starting_cash=initial_cash)
        agent_a_result, agent_b_result = self.run_head_to_head_backtest(
            agents[0],
            agents[1],
            ticker.upper(),
            window,
            match_config,
        )

        winner, loser, winner_value, loser_value, return_diff_pct, explanation = compute_match_winner(
            agent_a_result,
            agent_b_result,
        )
        match_result = MatchResult(
            match_id=match_config.match_id,
            ticker=match_config.ticker,
            start_date=match_config.start_date,
            end_date=match_config.end_date,
            config=match_config,
            agent_a_result=agent_a_result,
            agent_b_result=agent_b_result,
            winner_agent_name=winner,
            winner_final_value=winner_value,
            loser_final_value=loser_value,
            return_diff_pct=return_diff_pct,
            trophy=True,
            winner_explanation=explanation,
            timestamp=datetime.now(timezone.utc),
            metadata={"loser_agent_name": loser, "months": months},
        )
        self.persist_match_result(match_result)
        self.update_leaderboard(match_result)
        return match_result

    @staticmethod
    def _compute_max_drawdown(curve: list[EquityPoint]) -> float:
        if not curve:
            return 0.0
        peak = curve[0].total_equity
        max_dd = 0.0
        for point in curve:
            value = point.total_equity
            if value > peak:
                peak = value
            if peak > 0:
                drawdown = (peak - value) / peak
                if drawdown > max_dd:
                    max_dd = drawdown
        return round(max_dd * 100.0, 4)

    @staticmethod
    def _compute_trade_win_rate(trades: list[ExecutedTrade]) -> float:
        avg_cost = 0.0
        shares_held = 0.0
        wins = 0
        closed = 0

        for trade in trades:
            if trade.action == TradeAction.BUY and trade.shares > 0:
                total_cost = avg_cost * shares_held + trade.execution_price * trade.shares
                shares_held += trade.shares
                if shares_held > 0:
                    avg_cost = total_cost / shares_held
            elif trade.action == TradeAction.SELL and trade.shares > 0 and shares_held > 0:
                sold = min(shares_held, trade.shares)
                pnl = (trade.execution_price - avg_cost) * sold
                shares_held -= sold
                closed += 1
                if pnl > 0:
                    wins += 1
                if shares_held <= 0:
                    avg_cost = 0.0

        return (wins / closed) if closed else 0.0


DebateMatchEngine = MatchEngine
