"""LLM client wrapper for vLLM on Euler.

Connects to the vLLM server via SSH tunnel (localhost:8000).
Uses the OpenAI SDK as a generic HTTP client for the OpenAI-compatible API.
"""

import json
import logging
from dataclasses import dataclass, field

from openai import OpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.utils.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Track token usage across calls."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_calls: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def update(self, usage) -> None:
        if usage:
            self.prompt_tokens += usage.prompt_tokens or 0
            self.completion_tokens += usage.completion_tokens or 0
            self.total_calls += 1


@dataclass
class LLMResponse:
    """Structured response from the LLM."""
    text: str
    usage: dict = field(default_factory=dict)
    model: str = ""
    finish_reason: str = ""


class LLMClient:
    """Client for calling vLLM on Euler via the OpenAI-compatible API."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        settings = get_settings()
        self._base_url = base_url or settings.vllm_base_url
        self._model = model or settings.vllm_model
        self._default_max_tokens = settings.vllm_max_tokens
        self._default_temperature = settings.vllm_temperature

        self._client = OpenAI(base_url=self._base_url, api_key="none")
        self._usage = TokenUsage()

    @property
    def model(self) -> str:
        return self._model

    @property
    def usage(self) -> TokenUsage:
        return self._usage

    def is_available(self) -> bool:
        """Check if the vLLM server is reachable."""
        try:
            self._client.models.list()
            return True
        except Exception:
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float = 0.95,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Generate a completion from a list of messages.

        Args:
            messages: OpenAI-format messages [{"role": "...", "content": "..."}]
            max_tokens: Max tokens to generate (default from .env)
            temperature: Sampling temperature (default from .env)
            top_p: Nucleus sampling parameter
            stop: Stop sequences

        Returns:
            LLMResponse with generated text and metadata
        """
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=max_tokens or self._default_max_tokens,
            temperature=temperature if temperature is not None else self._default_temperature,
            top_p=top_p,
            stop=stop,
        )

        choice = response.choices[0]
        self._usage.update(response.usage)

        return LLMResponse(
            text=choice.message.content or "",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
            model=response.model,
            finish_reason=choice.finish_reason or "",
        )

    def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        **kwargs,
    ) -> str:
        """Convenience: generate text from a simple prompt string."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.generate(messages, **kwargs).text

    def generate_batch(
        self,
        prompts: list[str],
        *,
        system: str | None = None,
        **kwargs,
    ) -> list[LLMResponse]:
        """Generate completions for a batch of prompts sequentially."""
        results = []
        for prompt in prompts:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            results.append(self.generate(messages, **kwargs))
        return results

    def generate_structured(
        self,
        messages: list[dict[str, str]],
        schema: type[BaseModel],
        **kwargs,
    ) -> BaseModel:
        """Generate and parse response into a Pydantic model.

        Injects the JSON schema into the system prompt and parses the output.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        system_suffix = (
            f"\n\nRespond ONLY with valid JSON matching this schema:\n{schema_json}"
        )

        messages = list(messages)
        if messages and messages[0]["role"] == "system":
            messages[0] = {
                "role": "system",
                "content": messages[0]["content"] + system_suffix,
            }
        else:
            messages = [{"role": "system", "content": system_suffix.strip()}] + messages

        response = self.generate(messages, **kwargs)

        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        return schema.model_validate_json(text)

