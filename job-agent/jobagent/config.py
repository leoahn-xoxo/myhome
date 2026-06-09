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


def load_env() -> None:
    """job-agent/.env 가 있으면 환경변수로 로드(이미 설정된 값은 유지).

    이메일/Notion 시크릿을 로컬에서 간편히 쓰기 위함. python-dotenv 불필요.
    """
    env_path = _DEFAULT.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)
