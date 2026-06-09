"""잡코리아(JobKorea) best-effort 스크래핑.

공식 공개 API가 없어 검색 결과 페이지 HTML을 파싱한다. 잡코리아는 봇 차단이
잦으므로 실패하면 조용히 0건을 반환한다(파이프라인을 막지 않음).
"""
from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from ..models import Job
from .base import get

log = logging.getLogger("jobagent.sources.jobkorea")

SEARCH = "https://www.jobkorea.co.kr/Search/"


def fetch(queries: list[str], limit: int = 20, **_) -> list[Job]:
    jobs: list[Job] = []
    for q in queries:
        try:
            resp = get(SEARCH, params={"stext": q, "tabType": "recruit"})
            if resp.status_code != 200:
                log.info("jobkorea %s -> HTTP %s (skip)", q, resp.status_code)
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:  # noqa: BLE001
            log.info("jobkorea 검색 실패 (%s): %s (skip)", q, e)
            continue

        # 잡코리아 마크업은 자주 바뀌므로 여러 셀렉터를 관대하게 시도한다.
        rows = soup.select("a.information-title-link, a.title, .list-default .post .title a")
        for a in rows[:limit]:
            href = a.get("href", "")
            if not href:
                continue
            if href.startswith("/"):
                href = "https://www.jobkorea.co.kr" + href
            title = a.get_text(strip=True)
            if not title:
                continue
            jobs.append(
                Job(
                    source="jobkorea",
                    title=title,
                    company="",
                    url=href.split("?")[0],
                    description=title,
                )
            )
    log.info("jobkorea: %d건 수집", len(jobs))
    return jobs
