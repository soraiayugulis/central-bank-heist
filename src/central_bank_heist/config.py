"""Configuration: env vars > data/game.yaml > built-in defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_DATA_DIR = Path(__file__).parent / "data"

_DEFAULTS = {
    "time_limit_minutes": 20,
    "repeat_question_threshold": 3,
    "repeat_penalty_minutes": 2,
    "accusation_min_round2_actions": 2,
    "accusation_min_facts": 1,
    "statement_log_max": 10,
}

_ENV_PREFIX = "HEIST_"


@dataclass(frozen=True)
class GameConfig:
    """Tunable game parameters."""

    time_limit_minutes: int = 20
    repeat_question_threshold: int = 3
    repeat_penalty_minutes: int = 2
    accusation_min_round2_actions: int = 2
    accusation_min_facts: int = 1
    statement_log_max: int = 10


@dataclass(frozen=True)
class ProviderConfig:
    """LLM provider settings."""

    provider: str = "scripted"
    model: str = ""
    api_key: str = ""
    base_url: str = ""


def _load_yaml_tunables() -> dict:
    """Load tunables from data/game.yaml if it exists."""
    path = _DATA_DIR / "game.yaml"
    if path.exists():
        with open(path, "r") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    return {}


def _env_int(key: str) -> int | None:
    """Read an int from an env var, or None if unset/empty."""
    val = os.environ.get(f"{_ENV_PREFIX}{key.upper()}")
    if val is not None and val.strip():
        return int(val)
    return None


def load_game_config() -> GameConfig:
    """Load game config with precedence: env > game.yaml > defaults."""
    yaml_vals = _load_yaml_tunables()
    merged: dict = {}
    for key, default in _DEFAULTS.items():
        env_val = _env_int(key)
        if env_val is not None:
            merged[key] = env_val
        elif key in yaml_vals:
            merged[key] = int(yaml_vals[key])
        else:
            merged[key] = default
    return GameConfig(**merged)


def is_debug() -> bool:
    """Check if debug mode is enabled via HEIST_DEBUG=1."""
    return os.environ.get("HEIST_DEBUG", "").strip() in ("1", "true", "yes")


def is_power_up() -> bool:
    """Check if player powers are enabled via HEIST_POWER_UP=1."""
    return os.environ.get("HEIST_POWER_UP", "").strip() in ("1", "true", "yes")


def load_provider_config() -> ProviderConfig:
    """Load LLM provider config from env vars."""
    return ProviderConfig(
        provider=os.environ.get(f"{_ENV_PREFIX}PROVIDER", "scripted").lower(),
        model=os.environ.get(f"{_ENV_PREFIX}MODEL", ""),
        api_key=os.environ.get(f"{_ENV_PREFIX}API_KEY", ""),
        base_url=os.environ.get(f"{_ENV_PREFIX}BASE_URL", ""),
    )
