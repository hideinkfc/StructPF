"""LLM client wrapper for OpenAI-compatible APIs (vLLM / Swiss AI).

Supports both:
  - Euler vLLM (localhost:8000, api_key="none")
  - Swiss AI platform (api.swissai.svc.cscs.ch, api_key from CSCS_SERVING_API)

Roles (via from_role):
  - "generator":   Qwen/Qwen3.5-27B (free-text & structured JSON)
  - "embed":       Snowflake/snowflake-arctic-embed-l-v2.0
    - "judge":       Azure GPT-4.1-mini (classification)
    - "structured":  Azure GPT-4.1-mini (cleaner JSON, less thinking overhead)
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.utils.config import SWISSAI_BASE_URL, get_settings

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

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ):
        settings = get_settings()
        self._base_url = base_url or settings.vllm_base_url
        self._model = model or settings.vllm_model
        self._default_max_tokens = settings.vllm_max_tokens
        self._default_temperature = settings.vllm_temperature

        self._client = OpenAI(base_url=self._base_url, api_key=api_key or "none")
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
        strip_thinking: bool = True,
    ) -> LLMResponse:
        """Generate a completion from a list of messages.

        Args:
            messages: OpenAI-format messages [{"role": "...", "content": "..."}]
            max_tokens: Max tokens to generate (default from .env)
            temperature: Sampling temperature (default from .env)
            top_p: Nucleus sampling parameter
            stop: Stop sequences
            strip_thinking: Remove the 'Thinking Process:' preamble (Qwen3.5).

        Returns:
            LLMResponse with generated text and metadata
        """
        request = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self._default_temperature,
            "top_p": top_p,
            "stop": stop,
        }
        token_limit = max_tokens or self._default_max_tokens
        if self._model.startswith("deepseek-ai/"):
            # DeepSeek's reasoning deployments expect the newer completion
            # budget field; max_tokens can leave the final answer empty.
            request["max_completion_tokens"] = token_limit
        else:
            request["max_tokens"] = token_limit

        response = self._client.chat.completions.create(**request)

        choice = response.choices[0]
        text = choice.message.content or ""
        if strip_thinking:
            text = _strip_thinking(text)

        self._usage.update(response.usage)

        return LLMResponse(
            text=text,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
            model=response.model,
            finish_reason=choice.finish_reason or "",
        )

    @classmethod
    def from_role(
        cls,
        role: Literal["generator", "embed", "judge", "structured"],
        settings = None,
    ) -> "LLMClient":
        """Create a client for a specific role.

        Args:
            role: "generator" (Qwen3.5-27B, free-text), "embed" (Arctic-embed),
                  or "judge"/"structured" (Azure GPT-4.1-mini, reliable JSON).
            settings: Optional Settings instance (loaded fresh if omitted).

        Returns:
            Configured LLMClient for the selected backend.
        """
        from src.utils.config import (
            SWISSAI_DEFAULT_EMBED,
            SWISSAI_DEFAULT_GENERATOR,
            SWISSAI_DEFAULT_JUDGE,
            load_azure_judge_config,
        )

        if settings is None:
            settings = get_settings()

        if role in {"judge", "structured"}:
            base_url, api_key, model = load_azure_judge_config()
            return cls(base_url=base_url, model=model, api_key=api_key)

        model_map = {
            "generator":  (settings.swissai_generator_model or SWISSAI_DEFAULT_GENERATOR),
            "embed":      (settings.swissai_embed_model or SWISSAI_DEFAULT_EMBED),
            "judge":      (settings.swissai_judge_model or SWISSAI_DEFAULT_JUDGE),
            "structured": (settings.swissai_judge_model or SWISSAI_DEFAULT_JUDGE),
        }

        return cls(
            base_url=settings.swissai_base_url or SWISSAI_BASE_URL,
            model=model_map[role],
            api_key=settings.swissai_api_key,
        )

    def embed(
        self,
        texts: str | list[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        """Generate embeddings via the OpenAI-compatible embeddings endpoint.

        Args:
            texts: Single string or list of strings to embed.
            model: Embedding model name (defaults to the client's model).

        Returns:
            List of embedding vectors (one per input text).
        """
        if isinstance(texts, str):
            texts = [texts]

        embeddings = []
        for start in range(0, len(texts), 2048):
            response = self._client.embeddings.create(
                model=model or self._model,
                input=texts[start:start + 2048],
            )
            sorted_data = sorted(response.data, key=lambda x: x.index)
            embeddings.extend(d.embedding for d in sorted_data)
        return embeddings

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

        # Try direct parse first; fall back to JSON extraction from text
        try:
            return schema.model_validate_json(text)
        except (json.JSONDecodeError, ValidationError):
            extracted = _extract_json(text)
            if extracted:
                return schema.model_validate_json(extracted)
            raise

# ── Helpers ──────────────────────────────────────────────────────────────────


def _strip_thinking(text: str) -> str:
    """Remove the Qwen3.5 thinking preamble from model output.

    Qwen3.5 models emit an internal reasoning chain before the actual answer.
    Handles both formats: `<think>...</think>` tags and "Thinking Process:" header.
    """
    result = text.strip()

    # Some Qwen deployments place the reasoning and final answer in the same
    # content field, ending the reasoning with </think>. Prefer everything
    # after the final closing tag; numbered items in the consolidation note
    # must not be mistaken for reasoning steps.
    closing_tags = list(re.finditer(r"</think>", result, flags=re.IGNORECASE))
    if closing_tags:
        result = result[closing_tags[-1].end():].strip()
        result = re.sub(r"</?think>", "", result, flags=re.IGNORECASE).strip()
        return result if result else text.strip()

    # Format 1: <think>...</think> tags
    if result.lower().startswith("<think>"):
        end_idx = result.find("</think>")
        if end_idx != -1:
            result = result[end_idx + len("</think>"):].strip()

    # Format 2: "Thinking Process:" header (may coexist with format 1)
    for marker in ("Thinking Process:", "Thinking process:"):
        idx = result.find(marker)
        if idx != -1:
            rest = result[idx + len(marker):].strip()
            # If a model omits </think>, locate the final structured answer
            # instead of using the last numbered line (which may be a valid
            # student attempt inside CONSOLIDATION NOTE).
            section_starts = list(re.finditer(
                r"(?im)^\s*(?:\d+[.)]\s*)?(?:\*\*)?TOPIC\b", rest,
            ))
            for section_start in reversed(section_starts):
                candidate = rest[section_start.start():].strip()
                if re.search(r"(?im)^\s*(?:\d+[.)]\s*)?(?:\*\*)?NARRATIVE\b", candidate):
                    result = candidate
                    break
            else:
                lines = rest.split("\n")
                # Find the last numbered step
                last_step = -1
                for i, line in enumerate(lines):
                    if re.match(r"^\d+\.\s", line.strip()):
                        last_step = i
                if last_step >= 0:
                    result = "\n".join(lines[last_step + 1:]).strip()
                else:
                    result = rest
            break

    # Final cleanup: strip any remaining <think>/</think> artifacts
    result = re.sub(r"</?think>", "", result).strip()

    return result if result else text.strip()


def _extract_json(text: str) -> str | None:
    """Extract the LAST valid JSON object from text (right-to-left).

    Qwen3.5's thinking output often contains JSON schema fragments before
    the actual answer JSON. By scanning right-to-left we prefer the final
    (answer) JSON over intermediate schema copies.

    Objects `{...}` are preferred over arrays `[...]` to ensure the
    extracted JSON matches the expected structured schema.
    Skips objects that look like JSON schemas (have "properties" key).
    Returns None if no valid JSON is found.
    """
    # Find all {...} object candidates using stack-based brace matching
    def _find_balanced(pairs: list[tuple[str, str]]) -> list[str]:
        """Find top-level balanced spans for the given brace pairs."""
        open_chars = {o for o, _ in pairs}
        close_map = {c: o for o, c in pairs}
        candidates = []
        stack = []
        for i, ch in enumerate(text):
            if ch in open_chars:
                stack.append((ch, i))
            elif ch in close_map and stack:
                expected_open = close_map[ch]
                if stack[-1][0] == expected_open:
                    _, start = stack.pop()
                    if not stack:
                        candidates.append(text[start:i + 1])
        return candidates

    # Collect candidates: objects first (preferred), then arrays
    obj_candidates = _find_balanced([("{", "}")])
    arr_candidates = _find_balanced([("[", "]")])

    # Check all object candidates (right-to-left), then array candidates
    for candidate in reversed(obj_candidates):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict) and "properties" in parsed:
                continue
            return candidate
        except json.JSONDecodeError:
            continue

    # Fall back to array candidates if no valid object found
    for candidate in reversed(arr_candidates):
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue
    return None

