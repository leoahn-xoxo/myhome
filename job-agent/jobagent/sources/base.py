"""소스 공통 유틸 (Playwright 기반).

각 소스는 fetch(browser, queries, limit) 시그니처를 가진다. browser 는
jobagent.browser.Browser 인스턴스로 .new_page() / .request 를 제공한다.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

log = logging.getLogger("jobagent.sources")

DEBUG_DIR = Path(__file__).resolve().parents[2] / "data" / "debug"


def debug_dump(page, tag: str) -> None:
    """JOBAGENT_DEBUG=1 일 때 해당 페이지의 스크린샷+HTML을 저장.

    셀렉터 튜닝용. 0건이 나온 사이트의 실제 화면을 캡처해 원인을 파악한다.
    """
    if os.environ.get("JOBAGENT_DEBUG") != "1":
        return
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w.-]", "_", tag)[:60]
    try:
        page.screenshot(path=str(DEBUG_DIR / f"{safe}.png"), full_page=True)
        (DEBUG_DIR / f"{safe}.html").write_text(page.content(), encoding="utf-8")
        log.info("debug 캡처 저장: data/debug/%s.{png,html}", safe)
    except Exception as e:  # noqa: BLE001
        log.warning("debug 캡처 실패(%s): %s", tag, e)

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


def lazy_scroll(page, times: int = 5, dy: int = 1600, pause: int = 900):
    """지연 로딩(lazy-load) 목록을 끝까지 끌어오기 위해 천천히 스크롤.

    링크드인·리멤버처럼 스크롤해야 카드가 더 붙는 SPA에 필요. 완만한 속도로
    움직여 anti-bot 감지를 피한다.
    """
    for _ in range(times):
        try:
            page.mouse.wheel(0, dy)
        except Exception:  # noqa: BLE001
            break
        page.wait_for_timeout(pause)
