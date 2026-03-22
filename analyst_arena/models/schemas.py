from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from analyst_arena.models.enums import ExecutionRule, MatchOutcome, TradeAction


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return _utc_now()
    return _utc_now()


def _parse_date(value: Any, default: date | None = None) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return default or _utc_now().date()


def _stringify(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _maybe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _maybe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _deep_serialize(value: Any) -> Any:
    if is_dataclass(value):
        return {item.name: _deep_serialize(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _deep_serialize(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_deep_serialize(item) for item in value]
    if isinstance(value, list):
        return [_deep_serialize(item) for item in value]
    return value


def _max_drawdown(values: list[float]) -> float:
    if not values:
        return 0.0
    peak = values[0]
    max_dd = 0.0
    for value in values:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = (peak - value) / peak
            if drawdown > max_dd:
                max_dd = drawdown
    return round(max_dd * 100.0, 3)


@dataclass(slots=True)
class SerializableModel:
    def to_dict(self) -> dict[str, Any]:
        return _deep_serialize(self)


@dataclass(slots=True)
class Agent(SerializableModel):
    name: str
    provider: str
    model_id: str
    display_name: str | None = None
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Agent:
        return cls(
            name=_stringify(payload.get("name")),
            provider=_stringify(payload.get("provider"), "unknown"),
            model_id=_stringify(payload.get("model_id", payload.get("model")), "unknown"),
            display_name=payload.get("display_name"),
            enabled=bool(payload.get("enabled", True)),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class MatchConfig(SerializableModel):
    match_id: str
    ticker: str
    start_date: date
    end_date: date
    starting_cash: float
    execution_rule: ExecutionRule = ExecutionRule.NEXT_OPEN
    transaction_cost_bps: float = 0.0
    decision_lookback_days: int = 20
    flow_name: str = "backtest_showdown"
    agent_a: Agent | None = None
    agent_b: Agent | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MatchConfig:
        return cls(
            match_id=_stringify(payload.get("match_id")),
            ticker=_stringify(payload.get("ticker"), "NVDA").upper(),
            start_date=_parse_date(payload.get("start_date")),
            end_date=_parse_date(payload.get("end_date")),
            starting_cash=_maybe_float(payload.get("starting_cash"), 100000.0),
            execution_rule=ExecutionRule(_stringify(payload.get("execution_rule"), ExecutionRule.NEXT_OPEN.value)),
            transaction_cost_bps=_maybe_float(payload.get("transaction_cost_bps"), 0.0),
            decision_lookback_days=_maybe_int(payload.get("decision_lookback_days"), 20),
            flow_name=_stringify(payload.get("flow_name"), "backtest_showdown"),
            agent_a=Agent.from_dict(payload["agent_a"]) if payload.get("agent_a") else None,
            agent_b=Agent.from_dict(payload["agent_b"]) if payload.get("agent_b") else None,
            metadata=dict(payload.get("metadata", {})),
            created_at=_parse_datetime(payload.get("created_at")),
        )


@dataclass(slots=True)
class HistoricalInfoBundle(SerializableModel):
    ticker: str
    as_of_date: date
    price_history: list[dict[str, Any]] = field(default_factory=list)
    summary_stats: dict[str, float] = field(default_factory=dict)
    dated_events: list[dict[str, Any]] = field(default_factory=list)
    financial_context: dict[str, Any] = field(default_factory=dict)
    stock_archetype: str = "unknown"
    market_regime: str = "neutral"
    candidate_factors: list[str] = field(default_factory=list)
    portfolio_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> HistoricalInfoBundle:
        return cls(
            ticker=_stringify(payload.get("ticker"), "NVDA").upper(),
            as_of_date=_parse_date(payload.get("as_of_date")),
            price_history=list(payload.get("price_history", [])),
            summary_stats={str(k): _maybe_float(v) for k, v in dict(payload.get("summary_stats", {})).items()},
            dated_events=list(payload.get("dated_events", [])),
            financial_context=dict(payload.get("financial_context", {})),
            stock_archetype=_stringify(payload.get("stock_archetype"), "unknown"),
            market_regime=_stringify(payload.get("market_regime"), "neutral"),
            candidate_factors=[_stringify(item) for item in payload.get("candidate_factors", []) if _stringify(item)],
            portfolio_context=dict(payload.get("portfolio_context", {})),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class PortfolioState(SerializableModel):
    cash: float
    shares: float
    market_value: float
    total_equity: float
    last_price: float

    @classmethod
    def starting(cls, cash: float, initial_price: float = 0.0) -> PortfolioState:
        market_value = 0.0
        return cls(
            cash=round(cash, 4),
            shares=0.0,
            market_value=market_value,
            total_equity=round(cash + market_value, 4),
            last_price=round(initial_price, 4),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PortfolioState:
        return cls(
            cash=_maybe_float(payload.get("cash"), 0.0),
            shares=_maybe_float(payload.get("shares"), 0.0),
            market_value=_maybe_float(payload.get("market_value"), 0.0),
            total_equity=_maybe_float(payload.get("total_equity"), 0.0),
            last_price=_maybe_float(payload.get("last_price"), 0.0),
        )

    def mark_to_market(self, price: float) -> PortfolioState:
        market_value = round(self.shares * price, 4)
        total_equity = round(self.cash + market_value, 4)
        return PortfolioState(
            cash=round(self.cash, 4),
            shares=round(self.shares, 8),
            market_value=market_value,
            total_equity=total_equity,
            last_price=round(price, 4),
        )


@dataclass(slots=True)
class ActionDecision(SerializableModel):
    as_of_date: date
    action: TradeAction
    size_pct: float
    position_size: float = 0.0
    horizon: str = "short"
    rationale: str = ""
    confidence: float = 0.0
    top_reasons: list[str] = field(default_factory=list)
    top_risks: list[str] = field(default_factory=list)
    invalidation_condition: str = ""
    factor_scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], default_as_of_date: date | None = None) -> ActionDecision:
        raw_action = _stringify(payload.get("action"), TradeAction.HOLD.value).upper()
        action = TradeAction(raw_action if raw_action in {item.value for item in TradeAction} else TradeAction.HOLD.value)
        parsed_size = _maybe_float(payload.get("size_pct", payload.get("position_size")), 0.0)
        size_pct = max(0.0, min(1.0, parsed_size))
        return cls(
            as_of_date=_parse_date(payload.get("as_of_date"), default_as_of_date),
            action=action,
            size_pct=size_pct,
            position_size=size_pct,
            horizon=_stringify(payload.get("horizon"), "short"),
            rationale=_stringify(payload.get("rationale")),
            confidence=max(0.0, min(1.0, _maybe_float(payload.get("confidence"), 0.0))),
            top_reasons=[_stringify(item) for item in payload.get("top_reasons", []) if _stringify(item)],
            top_risks=[_stringify(item) for item in payload.get("top_risks", []) if _stringify(item)],
            invalidation_condition=_stringify(payload.get("invalidation_condition")),
            factor_scores={str(k): _maybe_float(v, 0.0) for k, v in dict(payload.get("factor_scores", {})).items()},
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class FactorWeightRankingResult(SerializableModel):
    as_of_date: date
    ranked_factors: list[str] = field(default_factory=list)
    factor_weights: dict[str, float] = field(default_factory=dict)
    decisive_metrics: list[str] = field(default_factory=list)
    noisy_metrics: list[str] = field(default_factory=list)
    rationale: str = ""
    horizon: str = "short"
    stock_archetype: str = "unknown"
    market_regime: str = "neutral"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
        default_as_of_date: date | None = None,
    ) -> FactorWeightRankingResult:
        ranked = [_stringify(item) for item in payload.get("ranked_factors", []) if _stringify(item)]
        weights = {
            str(k): max(0.0, _maybe_float(v, 0.0))
            for k, v in dict(payload.get("factor_weights", {})).items()
        }
        return cls(
            as_of_date=_parse_date(payload.get("as_of_date"), default_as_of_date),
            ranked_factors=ranked,
            factor_weights=weights,
            decisive_metrics=[_stringify(item) for item in payload.get("decisive_metrics", []) if _stringify(item)],
            noisy_metrics=[_stringify(item) for item in payload.get("noisy_metrics", []) if _stringify(item)],
            rationale=_stringify(payload.get("rationale")),
            horizon=_stringify(payload.get("horizon"), "short"),
            stock_archetype=_stringify(payload.get("stock_archetype"), "unknown"),
            market_regime=_stringify(payload.get("market_regime"), "neutral"),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class PostTradeReflectionResult(SerializableModel):
    as_of_date: date
    decision_quality: str
    process_quality: str
    luck_vs_skill: str
    confidence_assessment: str
    size_assessment: str
    signals_helped: list[str] = field(default_factory=list)
    signals_misled: list[str] = field(default_factory=list)
    next_time_changes: list[str] = field(default_factory=list)
    outcome_summary: str = ""
    hindsight_flags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
        default_as_of_date: date | None = None,
    ) -> PostTradeReflectionResult:
        return cls(
            as_of_date=_parse_date(payload.get("as_of_date"), default_as_of_date),
            decision_quality=_stringify(payload.get("decision_quality"), "unknown"),
            process_quality=_stringify(payload.get("process_quality"), "unknown"),
            luck_vs_skill=_stringify(payload.get("luck_vs_skill"), "unknown"),
            confidence_assessment=_stringify(payload.get("confidence_assessment"), "unknown"),
            size_assessment=_stringify(payload.get("size_assessment"), "unknown"),
            signals_helped=[_stringify(item) for item in payload.get("signals_helped", []) if _stringify(item)],
            signals_misled=[_stringify(item) for item in payload.get("signals_misled", []) if _stringify(item)],
            next_time_changes=[_stringify(item) for item in payload.get("next_time_changes", []) if _stringify(item)],
            outcome_summary=_stringify(payload.get("outcome_summary")),
            hindsight_flags=[_stringify(item) for item in payload.get("hindsight_flags", []) if _stringify(item)],
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class ScenarioEvaluation(SerializableModel):
    score: float
    components: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ScenarioEvaluation:
        return cls(
            score=max(0.0, min(1.0, _maybe_float(payload.get("score"), 0.0))),
            components={str(k): max(0.0, min(1.0, _maybe_float(v, 0.0))) for k, v in dict(payload.get("components", {})).items()},
            notes=[_stringify(item) for item in payload.get("notes", []) if _stringify(item)],
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class ExecutedTrade(SerializableModel):
    date: date
    action: TradeAction
    shares: float
    execution_price: float
    notional: float
    fees: float = 0.0
    rationale: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ExecutedTrade:
        raw_action = _stringify(payload.get("action"), TradeAction.HOLD.value).upper()
        action = TradeAction(raw_action if raw_action in {item.value for item in TradeAction} else TradeAction.HOLD.value)
        return cls(
            date=_parse_date(payload.get("date")),
            action=action,
            shares=_maybe_float(payload.get("shares"), 0.0),
            execution_price=_maybe_float(payload.get("execution_price"), 0.0),
            notional=_maybe_float(payload.get("notional"), 0.0),
            fees=_maybe_float(payload.get("fees"), 0.0),
            rationale=_stringify(payload.get("rationale")),
            confidence=_maybe_float(payload.get("confidence"), 0.0),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class EquityPoint(SerializableModel):
    date: date
    cash: float
    shares: float
    price: float
    total_equity: float

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> EquityPoint:
        return cls(
            date=_parse_date(payload.get("date")),
            cash=_maybe_float(payload.get("cash"), 0.0),
            shares=_maybe_float(payload.get("shares"), 0.0),
            price=_maybe_float(payload.get("price"), 0.0),
            total_equity=_maybe_float(payload.get("total_equity"), 0.0),
        )


@dataclass(slots=True)
class AgentBacktestResult(SerializableModel):
    agent: Agent
    ticker: str
    start_date: date
    end_date: date
    initial_cash: float
    final_portfolio_value: float
    total_return_pct: float
    max_drawdown_pct: float
    trade_count: int
    win_rate: float
    portfolio_state: PortfolioState
    trade_log: list[ExecutedTrade] = field(default_factory=list)
    equity_curve: list[EquityPoint] = field(default_factory=list)
    decisions: list[ActionDecision] = field(default_factory=list)
    factor_rankings: list[FactorWeightRankingResult] = field(default_factory=list)
    reflections: list[PostTradeReflectionResult] = field(default_factory=list)
    decision_evaluations: list[ScenarioEvaluation] = field(default_factory=list)
    factor_evaluations: list[ScenarioEvaluation] = field(default_factory=list)
    reflection_evaluations: list[ScenarioEvaluation] = field(default_factory=list)
    summaries: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AgentBacktestResult:
        equity_curve = [EquityPoint.from_dict(item) for item in payload.get("equity_curve", [])]
        trade_log = [ExecutedTrade.from_dict(item) for item in payload.get("trade_log", [])]
        decisions = [ActionDecision.from_dict(item) for item in payload.get("decisions", [])]
        factor_rankings = [FactorWeightRankingResult.from_dict(item) for item in payload.get("factor_rankings", [])]
        reflections = [PostTradeReflectionResult.from_dict(item) for item in payload.get("reflections", [])]
        return cls(
            agent=Agent.from_dict(payload.get("agent", {})),
            ticker=_stringify(payload.get("ticker"), "NVDA").upper(),
            start_date=_parse_date(payload.get("start_date")),
            end_date=_parse_date(payload.get("end_date")),
            initial_cash=_maybe_float(payload.get("initial_cash"), 100000.0),
            final_portfolio_value=_maybe_float(payload.get("final_portfolio_value"), 0.0),
            total_return_pct=_maybe_float(payload.get("total_return_pct"), 0.0),
            max_drawdown_pct=_maybe_float(
                payload.get(
                    "max_drawdown_pct",
                    _max_drawdown([point.total_equity for point in equity_curve]),
                ),
                0.0,
            ),
            trade_count=_maybe_int(payload.get("trade_count"), len(trade_log)),
            win_rate=max(0.0, min(1.0, _maybe_float(payload.get("win_rate"), 0.0))),
            portfolio_state=PortfolioState.from_dict(payload.get("portfolio_state", {})),
            trade_log=trade_log,
            equity_curve=equity_curve,
            decisions=decisions,
            factor_rankings=factor_rankings,
            reflections=reflections,
            decision_evaluations=[ScenarioEvaluation.from_dict(item) for item in payload.get("decision_evaluations", [])],
            factor_evaluations=[ScenarioEvaluation.from_dict(item) for item in payload.get("factor_evaluations", [])],
            reflection_evaluations=[ScenarioEvaluation.from_dict(item) for item in payload.get("reflection_evaluations", [])],
            summaries=[_stringify(item) for item in payload.get("summaries", [])],
            elapsed_seconds=_maybe_float(payload.get("elapsed_seconds"), 0.0),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class MatchResult(SerializableModel):
    match_id: str
    ticker: str
    start_date: date
    end_date: date
    config: MatchConfig
    agent_a_result: AgentBacktestResult
    agent_b_result: AgentBacktestResult
    winner_agent_name: str
    winner_final_value: float
    loser_final_value: float
    return_diff_pct: float
    trophy: bool = True
    winner_explanation: str = ""
    timestamp: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def agent_names(self) -> tuple[str, str]:
        return (self.agent_a_result.agent.name, self.agent_b_result.agent.name)

    @property
    def winner(self) -> str:
        return self.winner_agent_name

    @property
    def outcome_for_agent(self) -> dict[str, MatchOutcome]:
        winner = self.winner_agent_name
        if not winner:
            return {name: MatchOutcome.DRAW for name in self.agent_names}
        return {
            self.agent_a_result.agent.name: MatchOutcome.WIN if self.agent_a_result.agent.name == winner else MatchOutcome.LOSS,
            self.agent_b_result.agent.name: MatchOutcome.WIN if self.agent_b_result.agent.name == winner else MatchOutcome.LOSS,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MatchResult:
        config_payload = payload.get("config", {})
        config = MatchConfig.from_dict(config_payload) if config_payload else MatchConfig(
            match_id=_stringify(payload.get("match_id")),
            ticker=_stringify(payload.get("ticker"), "NVDA").upper(),
            start_date=_parse_date(payload.get("start_date")),
            end_date=_parse_date(payload.get("end_date")),
            starting_cash=_maybe_float(payload.get("starting_cash"), 100000.0),
        )
        agent_a_payload = payload.get("agent_a_result", payload.get("agent_a", {}))
        agent_b_payload = payload.get("agent_b_result", payload.get("agent_b", {}))
        winner_name = _stringify(payload.get("winner_agent_name"))
        return cls(
            match_id=_stringify(payload.get("match_id", config.match_id)),
            ticker=_stringify(payload.get("ticker", config.ticker), "NVDA").upper(),
            start_date=_parse_date(payload.get("start_date"), config.start_date),
            end_date=_parse_date(payload.get("end_date"), config.end_date),
            config=config,
            agent_a_result=AgentBacktestResult.from_dict(agent_a_payload),
            agent_b_result=AgentBacktestResult.from_dict(agent_b_payload),
            winner_agent_name=winner_name,
            winner_final_value=_maybe_float(payload.get("winner_final_value"), 0.0),
            loser_final_value=_maybe_float(payload.get("loser_final_value"), 0.0),
            return_diff_pct=_maybe_float(payload.get("return_diff_pct"), 0.0),
            trophy=bool(payload.get("trophy", bool(winner_name))),
            winner_explanation=_stringify(payload.get("winner_explanation")),
            timestamp=_parse_datetime(payload.get("timestamp")),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class LeaderboardEntry(SerializableModel):
    agent_name: str
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    avg_final_value: float = 0.0
    avg_return_pct: float = 0.0
    avg_max_drawdown_pct: float = 0.0
    win_rate: float = 0.0
    last_updated: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> LeaderboardEntry:
        return cls(
            agent_name=_stringify(payload.get("agent_name", payload.get("agent"))),
            matches_played=_maybe_int(payload.get("matches_played"), 0),
            wins=_maybe_int(payload.get("wins"), 0),
            losses=_maybe_int(payload.get("losses"), 0),
            draws=_maybe_int(payload.get("draws"), 0),
            avg_final_value=_maybe_float(payload.get("avg_final_value"), 0.0),
            avg_return_pct=_maybe_float(payload.get("avg_return_pct"), 0.0),
            avg_max_drawdown_pct=_maybe_float(payload.get("avg_max_drawdown_pct"), 0.0),
            win_rate=_maybe_float(payload.get("win_rate"), 0.0),
            last_updated=_parse_datetime(payload.get("last_updated")),
            metadata=dict(payload.get("metadata", {})),
        )
