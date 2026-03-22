from __future__ import annotations

from typing import Any

from analyst_arena.engine.scenarios import build_prompt
from analyst_arena.integrations.providers import ScenarioProvider
from analyst_arena.integrations.response import normalize_scenario_result


class HUDClient:
    def __init__(
        self,
        provider_registry: dict[str, ScenarioProvider] | None = None,
        default_provider: ScenarioProvider | None = None,
    ) -> None:
        self._provider_registry = dict(provider_registry or {})
        self._default_provider = default_provider

    def register_provider(self, agent_name: str, provider: ScenarioProvider) -> None:
        self._provider_registry[agent_name] = provider

    def run_scenario(self, scenario_name: str, agent_name: str, inputs: dict[str, Any]) -> dict[str, Any]:
        provider = self._provider_registry.get(agent_name, self._default_provider)
        if provider is None:
            raise ValueError(f"No provider registered for agent '{agent_name}'")
        prompt = build_prompt(scenario_name=scenario_name, inputs=inputs, agent_name=agent_name)
        raw_response = provider.complete(
            prompt,
            scenario_name=scenario_name,
            agent_name=agent_name,
            inputs=inputs,
        )
        result = normalize_scenario_result(raw_response, scenario_name)
        metadata = dict(result.get("metadata", {}))
        metadata["agent_name"] = agent_name
        result["metadata"] = metadata
        return result
