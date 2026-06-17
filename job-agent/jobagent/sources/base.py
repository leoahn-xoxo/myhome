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


# 공고 카드일 가능성이 높은 요소만 추려 tag+class+text를 뽑는 JS.
# 전체 HTML 대신 이 작은 outline 파일이 셀렉터 튜닝의 핵심 단서가 된다.
_OUTLINE_JS = r"""
() => {
  const sel = "a[href*='job'],a[href*='posting'],a[href*='/wd/'],a[href*='rec_idx']," +
              "li,article,[class*='card'],[class*='Card'],[class*='item'],[class*='post']";
  const els = document.querySelectorAll(sel);
  const out = [], seen = new Set();
  for (const el of els) {
    if (out.length >= 70) break;
    const cls = (el.className && el.className.toString) ? el.className.toString() : "";
    const txt = (el.innerText || "").trim().replace(/\s+/g, " ").slice(0, 90);
    if (!txt) continue;
    const key = el.tagName + "|" + cls + "|" + txt;
    if (seen.has(key)) continue; seen.add(key);
    const href = (el.getAttribute && el.getAttribute("href")) || "";
    out.push(`<${el.tagName.toLowerCase()} class="${cls}"` + (href ? ` href="${href}"` : "") + `> ${txt}`);
  }
  return "URL: " + location.href + "\n" + out.join("\n");
}
"""


def debug_dump(page, tag: str) -> None:
    """JOBAGENT_DEBUG=1 일 때 화면 캡처(png) + 전체 HTML + 핵심 outline(txt) 저장.

    셀렉터 튜닝용. outline.txt 는 공고 카드 후보 요소의 tag/class/text만 추린
    작은 파일이라 그대로 붙여넣어 공유하기 쉽다.
    """
    if os.environ.get("JOBAGENT_DEBUG") != "1":
        return
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w.-]", "_", tag)[:60]
    try:
        page.screenshot(path=str(DEBUG_DIR / f"{safe}.png"), full_page=True)
        (DEBUG_DIR / f"{safe}.html").write_text(page.content(), encoding="utf-8")
        try:
            outline = page.evaluate(_OUTLINE_JS)
            (DEBUG_DIR / f"{safe}.outline.txt").write_text(outline, encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            log.warning("debug outline 실패(%s): %s", tag, e)
        log.info("debug 캡처 저장: data/debug/%s.{png,html,outline.txt}", safe)
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
