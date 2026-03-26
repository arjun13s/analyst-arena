from __future__ import annotations

import logging
import os
from typing import Any, Callable, Protocol

logger = logging.getLogger(__name__)


def _chat_completion_message_text(message: Any) -> str:
    """Normalize `choice.message.content` (str, or list of structured parts from some gateways)."""
    if message is None:
        return ""
    content = getattr(message, "content", None)
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text" and part.get("text"):
                    parts.append(str(part["text"]))
                elif "text" in part:
                    parts.append(str(part["text"]))
            else:
                text = getattr(part, "text", None)
                parts.append(str(text) if text is not None else str(part))
        return "\n".join(p for p in parts if p).strip()
    return str(content).strip()


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
    """
    HUD gateway models are often exposed on **chat** only (see `hud models` "Routes" column).
    Base OpenAIProvider uses the Responses API (`/v1/responses`); many HUD models reject that with:
    "not available on this endpoint". Default here is chat completions on the same base URL.
    Set HUD_USE_RESPONSES_API=1 to force `responses.create` if a model supports it.
    """

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

        use_responses = os.getenv("HUD_USE_RESPONSES_API", "").strip().lower() in {"1", "true", "yes"}
        if use_responses:
            return super().complete(
                prompt,
                scenario_name=scenario_name,
                agent_name=agent_name,
                inputs=inputs,
            )

        from openai import OpenAI

        api_key = self.api_key or os.getenv("HUD_API_KEY")
        client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        try:
            _mt = int(os.getenv("HUD_CHAT_MAX_TOKENS", "2048"))
        except ValueError:
            _mt = 2048
        try:
            _temp = float(os.getenv("HUD_CHAT_TEMPERATURE", "0.2"))
        except ValueError:
            _temp = 0.2
        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": _mt,
            "temperature": _temp,
        }
        # OpenAI-compatible JSON mode; improves small models that drift into prose. Retry if gateway rejects it.
        want_json = os.getenv("HUD_CHAT_JSON_OBJECT", "1").strip().lower() not in {"0", "false", "no", "off"}
        if want_json:
            create_kwargs["response_format"] = {"type": "json_object"}
        try:
            response = client.chat.completions.create(**create_kwargs)
        except Exception as exc:
            if want_json and "response_format" in create_kwargs:
                logger.debug("HUD chat completions: json_object not accepted (%s), retrying without", exc)
                del create_kwargs["response_format"]
                response = client.chat.completions.create(**create_kwargs)
            else:
                raise
        choice = response.choices[0].message if response.choices else None
        return _chat_completion_message_text(choice)


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
