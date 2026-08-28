"""
loader.py

Single entry point for reading config.yaml. Every module that needs an
operational knob (thresholds, weights-as-numbers, allowed tools) calls
get_config() instead of parsing YAML itself, and instead of hardcoding
the value inline.
"""

from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent / "config.yaml"


@lru_cache(maxsize=1)
def get_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def reload_config() -> dict:
    """Clears the cache and re-reads config.yaml — useful in tests that
    need to simulate a config change without restarting the process."""
    get_config.cache_clear()
    return get_config()
