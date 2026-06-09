"""잡코리아(JobKorea) — 로그인 세션으로 검색 결과 페이지를 파싱."""
from __future__ import annotations

import logging
from urllib.parse import quote

from ..models import Job
from .base import safe_text, settle

log = logging.getLogger("jobagent.sources.jobkorea")

SEARCH = "https://www.jobkorea.co.kr/Search/?stext={q}&tabType=recruit&Page_No=1"


def fetch(browser, queries: list[str], limit: int = 20, **_) -> list[Job]:
    jobs: list[Job] = []
    page = browser.new_page()
    try:
        for q in queries:
            try:
                page.goto(SEARCH.format(q=quote(q)), wait_until="domcontentloaded", timeout=25000)
                settle(page)
            except Exception as e:  # noqa: BLE001
                log.warning("jobkorea 이동 실패 (%s): %s", q, e)
                continue

            rows = page.query_selector_all(
                ".list-default .list-post, .recruit-info .list-post, article.list-item"
            )
            for r in rows[:limit]:
                title_el = r.query_selector(
                    "a.information-title-link, .title a, a.title, .post-list-info a.title"
                )
                comp_el = r.query_selector(".name, .corp-name-link, a.name")
                loc_el = r.query_selector(".option .loc, .work-place")
                href = (title_el.get_attribute("href") if title_el else "") or ""
                title = safe_text(title_el)
                if not (href and title):
                    continue
                if href.startswith("/"):
                    href = "https://www.jobkorea.co.kr" + href
                jobs.append(
                    Job(
                        source="jobkorea",
                        title=title,
                        company=safe_text(comp_el),
                        url=href.split("?")[0],
                        location=safe_text(loc_el),
                        description=title,
                    )
                )
    finally:
        page.close()
    log.info("jobkorea: %d건 수집", len(jobs))
    return jobs
