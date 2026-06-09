"""설정 로딩."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

_DEFAULT = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: str | None = None) -> dict:
    cfg_path = Path(path or os.environ.get("JOBAGENT_CONFIG", _DEFAULT))
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
