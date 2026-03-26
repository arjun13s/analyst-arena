from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from run_tournament import (
    DEFAULT_LEADERBOARD_PATH,
    DEFAULT_RESULTS_PATH,
    get_leaderboard,
    run_match,
)


class MatchRequest(BaseModel):
    agent_a: str = Field(default="hud_model")
    agent_b: str = Field(default="gpt4o")
    ticker: str = Field(default="NVDA")
    months: int = Field(default=1, ge=1, le=12)
    starting_cash: float = Field(default=100000.0, gt=0.0)
    results_path: str | None = None
    leaderboard_path: str | None = None


app = FastAPI(title="Analyst Arena API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/match")
def create_match(payload: MatchRequest) -> dict[str, Any]:
    try:
        return run_match(
            payload.agent_a,
            payload.agent_b,
            ticker=payload.ticker,
            months=payload.months,
            starting_cash=payload.starting_cash,
            results_path=Path(payload.results_path) if payload.results_path else DEFAULT_RESULTS_PATH,
            leaderboard_path=Path(payload.leaderboard_path) if payload.leaderboard_path else DEFAULT_LEADERBOARD_PATH,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/leaderboard")
def leaderboard() -> list[dict[str, Any]]:
    return get_leaderboard()
