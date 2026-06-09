"""소스 공통 유틸 (Playwright 기반).

각 소스는 fetch(browser, queries, limit) 시그니처를 가진다. browser 는
jobagent.browser.Browser 인스턴스로 .new_page() / .request 를 제공한다.
"""
from __future__ import annotations

import logging

log = logging.getLogger("jobagent.sources")

# 로그인 세션을 보유한 사이트 도메인 → 최초 로그인 시 방문할 URL
LOGIN_URLS = {
    "wanted": "https://www.wanted.co.kr/",
    "linkedin": "https://www.linkedin.com/jobs/",
    "saramin": "https://www.saramin.co.kr/",
    "jobkorea": "https://www.jobkorea.co.kr/",
    "remember": "https://career.rememberapp.co.kr/",
}


def safe_text(el) -> str:
    try:
        return (el.inner_text() or "").strip() if el else ""
    except Exception:  # noqa: BLE001
        return ""


def settle(page, ms: int = 1500):
    """동적 로딩 대기."""
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:  # noqa: BLE001
        pass
    page.wait_for_timeout(ms)
