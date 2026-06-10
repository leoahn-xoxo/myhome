"""리멤버 커리어(Remember) — 로그인 세션으로 추천/검색 포지션 파싱.

리멤버 커리어 웹(career.rememberapp.co.kr)은 로그인해야 공고가 보인다.
A안(실제 프로필)에서는 로그인 세션이 있으므로 추천 포지션을 긁을 수 있다.
SPA라 구조가 자주 바뀌므로 보이는 카드 기준 best-effort로 수집한다.
"""
from __future__ import annotations

import logging
from urllib.parse import quote

from ..models import Job
from .base import debug_dump, safe_text, settle

log = logging.getLogger("jobagent.sources.remember")

# 추천 포지션 + 키워드 검색
RECOMMEND = "https://career.rememberapp.co.kr/job/postings"
SEARCH = "https://career.rememberapp.co.kr/job/postings?keyword={q}"


def _scrape(page, limit: int) -> list[Job]:
    out: list[Job] = []
    cards = page.query_selector_all(
        "a[href*='/job/posting'], li[class*='posting'], div[class*='JobCard'], "
        "div[class*='card'] a[href*='posting']"
    )
    seen = set()
    for c in cards[:limit * 2]:
        href = (c.get_attribute("href") or "")
        if not href or href in seen:
            continue
        seen.add(href)
        title = safe_text(c.query_selector("[class*='title'], h3, strong")) or safe_text(c)
        company = safe_text(c.query_selector("[class*='company'], [class*='corp']"))
        if not title:
            continue
        if href.startswith("/"):
            href = "https://career.rememberapp.co.kr" + href
        out.append(
            Job(
                source="remember",
                title=title.split("\n")[0][:120],
                company=company,
                url=href.split("?")[0],
                description=title,
            )
        )
        if len(out) >= limit:
            break
    return out


def fetch(browser, queries: list[str], limit: int = 20, **_) -> list[Job]:
    jobs: list[Job] = []
    page = browser.new_page()
    try:
        # 1) 로그인 여부 확인 겸 추천 포지션
        try:
            page.goto(RECOMMEND, wait_until="domcontentloaded", timeout=25000)
            settle(page, 2500)
            debug_dump(page, "remember")
            if "login" in page.url or "signin" in page.url:
                log.info("remember: 로그인 필요 → `--login`으로 1회 로그인 후 재시도")
                return []
            jobs.extend(_scrape(page, limit))
        except Exception as e:  # noqa: BLE001
            log.info("remember 추천 수집 실패: %s", e)

        # 2) 키워드 검색 (몇 개만)
        for q in queries[:4]:
            try:
                page.goto(SEARCH.format(q=quote(q)), wait_until="domcontentloaded", timeout=25000)
                settle(page, 2000)
                jobs.extend(_scrape(page, limit))
            except Exception as e:  # noqa: BLE001
                log.info("remember 검색 실패 (%s): %s", q, e)
    finally:
        page.close()
    log.info("remember: %d건 수집", len(jobs))
    return jobs
