from __future__ import annotations

import os
from typing import Callable

from analyst_arena.agents.base import Agent
from analyst_arena.integrations import (
    AnthropicProvider,
    CallableProvider,
    HUDInferenceProvider,
    HUDClient,
    OpenAIProvider,
    XAIProvider,
)


class OpenAIAgent(Agent):
    def __init__(
        self,
        name: str,
        model: str = "gpt-4o",
        api_key: str | None = None,
        base_url: str | None = None,
        display_name: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            client=HUDClient(default_provider=OpenAIProvider(model=model, api_key=api_key, base_url=base_url)),
            model=model,
            provider="openai",
            display_name=display_name,
        )


class AnthropicAgent(Agent):
    def __init__(
        self,
        name: str,
        model: str = "claude-3-7-sonnet-latest",
        api_key: str | None = None,
        display_name: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            client=HUDClient(default_provider=AnthropicProvider(model=model, api_key=api_key)),
            model=model,
            provider="anthropic",
            display_name=display_name,
        )


class HUDModelAgent(Agent):
    def __init__(
        self,
        name: str,
        model: str,
        completion_fn: Callable[[str], str] | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        display_name: str | None = None,
    ) -> None:
        provider = (
            CallableProvider(completion_fn)
            if completion_fn is not None
            else HUDInferenceProvider(model=model, api_key=api_key, base_url=base_url)
        )
        super().__init__(
            name=name,
            client=HUDClient(default_provider=provider),
            model=model,
            provider="hud",
            display_name=display_name,
        )


class GrokAgent(Agent):
    def __init__(
        self,
        name: str,
        model: str = "grok-3-mini",
        api_key: str | None = None,
        base_url: str | None = None,
        display_name: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            client=HUDClient(default_provider=XAIProvider(model=model, api_key=api_key, base_url=base_url)),
            model=model,
            provider="xai",
            display_name=display_name or "Grok",
        )


def build_real_agents() -> dict[str, Agent]:
    hud_model = os.getenv("HUD_MODEL", "hud-default")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")
    anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")
    grok_model = os.getenv("GROK_MODEL", "grok-3-mini")
    return {
        "hud_model": HUDModelAgent(name="hud_model", model=hud_model, display_name="HUD Agent"),
        "gpt4o": OpenAIAgent(name="gpt4o", model=openai_model, display_name="ChatGPT"),
        "claude": AnthropicAgent(name="claude", model=anthropic_model, display_name="Claude"),
        "grok": GrokAgent(name="grok", model=grok_model, display_name="Grok"),
    }
