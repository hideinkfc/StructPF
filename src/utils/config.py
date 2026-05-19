"""Configuration loading and validation."""

from pathlib import Path
import yaml


def load_config(config_path: str | Path) -> dict:
    """Load a YAML configuration file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f)
