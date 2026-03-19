from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from analyst_arena.engine.match import MatchResult


DEFAULT_RESULTS_PATH = Path("results.json")


def save_results(results: list[MatchResult], path: str | Path = DEFAULT_RESULTS_PATH) -> None:
    output_path = Path(path)
    payload = [asdict(result) for result in results]
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_results(path: str | Path = DEFAULT_RESULTS_PATH) -> list[MatchResult]:
    input_path = Path(path)
    if not input_path.exists():
        return []
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    return [MatchResult(**item) for item in payload]
