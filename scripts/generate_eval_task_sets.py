from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from data import (
    SUPPORTED_TICKERS,
    get_forward_return_pct,
    get_forward_window,
    get_historical_info,
    get_market_regime_label,
    get_stock_archetype,
    load_backtest_window,
)


@dataclass
class EvalRecord:
    task_id: str
    scenario: str
    split: str
    ticker: str
    as_of_date: str
    inputs: dict[str, Any]
    metadata: dict[str, Any]


def _portfolio_templates() -> list[dict[str, float]]:
    return [
        {"cash": 100000.0, "shares": 0.0},
        {"cash": 60000.0, "shares": 180.0},
        {"cash": 25000.0, "shares": 420.0},
    ]


def _split_for_index(idx: int, total: int) -> str:
    if idx < int(total * 0.65):
        return "train"
    if idx < int(total * 0.85):
        return "val"
    return "test"


def _make_trade_decision_records(
    ticker: str,
    dates: list[str],
    lookback_days: int,
    flow_name: str,
) -> list[EvalRecord]:
    records: list[EvalRecord] = []
    portfolios = _portfolio_templates()
    total = len(dates)

    for idx, as_of_date in enumerate(dates):
        split = _split_for_index(idx, total)
        bundle = get_historical_info(ticker, as_of_date, lookback_days=lookback_days)
        for p_idx, portfolio_state in enumerate(portfolios):
            task_id = f"tds::{ticker}::{as_of_date}::p{p_idx}"
            records.append(
                EvalRecord(
                    task_id=task_id,
                    scenario="trade_decision_step",
                    split=split,
                    ticker=ticker,
                    as_of_date=as_of_date,
                    inputs={
                        "ticker": ticker,
                        "flow_name": flow_name,
                        "as_of_date": as_of_date,
                        "portfolio_state": portfolio_state,
                        "lookback_days": lookback_days,
                        "info_bundle": bundle,
                    },
                    metadata={
                        "profile": "decision_eval",
                        "portfolio_template": p_idx,
                    },
                )
            )
    return records


def _make_factor_ranking_records(
    ticker: str,
    dates: list[str],
    lookback_days: int,
    flow_name: str,
) -> list[EvalRecord]:
    records: list[EvalRecord] = []
    horizons = ["short", "medium", "long"]
    total = len(dates)

    for idx, as_of_date in enumerate(dates):
        split = _split_for_index(idx, total)
        bundle = get_historical_info(ticker, as_of_date, lookback_days=lookback_days)
        for horizon in horizons:
            task_id = f"fwr::{ticker}::{as_of_date}::{horizon}"
            records.append(
                EvalRecord(
                    task_id=task_id,
                    scenario="factor_weight_ranking",
                    split=split,
                    ticker=ticker,
                    as_of_date=as_of_date,
                    inputs={
                        "ticker": ticker,
                        "flow_name": flow_name,
                        "as_of_date": as_of_date,
                        "horizon": horizon,
                        "lookback_days": lookback_days,
                        "portfolio_state": {"cash": 100000.0, "shares": 0.0},
                        "candidate_factors": list(bundle.get("candidate_factors", [])),
                        "stock_archetype": bundle.get("stock_archetype", get_stock_archetype(ticker)),
                        "market_regime": bundle.get("market_regime", get_market_regime_label(ticker, as_of_date)),
                        "info_bundle": bundle,
                    },
                    metadata={
                        "profile": "factor_eval",
                    },
                )
            )
    return records


def _seed_decision(bundle: dict[str, Any], ticker: str, as_of_date: str) -> dict[str, Any]:
    stats = bundle.get("summary_stats", {})
    ret_5d = float(stats.get("return_5d_pct", 0.0))
    ret_20d = float(stats.get("return_20d_pct", 0.0))
    if ret_5d > 1.2:
        action, size = "BUY", 0.2
    elif ret_20d < -1.2:
        action, size = "SELL", 0.2
    else:
        action, size = "HOLD", 0.0
    return {
        "as_of_date": as_of_date,
        "ticker": ticker,
        "action": action,
        "size_pct": size,
        "position_size": size,
        "confidence": 0.58,
        "horizon": "short",
        "top_reasons": ["momentum_5d", "momentum_20d"],
        "top_risks": ["event_risk"],
        "invalidation_condition": "Momentum reverses and volatility rises.",
        "factor_scores": {
            "momentum_5d": min(1.0, abs(ret_5d) / 5.0),
            "momentum_20d": min(1.0, abs(ret_20d) / 8.0),
        },
        "rationale": "Seeded baseline decision for reflection eval set generation.",
    }


