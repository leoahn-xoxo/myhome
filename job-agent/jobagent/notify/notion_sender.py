"""Notion 데이터베이스에 채용 공고를 카드로 누적 저장.

필요 환경변수:
  NOTION_TOKEN          Notion 내부 인티그레이션 시크릿
  NOTION_DATABASE_ID    공고를 적재할 데이터베이스 ID

DB는 아래 속성을 가진다고 가정한다(setup_notion.py로 자동 생성 가능):
  포지션(title), 회사(rich_text), 적합도(number), 레벨(select),
  소스(select), 지역(rich_text), URL(url), 등록일(date),
  키워드(multi_select), 상태(select)
URL 기준으로 이미 있으면 건너뛰어 중복 적재를 막는다.
"""
from __future__ import annotations

import logging
import os

import requests

from ..models import Job

log = logging.getLogger("jobagent.notify.notion")

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": VERSION,
        "Content-Type": "application/json",
    }


def _exists(db: str, url: str, headers: dict) -> bool:
    try:
        r = requests.post(
            f"{API}/databases/{db}/query",
            headers=headers,
            json={"filter": {"property": "URL", "url": {"equals": url}}, "page_size": 1},
            timeout=15,
        )
        r.raise_for_status()
        return bool(r.json().get("results"))
    except Exception as e:  # noqa: BLE001
        log.warning("notion 중복확인 실패(%s): %s", url, e)
        return False


def _page_props(job: Job) -> dict:
    props = {
        "포지션": {"title": [{"text": {"content": job.title[:200] or "(제목없음)"}}]},
        "적합도": {"number": round(job.score, 1)},
        "레벨": {"select": {"name": job.level or "실무·기타"}},
        "소스": {"select": {"name": job.source}},
        "상태": {"select": {"name": "신규"}},
    }
    if job.company:
        props["회사"] = {"rich_text": [{"text": {"content": job.company[:200]}}]}
    if job.location:
        props["지역"] = {"rich_text": [{"text": {"content": job.location[:200]}}]}
    if job.url:
        props["URL"] = {"url": job.url}
    if job.posted and _is_iso(job.posted):
        props["등록일"] = {"date": {"start": job.posted[:10]}}
    if job.deadline and _is_iso(job.deadline):
        props["마감일"] = {"date": {"start": job.deadline[:10]}}
    if job.years_required is not None:
        props["연차요구"] = {"number": job.years_required}
    if job.matched_keywords:
        props["키워드"] = {
            "multi_select": [{"name": k[:40]} for k in job.matched_keywords[:8]]
        }
    if job.flags:
        props["플래그"] = {"multi_select": [{"name": f} for f in job.flags]}
    return props


def _is_iso(value: str) -> bool:
    """Notion date에 넣을 수 있는 YYYY-MM-DD 형태인지(상시/텍스트 마감 제외)."""
    import re

    return bool(re.match(r"^\d{4}-\d{2}-\d{2}", value or ""))


def send(jobs: list[Job]) -> int:
    token = os.environ.get("NOTION_TOKEN")
    db = os.environ.get("NOTION_DATABASE_ID")
    if not (token and db):
        log.info("notion: NOTION_TOKEN/NOTION_DATABASE_ID 미설정 → 건너뜀")
        return 0

    headers = _headers(token)
    added = 0
    for job in jobs:
        if job.url and _exists(db, job.url, headers):
            continue
        try:
            r = requests.post(
                f"{API}/pages",
                headers=headers,
                json={"parent": {"database_id": db}, "properties": _page_props(job)},
                timeout=15,
            )
            r.raise_for_status()
            added += 1
        except Exception as e:  # noqa: BLE001
            log.warning("notion 적재 실패(%s): %s", job.title, e)
    log.info("notion: %d건 신규 적재", added)
    return added
