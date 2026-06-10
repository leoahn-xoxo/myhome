"""링크드인(LinkedIn) — 로그인 세션으로 채용 검색 페이지를 직접 파싱.

로그인 상태면 차단 없이 검색·추천 공고가 보인다. DOM은 자주 바뀌므로
여러 셀렉터를 관대하게 시도하고, 실패해도 0건으로 빠진다.
"""
from __future__ import annotations

import logging
from urllib.parse import quote

from ..models import Job
from .base import debug_dump, safe_text, settle

log = logging.getLogger("jobagent.sources.linkedin")


def fetch(browser, queries: list[str], limit: int = 20, **_) -> list[Job]:
    jobs: list[Job] = []
    page = browser.new_page()
    try:
        for i, q in enumerate(queries):
            url = (
                "https://www.linkedin.com/jobs/search/?"
                f"keywords={quote(q)}&location={quote('South Korea')}&f_TPR=r604800"
            )
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=25000)
                settle(page)
                if i == 0:
                    debug_dump(page, "linkedin")
            except Exception as e:  # noqa: BLE001
                log.warning("linkedin 이동 실패 (%s): %s", q, e)
                continue

            cards = page.query_selector_all(
                ".job-card-container, li.jobs-search-results__list-item, "
                "div.base-card, li.scaffold-layout__list-item"
            )
            for card in cards[:limit]:
                link = card.query_selector("a.job-card-container__link, a.base-card__full-link, a")
                title_el = card.query_selector(
                    ".job-card-list__title, .base-search-card__title, "
                    "[class*='job-card-list__title']"
                )
                company_el = card.query_selector(
                    ".job-card-container__primary-description, "
                    ".base-search-card__subtitle, [class*='subtitle']"
                )
                loc_el = card.query_selector(
                    ".job-card-container__metadata-item, .job-search-card__location"
                )
                href = (link.get_attribute("href") if link else "") or ""
                title = safe_text(title_el) or safe_text(link)
                if not (href and title):
                    continue
                if href.startswith("/"):
                    href = "https://www.linkedin.com" + href
                jobs.append(
                    Job(
                        source="linkedin",
                        external_id=href.split("/view/")[-1].split("/")[0][:24],
                        title=title,
                        company=safe_text(company_el),
                        url=href.split("?")[0],
                        location=safe_text(loc_el),
                        description=title,
                    )
                )
    finally:
        page.close()
    log.info("linkedin: %d건 수집", len(jobs))
    return jobs
