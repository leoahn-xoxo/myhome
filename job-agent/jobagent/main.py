"""채용 취합 파이프라인 엔트리포인트.

흐름: 소스 수집 → 중복 제거 → 채점/필터 → 신규만 추림 → 정렬/상위 N →
이메일·Notion 발송 → seen store 저장.

사용:
  python -m jobagent.main                # 전체 실행
  python -m jobagent.main --dry-run      # 발송 없이 콘솔 출력만
  python -m jobagent.main --no-dedupe    # 신규 필터 끄고 전체 출력
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from .config import load_config
from .dedupe import save, split_new
from .models import Job
from .notify import email_sender, notion_sender
from .scoring import passes_filters, score_job
from .sources import REGISTRY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("jobagent")


def collect(cfg: dict) -> list[Job]:
    queries = cfg["queries"]
    enabled = cfg["sources"]
    jobs: list[Job] = []
    for name, on in enabled.items():
        if not on or name not in REGISTRY:
            continue
        try:
            jobs.extend(REGISTRY[name](queries))
        except Exception as e:  # noqa: BLE001
            log.warning("%s 소스 전체 실패: %s", name, e)
    return jobs


def dedupe(jobs: list[Job]) -> list[Job]:
    seen: dict[str, Job] = {}
    for j in jobs:
        # 같은 key는 점수 매기기 전이므로 먼저 들어온 것 유지
        seen.setdefault(j.key, j)
    return list(seen.values())


def run(dry_run: bool = False, use_dedupe: bool = True) -> int:
    cfg = load_config()
    raw = collect(cfg)
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
    p = argparse.ArgumentParser(description="맞춤 채용 취합 에이전트")
    p.add_argument("--dry-run", action="store_true", help="발송 없이 콘솔 출력")
    p.add_argument("--no-dedupe", action="store_true", help="신규 필터 끄기")
    args = p.parse_args()
    return run(dry_run=args.dry_run, use_dedupe=not args.no_dedupe)


if __name__ == "__main__":
    sys.exit(main())
