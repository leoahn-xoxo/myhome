"""사람인(Saramin) 공식 오픈 API.

문서: https://oapi.saramin.co.kr/guide  (무료 발급)
SARAMIN_API_KEY 환경변수가 있으면 사용하고, 없으면 조용히 건너뛴다.
(키 없이 HTML 스크래핑은 차단/약관 이슈가 커서 공식 API만 지원.)
"""
from __future__ import annotations

import logging
import os

from ..models import Job
from .base import get

log = logging.getLogger("jobagent.sources.saramin")

API = "https://oapi.saramin.co.kr/job-search"


def fetch(queries: list[str], limit: int = 20, **_) -> list[Job]:
    key = os.environ.get("SARAMIN_API_KEY")
    if not key:
        log.info("saramin: SARAMIN_API_KEY 없음 → 건너뜀 (README의 발급 안내 참고)")
        return []

    jobs: list[Job] = []
    for q in queries:
        params = {
            "access-key": key,
            "keywords": q,
            "sort": "pd",          # 등록일순
            "count": str(limit),
            "fields": "posting-date,expiration-date",
        }
        try:
            resp = get(API, params=params, headers={"Accept": "application/json"})
            resp.raise_for_status()
            items = resp.json().get("jobs", {}).get("job", [])
        except Exception as e:  # noqa: BLE001
            log.warning("saramin 검색 실패 (%s): %s", q, e)
            continue

        if isinstance(items, dict):
            items = [items]
        for it in items:
            company = ((it.get("company") or {}).get("detail") or {}).get("name", "")
            position = it.get("position") or {}
            title = (position.get("title") or "")
            loc = ((position.get("location") or {}).get("name") or "")
            ind = ((position.get("industry") or {}).get("name") or "")
            jobs.append(
                Job(
                    source="saramin",
                    external_id=str(it.get("id", "")),
                    title=title,
                    company=company,
                    url=it.get("url", ""),
                    location=loc,
                    posted=_to_date(it.get("posting-date")),
                    description=f"{title} {ind}",
                )
            )
    log.info("saramin: %d건 수집", len(jobs))
    return jobs


def _to_date(value):
    # 사람인은 RFC822 형태(예: "2024-05-01T09:00:00+09:00")로 줄 때가 많다.
    if not value:
        return None
    return value[:10]