def _make_reflection_records(
    ticker: str,
    dates: list[str],
    lookback_days: int,
    flow_name: str,
) -> list[EvalRecord]:
    records: list[EvalRecord] = []
    total = len(dates)

    for idx, as_of_date in enumerate(dates):
        split = _split_for_index(idx, total)
        bundle = get_historical_info(ticker, as_of_date, lookback_days=lookback_days)
        decision = _seed_decision(bundle, ticker, as_of_date)
        horizon_days = 5
        forward_return_pct = get_forward_return_pct(ticker, as_of_date, horizon_days=horizon_days)
        task_id = f"ptr::{ticker}::{as_of_date}"
        records.append(
            EvalRecord(
                task_id=task_id,
                scenario="post_trade_reflection",
                split=split,
                ticker=ticker,
                as_of_date=as_of_date,
                inputs={
                    "ticker": ticker,
                    "flow_name": flow_name,
                    "as_of_date": as_of_date,
                    "lookback_days": lookback_days,
                    "original_decision": decision,
                    "future_outcome": {
                        "forward_return_pct": forward_return_pct,
                        "forward_path": get_forward_window(ticker, as_of_date, horizon_days=horizon_days),
                        "benchmark_return_pct": 0.0,
                    },
                    "info_bundle": bundle,
                },
                metadata={"profile": "reflection_eval"},
            )
        )
    return records


def _write_jsonl(path: Path, rows: list[EvalRecord]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(asdict(row), ensure_ascii=True) + "\n")


def _pick_dates(window: list[dict[str, Any]], stride: int) -> list[str]:
    dates = [str(row["date"]) for row in window]
    if stride <= 1:
        return dates
    sampled = dates[::stride]
    if sampled[-1] != dates[-1]:
        sampled.append(dates[-1])
    return sampled


def generate_task_sets(
    out_dir: Path,
    stride: int = 3,
    lookback_days: int = 20,
    flow_name: str = "backtest_showdown",
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    all_trade: list[EvalRecord] = []
    all_factor: list[EvalRecord] = []
    all_reflection: list[EvalRecord] = []

    for ticker in SUPPORTED_TICKERS:
        window = load_backtest_window(ticker, months=3)
        dates = _pick_dates(window[:-1], stride=stride)
        all_trade.extend(_make_trade_decision_records(ticker, dates, lookback_days, flow_name))
        all_factor.extend(_make_factor_ranking_records(ticker, dates, lookback_days, flow_name))
        all_reflection.extend(_make_reflection_records(ticker, dates, lookback_days, flow_name))

    paths = {
        "trade_decision_step": out_dir / "trade_decision_step.jsonl",
        "factor_weight_ranking": out_dir / "factor_weight_ranking.jsonl",
        "post_trade_reflection": out_dir / "post_trade_reflection.jsonl",
    }
    _write_jsonl(paths["trade_decision_step"], all_trade)
    _write_jsonl(paths["factor_weight_ranking"], all_factor)
    _write_jsonl(paths["post_trade_reflection"], all_reflection)

    by_split: dict[str, int] = {}
    for row in [*all_trade, *all_factor, *all_reflection]:
        by_split[row.split] = by_split.get(row.split, 0) + 1

    manifest = {
        "version": "eval-v1",
        "flow_name": flow_name,
        "tickers": list(SUPPORTED_TICKERS),
        "lookback_days": lookback_days,
        "stride": stride,
        "files": {k: str(v) for k, v in paths.items()},
        "counts": {
            "trade_decision_step": len(all_trade),
            "factor_weight_ranking": len(all_factor),
            "post_trade_reflection": len(all_reflection),
            "total": len(all_trade) + len(all_factor) + len(all_reflection),
        },
        "split_counts": by_split,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate eval task sets for Analyst Arena scenarios.")
    parser.add_argument(
        "--out-dir",
        default="task_sets/eval/v1",
        help="Output directory for generated JSONL files.",
    )
    parser.add_argument("--stride", type=int, default=3, help="Sample every Nth trading day.")
    parser.add_argument("--lookback-days", type=int, default=20)
    parser.add_argument("--flow-name", default="backtest_showdown")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    manifest = generate_task_sets(
        out_dir=out_dir,
        stride=max(1, args.stride),
        lookback_days=max(1, args.lookback_days),
        flow_name=args.flow_name,
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
