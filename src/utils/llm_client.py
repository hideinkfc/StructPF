"""LLM client wrapper with retry logic and rate limiting."""

import os
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """Unified client for LLM API calls."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.7):
        self.model = model
        self.temperature = temperature
        self.api_key = os.environ.get("OPENAI_API_KEY")

    def generate(self, messages: list[dict], **kwargs) -> str:
        """Generate a completion from the LLM."""
        raise NotImplementedError("TODO: Implement LLM client")
