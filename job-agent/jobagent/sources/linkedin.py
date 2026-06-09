"""링크드인(LinkedIn) 게스트 채용 검색.

로그인 없이 접근 가능한 게스트 API:
  https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
HTML 카드 목록을 돌려주므로 BeautifulSoup으로 파싱한다. 레이트리밋이 있어
요청 간 약간의 간격을 두고, 실패해도 다른 소스에 영향이 없도록 처리한다.
"""
from __future__ import annotations

import logging
import time

from bs4 import BeautifulSoup

from ..models import Job
from .base import get

log = logging.getLogger("jobagent.sources.linkedin")

API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"


def fetch(queries: list[str], location: str = "South Korea", limit: int = 20, **_) -> list[Job]:
    jobs: list[Job] = []
    for q in queries:
        params = {"keywords": q, "location": location, "start": "0", "f_TPR": "r604800"}
        try:
            resp = get(API, params=params)
            if resp.status_code != 200:
                log.warning("linkedin %s -> HTTP %s", q, resp.status_code)
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:  # noqa: BLE001
            log.warning("linkedin 검색 실패 (%s): %s", q, e)
            continue

        cards = soup.select("li")[:limit]
        for card in cards:
            title_el = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle")
            link_el = card.select_one("a.base-card__full-link")
            loc_el = card.select_one(".job-search-card__location")
            date_el = card.select_one("time")
            if not (title_el and link_el):
                continue
            url = link_el.get("href", "").split("?")[0]
            jobs.append(
                Job(
                    source="linkedin",
                    external_id=url.rstrip("/").split("-")[-1],
                    title=title_el.get_text(strip=True),
                    company=company_el.get_text(strip=True) if company_el else "",
                    url=url,
                    location=loc_el.get_text(strip=True) if loc_el else "",
                    posted=date_el.get("datetime") if date_el else None,
                    description=title_el.get_text(strip=True),
                )
            )
        time.sleep(1.0)  # 레이트리밋 회피
    log.info("linkedin: %d건 수집", len(jobs))
    return jobs
