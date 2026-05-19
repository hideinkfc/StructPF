"""Configuration loading and validation."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parents[2]
load_dotenv(_project_root / ".env")


@dataclass(frozen=True)
class Settings:
    """Application settings from .env."""
    vllm_base_url: str
    vllm_model: str
    vllm_max_tokens: int
    vllm_temperature: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            vllm_base_url=os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1"),
            vllm_model=os.environ.get("VLLM_MODEL", "Qwen/Qwen3-14B"),
            vllm_max_tokens=int(os.environ.get("VLLM_MAX_TOKENS", "2048")),
            vllm_temperature=float(os.environ.get("VLLM_TEMPERATURE", "0.7")),
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings.from_env()


def load_config(config_path: str | Path) -> dict:
    """Load a YAML configuration file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f)
