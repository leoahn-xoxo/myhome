"""원티드(Wanted) — 로그인 브라우저 안에서 공개 JSON API를 호출.

페이지 JS 컨텍스트(same-origin)에서 fetch를 실행하므로 쿠키·헤더가 진짜
브라우저 요청과 동일 → 데이터센터 IP 403을 우회한다.
"""
from __future__ import annotations

import logging

from ..models import Job

log = logging.getLogger("jobagent.sources.wanted")

API = "https://www.wanted.co.kr/api/v4/jobs"
_FETCH = """async (url) => {
  const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return await r.json();
}"""


def fetch(browser, queries: list[str], limit: int = 20, **_) -> list[Job]:
    jobs: list[Job] = []
    page = browser.new_page()
    try:
        page.goto("https://www.wanted.co.kr/", wait_until="domcontentloaded", timeout=20000)
        for q in queries:
            url = (
                f"{API}?country=kr&job_sort=job.latest_order&years=-1"
                f"&locations=all&limit={limit}&offset=0&query={q}"
            )
            try:
                data = page.evaluate(_FETCH, url).get("data", [])
            except Exception as e:  # noqa: BLE001
                log.warning("wanted 검색 실패 (%s): %s", q, e)
                continue
            for item in data:
                jid = str(item.get("id", ""))
                company = (item.get("company") or {}).get("name", "") or item.get(
                    "company_name", ""
                )
                addr = item.get("address") or {}
                jobs.append(
                    Job(
                        source="wanted",
                        external_id=jid,
                        title=item.get("position", "") or item.get("name", ""),
                        company=company,
                        url=f"https://www.wanted.co.kr/wd/{jid}",
                        location=addr.get("location") or addr.get("full_location") or "",
                        posted=item.get("confirm_period") or None,
                        deadline=(item.get("due_time") or None),
                        description=item.get("position", ""),
                    )
                )
    finally:
        page.close()
    log.info("wanted: %d건 수집", len(jobs))
    return jobs
