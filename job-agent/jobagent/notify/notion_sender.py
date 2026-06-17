"""Notion 데이터베이스에 채용 공고를 카드로 누적 저장 (스키마 적응형).

필요 환경변수:
  NOTION_TOKEN          Notion 내부 인티그레이션 시크릿
  NOTION_DATABASE_ID    공고를 적재할 데이터베이스 ID

DB의 실제 속성 타입을 읽어 거기에 맞춰 값을 기록한다. 사용자가 Notion에서
속성 타입을 바꾸거나(number→text 등) 이름을 바꿔도 깨지지 않는다.
- select / multi_select 는 '이미 존재하는 옵션'만 채운다(수동 큐레이션 보존).
- 지원여부/결과 같은 수동 관리 항목은 기본값만 넣거나 비워둔다.
URL 기준으로 이미 있으면 건너뛰어 중복 적재를 막는다.
"""
from __future__ import annotations

import logging
import os
import re

import requests

from ..models import Job

log = logging.getLogger("jobagent.notify.notion")

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": VERSION,
        "Content-Type": "application/json",
    }


def _get_schema(db: str, headers: dict) -> dict:
    """{속성명: {'type':..., 'options': set(...)}} 형태로 현재 스키마를 읽는다."""
    r = requests.get(f"{API}/databases/{db}", headers=headers, timeout=15)
    r.raise_for_status()
    props = r.json().get("properties", {})
    schema = {}
    for name, spec in props.items():
        t = spec.get("type")
        opts = set()
        if t in ("select", "multi_select", "status"):
            cfg = spec.get(t, {})
            opts = {o["name"] for o in cfg.get("options", [])}
        schema[name] = {"type": t, "options": opts}
    return schema


def _coerce(name: str, value, meta: dict):
    """canonical 값을 해당 속성 타입에 맞는 Notion 프로퍼티로 변환. 불가하면 None."""
    if value in (None, "", []):
        return None
    t = meta["type"]
    if t == "title":
        return {"title": [{"text": {"content": str(value)[:200]}}]}
    if t == "rich_text":
        text = f"{value}년+" if name == "연차요구" else str(value)
        return {"rich_text": [{"text": {"content": text[:1900]}}]}
    if t == "number":
        try:
            return {"number": float(value)}
        except (TypeError, ValueError):
            return None
    if t == "url":
        return {"url": str(value)}
    if t == "select":
        return {"select": {"name": str(value)}} if str(value) in meta["options"] else None
    if t == "multi_select":
        vals = value if isinstance(value, (list, tuple)) else [value]
        keep = [{"name": v} for v in vals if v in meta["options"]]
        return {"multi_select": keep} if keep else None
    if t in ("date",):
        s = str(value)
        return {"date": {"start": s[:10]}} if _ISO.match(s) else None
    return None


def _canonical(job: Job) -> dict:
    """우리가 채울 수 있는 표준 값들. 키 = Notion 속성명."""
    return {
        "포지션": job.title,
        "회사": job.company,
        "적합도": round(job.score, 1),
        "레벨": job.level,
        "소스": job.source,
        "지역": job.location,
        "URL": job.url,
        "등록일": job.posted,
        "마감일": job.deadline,
        "연차요구": job.years_required,
        "키워드": job.matched_keywords,
        "플래그": job.flags,
        "지원여부": "미지원",   # 수동 관리지만 초기값만 세팅
        "상태": "신규",
    }


def _props(job: Job, schema: dict) -> dict:
    out = {}
    for name, value in _canonical(job).items():
        meta = schema.get(name)
        if not meta:
            continue
        coerced = _coerce(name, value, meta)
        if coerced is not None:
            out[name] = coerced
    return out


def _url_prop_name(schema: dict) -> str | None:
    """중복 판별에 쓸 url 타입 속성명을 찾는다(보통 'URL')."""
    if schema.get("URL", {}).get("type") == "url":
        return "URL"
    for name, meta in schema.items():
        if meta["type"] == "url":
            return name
    return None


def _exists(db: str, url_name: str, url: str, headers: dict) -> bool:
    try:
        r = requests.post(
            f"{API}/databases/{db}/query",
            headers=headers,
            json={"filter": {"property": url_name, "url": {"equals": url}}, "page_size": 1},
            timeout=15,
        )
        r.raise_for_status()
        return bool(r.json().get("results"))
    except Exception as e:  # noqa: BLE001
        log.warning("notion 중복확인 실패(%s): %s", url, e)
        return False


def send(jobs: list[Job]) -> int:
    token = os.environ.get("NOTION_TOKEN")
    db = os.environ.get("NOTION_DATABASE_ID")
    if not (token and db):
        log.info("notion: NOTION_TOKEN/NOTION_DATABASE_ID 미설정 → 건너뜀")
        return 0

    headers = _headers(token)
    try:
        schema = _get_schema(db, headers)
    except Exception as e:  # noqa: BLE001
        log.error("notion 스키마 조회 실패: %s", e)
        return 0
    url_name = _url_prop_name(schema)

    added = 0
    for job in jobs:
        if url_name and job.url and _exists(db, url_name, job.url, headers):
            continue
        try:
            r = requests.post(
                f"{API}/pages",
                headers=headers,
                json={"parent": {"database_id": db}, "properties": _props(job, schema)},
                timeout=15,
            )
            r.raise_for_status()
            added += 1
        except Exception as e:  # noqa: BLE001
            log.warning("notion 적재 실패(%s): %s", job.title, e)
    log.info("notion: %d건 신규 적재", added)
    return added
