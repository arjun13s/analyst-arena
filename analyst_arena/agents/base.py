from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict


ScenarioInputs = dict[str, Any]


class ScenarioResult(TypedDict, total=False):
    scenario_name: str
    thesis_text: str
    stance: str
    rebuttal_text: str
    rating: str
    target_price: float
    rationale: str
    raw_response: str
    metadata: dict[str, Any]


class Agent(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def run_scenario(self, scenario_name: str, inputs: ScenarioInputs) -> ScenarioResult:
        raise NotImplementedError
