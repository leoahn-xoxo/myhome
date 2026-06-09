"""원티드(Wanted) 공개 검색 JSON API.

엔드포인트: https://www.wanted.co.kr/api/v4/jobs
인증 없이 query 파라미터로 검색 가능. 응답의 data[] 를 정규화한다.
"""
from __future__ import annotations

import logging

from ..models import Job
from .base import get

log = logging.getLogger("jobagent.sources.wanted")

API = "https://www.wanted.co.kr/api/v4/jobs"


def fetch(queries: list[str], limit: int = 20, **_) -> list[Job]:
    jobs: list[Job] = []
    for q in queries:
        params = {
            "country": "kr",
            "job_sort": "job.latest_order",
            "years": "-1",
            "locations": "all",
            "limit": str(limit),
            "offset": "0",
            "query": q,
        }
        try:
            resp = get(API, params=params)
            resp.raise_for_status()
            data = resp.json().get("data", [])
        except Exception as e:  # noqa: BLE001
            log.warning("wanted 검색 실패 (%s): %s", q, e)
            continue

        for item in data:
            jid = str(item.get("id", ""))
            company = (item.get("company") or {}).get("name", "") or item.get("company_name", "")
            address = item.get("address") or {}
            location = address.get("location") or address.get("full_location") or ""
            jobs.append(
                Job(
                    source="wanted",
                    external_id=jid,
                    title=item.get("position", "") or item.get("name", ""),
                    company=company,
                    url=f"https://www.wanted.co.kr/wd/{jid}",
                    location=location,
                    posted=(item.get("confirm_period") or item.get("due_time") or None),
                    description=item.get("position", ""),
                )
            )
    log.info("wanted: %d건 수집", len(jobs))
    return jobs
