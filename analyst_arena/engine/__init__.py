from __future__ import annotations

from typing import Any

__all__ = ["MatchEngine", "Tournament", "TournamentEngine"]


def __getattr__(name: str) -> Any:
    if name == "MatchEngine":
        from analyst_arena.engine.match import MatchEngine

        return MatchEngine
    if name in {"Tournament", "TournamentEngine"}:
        from analyst_arena.engine.tournament import Tournament, TournamentEngine

        return Tournament if name == "Tournament" else TournamentEngine
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
