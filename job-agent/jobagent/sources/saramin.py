"""사람인(Saramin) — 로그인 세션으로 검색 결과 페이지를 파싱.

로그인 상태면 맞춤 정보가 반영되고 차단이 줄어든다. 공식 오픈 API 대신
브라우저로 직접 본다(키 불필요).
"""
from __future__ import annotations

import logging
from urllib.parse import quote

from ..models import Job
from .base import debug_dump, safe_text, settle

log = logging.getLogger("jobagent.sources.saramin")

SEARCH = "https://www.saramin.co.kr/zf_user/search/recruit?searchType=search&searchword={q}&sort=RD"


def fetch(browser, queries: list[str], limit: int = 20, **_) -> list[Job]:
    jobs: list[Job] = []
    page = browser.new_page()
    try:
        for i, q in enumerate(queries):
            try:
                page.goto(SEARCH.format(q=quote(q)), wait_until="domcontentloaded", timeout=25000)
                settle(page)
                if i == 0:
                    debug_dump(page, "saramin")
            except Exception as e:  # noqa: BLE001
                log.warning("saramin 이동 실패 (%s): %s", q, e)
                continue

            items = page.query_selector_all(".item_recruit, .list_item, [class*='item_recruit']")
            for it in items[:limit]:
                title_el = it.query_selector(".job_tit a, h2.job_tit a, .str_tit")
                comp_el = it.query_selector(".corp_name a, .company_nm a, .corp_name")
                cond_el = it.query_selector(".job_condition")
                date_el = it.query_selector(".job_date .date, .support_detail .date")
                href = (title_el.get_attribute("href") if title_el else "") or ""
                title = safe_text(title_el)
                if not (href and title):
                    continue
                if href.startswith("/"):
                    href = "https://www.saramin.co.kr" + href
                jobs.append(
                    Job(
                        source="saramin",
                        title=title,
                        company=safe_text(comp_el),
                        url=href.split("?")[0] if "rec_idx" not in href else href,
                        location=safe_text(cond_el).split("\n")[0],
                        posted=safe_text(date_el) or None,
                        description=f"{title} {safe_text(cond_el)}",
                    )
                )
    finally:
        page.close()
    log.info("saramin: %d건 수집", len(jobs))
    return jobs
