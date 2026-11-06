"""Configuration loading with environment overrides and no embedded secrets."""

from __future__ import annotations

from copy import deepcopy
from importlib.resources import files
import os
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else Path(str(files("kaji_langgraph").joinpath("config/default.yaml")))
    with config_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    model = config["model"]
    model["name"] = os.getenv("KAJI_MODEL", model["name"])
    model["base_url"] = os.getenv("KAJI_OLLAMA_BASE_URL", model["base_url"])
    return config


def effective_policy(config: dict[str, Any], domain: str) -> dict[str, Any]:
    policy = deepcopy(config["policy"])
    policy.update(config.get("domains", {}).get(domain, {}))
    return policy

