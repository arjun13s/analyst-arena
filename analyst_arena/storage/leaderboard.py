from __future__ import annotations

import json
from pathlib import Path

from analyst_arena.models import LeaderboardEntry


DEFAULT_LEADERBOARD_PATH = Path("leaderboard.json")


def save_leaderboard(
    entries: list[LeaderboardEntry],
    path: str | Path = DEFAULT_LEADERBOARD_PATH,
) -> None:
    output_path = Path(path)
    payload = [entry.to_dict() for entry in entries]
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_leaderboard(path: str | Path = DEFAULT_LEADERBOARD_PATH) -> list[LeaderboardEntry]:
    input_path = Path(path)
    if not input_path.exists():
        return []
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    entries: list[LeaderboardEntry] = []
    for item in payload:
        try:
            parsed = LeaderboardEntry.from_dict(item)
            if not parsed.agent_name:
                continue
            entries.append(parsed)
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
    return entries
