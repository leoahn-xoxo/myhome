"""'이미 본 공고' 영속 저장 — 매일 신규 공고만 알림.

data/seen_jobs.json 에 job.key 목록을 저장한다. GitHub Actions는 실행 후
이 파일을 커밋해서 다음 실행 때 신규 여부를 판별한다.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from .models import Job

log = logging.getLogger("jobagent.dedupe")

STORE = Path(__file__).resolve().parent.parent.parent / "data" / "seen_jobs.json"
_MAX_KEEP = 5000  # 무한 증가 방지


def _load() -> dict:
    if STORE.exists():
        try:
            return json.loads(STORE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def split_new(jobs: list[Job]) -> tuple[list[Job], dict]:
    """기존 store와 비교해 (신규 공고, 갱신된 store) 반환."""
    store = _load()
    seen = store.get("keys", {})
    fresh: list[Job] = []
    for j in jobs:
        if j.key not in seen:
            fresh.append(j)
        seen[j.key] = date.today().isoformat()
    # 오래된 키 정리
    if len(seen) > _MAX_KEEP:
        for k in sorted(seen, key=seen.get)[: len(seen) - _MAX_KEEP]:
            seen.pop(k, None)
    store["keys"] = seen
    store["last_run"] = date.today().isoformat()
    return fresh, store


def save(store: dict) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("seen store 저장: %d keys", len(store.get("keys", {})))
