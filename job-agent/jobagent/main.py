"""채용 취합 파이프라인 엔트리포인트 (로컬 + 로그인된 크롬).

흐름: (로그인된)크롬 1회 실행 → 소스 수집 → 중복 제거 → 채점/필터 →
신규만 추림 → 정렬/상위 N → 이메일·Notion 발송 → seen store 저장.

사용:
  python -m jobagent.main --login     # (최초 1회) 창 띄워 각 사이트 로그인
  python -m jobagent.main             # 일일 실행(headless, 발송)
  python -m jobagent.main --dry-run   # 발송 없이 결과만 출력
  python -m jobagent.main --headed    # 창을 보면서 실행(디버깅)
  python -m jobagent.main --no-dedupe # 신규 필터 끄고 전체 출력
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from .browser import Browser
from .config import load_config, load_env
from .dedupe import save, split_new
from .models import Job
from .notify import email_sender, notion_sender
from .scoring import passes_filters, score_job
from .sources import REGISTRY
from .sources.base import LOGIN_URLS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("jobagent")


def login_flow(cfg: dict) -> int:
    """전용 프로필에 각 구직 사이트 로그인 세션을 저장(최초 1회)."""
    print("\n각 사이트가 탭으로 열립니다. 로그인(자동로그인 체크 권장)을 마친 뒤")
    print("이 창에 돌아와 Enter를 누르면 세션이 저장됩니다.\n")
    with Browser(cfg, headless=False) as b:
        for name, url in LOGIN_URLS.items():
            if not cfg["sources"].get(name):
                continue
            pg = b.new_page()
            try:
                pg.goto(url, wait_until="domcontentloaded", timeout=30000)
                print(f"  · {name}: {url}")
            except Exception as e:  # noqa: BLE001
                print(f"  · {name} 열기 실패: {e}")
        input("\n모든 사이트 로그인 후 Enter ▶ ")
    print("세션 저장 완료. 이제 `python -m jobagent.main` 으로 일일 실행하세요.")
    return 0


def collect(browser: Browser, cfg: dict) -> list[Job]:
    queries = cfg["queries"]
    jobs: list[Job] = []
    for name, on in cfg["sources"].items():
        if not on or name not in REGISTRY:
            continue
        try:
            jobs.extend(REGISTRY[name](browser, queries))
        except Exception as e:  # noqa: BLE001
            log.warning("%s 소스 전체 실패: %s", name, e)
    return jobs


def dedupe(jobs: list[Job]) -> list[Job]:
    seen: dict[str, Job] = {}
    for j in jobs:
        seen.setdefault(j.key, j)
    return list(seen.values())


def run(dry_run: bool = False, use_dedupe: bool = True, headed: bool = False) -> int:
    cfg = load_config()
    with Browser(cfg, headless=not headed) as browser:
        raw = collect(browser, cfg)
    log.info("총 %d건 수집(중복 포함)", len(raw))

    jobs = dedupe(raw)
    scored = [score_job(j, cfg) for j in jobs]
    kept = [j for j in scored if passes_filters(j, cfg)]
    log.info("필터 통과: %d건", len(kept))

    if use_dedupe:
        fresh, store = split_new(kept)
        log.info("신규 공고: %d건", len(fresh))
    else:
        fresh, store = kept, None

    fresh.sort(key=lambda j: j.score, reverse=True)
    top = fresh[: cfg["filters"]["max_results"]]

    if dry_run:
        print(json.dumps([j.as_dict() for j in top], ensure_ascii=False, indent=2))
        return 0

    email_sender.send(top)
    notion_sender.send(top)
    if store is not None:
        save(store)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="맞춤 채용 취합 에이전트 (로컬+로그인 크롬)")
    p.add_argument("--login", action="store_true", help="최초 1회 사이트 로그인")
    p.add_argument("--dry-run", action="store_true", help="발송 없이 콘솔 출력")
    p.add_argument("--no-dedupe", action="store_true", help="신규 필터 끄기")
    p.add_argument("--headed", action="store_true", help="창 표시(디버깅)")
    args = p.parse_args()
    load_env()
    if args.login:
        return login_flow(load_config())
    return run(dry_run=args.dry_run, use_dedupe=not args.no_dedupe, headed=args.headed)


if __name__ == "__main__":
    sys.exit(main())
