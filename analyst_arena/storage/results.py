from __future__ import annotations

import json
from pathlib import Path

from analyst_arena.models import MatchResult


DEFAULT_RESULTS_PATH = Path("match_results.json")


def save_results(results: list[MatchResult], path: str | Path = DEFAULT_RESULTS_PATH) -> None:
    output_path = Path(path)
    payload = [result.to_dict() for result in results]
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_results(path: str | Path = DEFAULT_RESULTS_PATH) -> list[MatchResult]:
    input_path = Path(path)
    if not input_path.exists():
        return []
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    results: list[MatchResult] = []
    for item in payload:
        try:
            parsed = MatchResult.from_dict(item)
            if not parsed.agent_a_result.agent.name or not parsed.agent_b_result.agent.name:
                continue
            results.append(parsed)
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
    return results


def append_result(result: MatchResult, path: str | Path = DEFAULT_RESULTS_PATH) -> list[MatchResult]:
    results = load_results(path)
    results.append(result)
    save_results(results, path)
    return results
