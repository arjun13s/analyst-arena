from __future__ import annotations

import os
from typing import Any, Callable, Protocol


class ScenarioProvider(Protocol):
    def complete(
        self,
        prompt: str,
        *,
        scenario_name: str,
        agent_name: str,
        inputs: dict[str, Any],
    ) -> str: ...


class CallableProvider:
    def __init__(self, fn: Callable[[str], str]) -> None:
        self._fn = fn

    def complete(
        self,
        prompt: str,
        *,
        scenario_name: str,
        agent_name: str,
        inputs: dict[str, Any],
    ) -> str:
        _ = (scenario_name, agent_name, inputs)
        return self._fn(prompt)


class OpenAIProvider:
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    def complete(
        self,
        prompt: str,
        *,
        scenario_name: str,
        agent_name: str,
        inputs: dict[str, Any],
    ) -> str:
        _ = (scenario_name, agent_name, inputs)
        from openai import OpenAI

        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIProvider")

        client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        response = client.responses.create(model=self.model, input=prompt)
        return getattr(response, "output_text", "") or ""


class HUDInferenceProvider(OpenAIProvider):
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key or os.getenv("HUD_API_KEY"),
            base_url=base_url or os.getenv("HUD_BASE_URL", "https://inference.hud.ai/v1"),
            timeout=timeout,
        )

    def complete(
        self,
        prompt: str,
        *,
        scenario_name: str,
        agent_name: str,
        inputs: dict[str, Any],
    ) -> str:
        _ = (scenario_name, agent_name, inputs)
        if not self.api_key and not os.getenv("HUD_API_KEY"):
            raise ValueError("HUD_API_KEY is required for HUDInferenceProvider")
        return super().complete(
            prompt,
            scenario_name=scenario_name,
            agent_name=agent_name,
            inputs=inputs,
        )


class XAIProvider(OpenAIProvider):
    def __init__(
        self,
        model: str = "grok-3-mini",
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key or os.getenv("XAI_API_KEY"),
            base_url=base_url or os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
            timeout=timeout,
        )

    def complete(
        self,
        prompt: str,
        *,
        scenario_name: str,
        agent_name: str,
        inputs: dict[str, Any],
    ) -> str:
        _ = (scenario_name, agent_name, inputs)
        if not self.api_key and not os.getenv("XAI_API_KEY"):
            raise ValueError("XAI_API_KEY is required for XAIProvider")
        return super().complete(
            prompt,
            scenario_name=scenario_name,
            agent_name=agent_name,
            inputs=inputs,
        )


class AnthropicProvider:
    def __init__(
        self,
        model: str = "claude-3-7-sonnet-latest",
        api_key: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def complete(
        self,
        prompt: str,
        *,
        scenario_name: str,
        agent_name: str,
        inputs: dict[str, Any],
    ) -> str:
        _ = (scenario_name, agent_name, inputs)
        from anthropic import Anthropic

        api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for AnthropicProvider")

        client = Anthropic(api_key=api_key, timeout=self.timeout)
        response = client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
        return "\n".join(parts)
