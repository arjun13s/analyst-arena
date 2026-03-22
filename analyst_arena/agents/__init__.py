from analyst_arena.agents.base import Agent, ScenarioInputs, ScenarioResult
from analyst_arena.agents.providers import (
    AnthropicAgent,
    GrokAgent,
    HUDModelAgent,
    OpenAIAgent,
    build_real_agents,
)


def build_default_agents() -> dict[str, Agent]:
    return build_real_agents()


__all__ = [
    "Agent",
    "AnthropicAgent",
    "build_default_agents",
    "build_real_agents",
    "GrokAgent",
    "HUDModelAgent",
    "OpenAIAgent",
    "ScenarioInputs",
    "ScenarioResult",
]
