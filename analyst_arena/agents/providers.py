from __future__ import annotations

import json
import os
from typing import Any, Callable

from analyst_arena.agents.base import Agent, ScenarioInputs, ScenarioResult
from analyst_arena.engine.scenarios import build_prompt


ProviderCallable = Callable[[str], str]


class JSONPromptAgent(Agent):
    def __init__(self, name: str, provider_name: str, completion_fn: ProviderCallable) -> None:
        super().__init__(name=name)
        self.provider_name = provider_name
        self._completion_fn = completion_fn

    def run_scenario(self, scenario_name: str, inputs: ScenarioInputs) -> ScenarioResult:
        prompt = build_prompt(scenario_name=scenario_name, inputs=inputs)
        raw_response = self._completion_fn(prompt)
        parsed = _parse_response(raw_response)
        parsed["scenario_name"] = scenario_name
        parsed["raw_response"] = raw_response
        metadata = dict(parsed.get("metadata", {}))
        metadata["provider"] = self.provider_name
        parsed["metadata"] = metadata
        return parsed


class OpenAIAgent(JSONPromptAgent):
    def __init__(
        self,
        name: str,
        model: str = "gpt-4o",
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        def completion_fn(prompt: str) -> str:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("openai package is required for OpenAIAgent") from exc

            client = OpenAI(
                api_key=api_key or os.getenv("OPENAI_API_KEY"),
                base_url=base_url,
            )
            response = client.responses.create(
                model=model,
                input=prompt,
            )
            return getattr(response, "output_text", "") or ""

        super().__init__(name=name, provider_name="openai", completion_fn=completion_fn)
        self.model = model


class AnthropicAgent(JSONPromptAgent):
    def __init__(
        self,
        name: str,
        model: str = "claude-3-7-sonnet-latest",
        api_key: str | None = None,
    ) -> None:
        def completion_fn(prompt: str) -> str:
            try:
                from anthropic import Anthropic
            except ImportError as exc:
                raise RuntimeError("anthropic package is required for AnthropicAgent") from exc

            client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model=model,
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}],
            )
            parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
            return "\n".join(parts)

        super().__init__(name=name, provider_name="anthropic", completion_fn=completion_fn)
        self.model = model


class HUDModelAgent(JSONPromptAgent):
    def __init__(
        self,
        name: str,
        model: str,
        completion_fn: ProviderCallable | None = None,
    ) -> None:
        def default_completion(prompt: str) -> str:
            return json.dumps(
                {
                    "thesis_text": (
                        f"{model} placeholder thesis: NVIDIA remains attractive because data center revenue, "
                        "gross margin expansion, and operating leverage support the bull case, but valuation and "
                        "normalization risk should be monitored closely."
                    ),
                    "stance": "bull",
                    "rebuttal_text": (
                        "The opponent underweights software mix, margin durability, and management guidance."
                    ),
                    "rating": "buy",
                    "target_price": 165.0,
                    "rationale": (
                        f"{model} placeholder rationale generated from scenario prompt length={len(prompt)}."
                    ),
                    "metadata": {"model": model, "placeholder": True},
                }
            )

        super().__init__(
            name=name,
            provider_name="hud_model",
            completion_fn=completion_fn or default_completion,
        )
        self.model = model


def _parse_response(raw_response: str) -> ScenarioResult:
    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError:
        payload = {}

    thesis_text = str(payload.get("thesis_text") or raw_response).strip()
    rebuttal_text = str(payload.get("rebuttal_text", "")).strip()
    rationale = str(payload.get("rationale") or thesis_text).strip()
    return ScenarioResult(
        thesis_text=thesis_text,
        stance=str(payload.get("stance", "bull")).strip().lower() or "bull",
        rebuttal_text=rebuttal_text,
        rating=str(payload.get("rating", "hold")).strip().lower() or "hold",
        target_price=float(payload.get("target_price", 0.0) or 0.0),
        rationale=rationale,
        metadata=dict(payload.get("metadata", {})),
    )
