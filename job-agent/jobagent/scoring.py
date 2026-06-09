"""프로필 적합도 채점.

점수는 '나에게 맞는 정도 + 지원 적합도'를 하나의 숫자로 환산한 것.
키워드 매칭(직무/도메인/시니어) + 제목 가중 + 최신성 + 선호 지역으로 계산한다.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from .models import Job

_ASCII = re.compile(r"^[a-z0-9 ]+$")


def _hit(text: str, kw: str) -> bool:
    """ASCII 키워드는 단어 경계로(retail 안의 'ai' 오탐 방지),
    한글 키워드는 교착어 특성상 부분 문자열로 매칭한다."""
    kw = kw.lower()
    if _ASCII.match(kw):
        return re.search(rf"\b{re.escape(kw)}\b", text) is not None
    return kw in text


def _count_hits(text: str, keywords: list[str]) -> list[str]:
    low = (text or "").lower()
    return [kw for kw in keywords if _hit(low, kw)]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            continue
    return None


def _detect_level(title: str, sc: dict) -> str:
    low = title.lower()
    if any(k.lower() in low for k in sc["executive"]["keywords"]):
        return "임원·C레벨"
    if any(k.lower() in low for k in sc["senior"]["keywords"]):
        return "팀장·리드"
    return "실무·기타"


def score_job(job: Job, cfg: dict) -> Job:
    sc = cfg["scoring"]
    title = job.title or ""
    body = f"{job.title} {job.description}"
    tmul = sc.get("title_multiplier", 2.0)

    total = 0.0
    matched: list[str] = []

    for bucket in ("core", "domain", "senior", "executive"):
        spec = sc[bucket]
        w = spec["weight"]
        kws = spec["keywords"]
        # 본문 매칭
        body_hits = _count_hits(body, kws)
        # 제목 매칭(가중)
        title_hits = _count_hits(title, kws)
        total += w * len(set(body_hits))
        total += w * (tmul - 1) * len(set(title_hits))
        matched.extend(body_hits)

    # 선호 지역 가산점
    loc = (job.location or "").lower()
    if any(p.lower() in loc for p in cfg["filters"].get("locations_preferred", [])):
        total += 1.0

    # 최신성 가산점 (최근 3일)
    posted = _parse_date(job.posted)
    if posted and posted >= date.today() - timedelta(days=3):
        total += sc.get("recency_bonus", 1.5)

    job.score = total
    job.matched_keywords = sorted(set(matched))
    job.level = _detect_level(title, sc)
    return job


def passes_filters(job: Job, cfg: dict) -> bool:
    f = cfg["filters"]
    low_title = (job.title or "").lower()
    for ex in f.get("exclude_keywords", []):
        if ex.lower() in low_title:
            return False
    # 핵심 직무 키워드가 제목/본문 어디에도 없으면 무관 공고로 간주
    core_kws = cfg["scoring"]["core"]["keywords"]
    if not _count_hits(f"{job.title} {job.description}", core_kws):
        return False
    return job.score >= f.get("min_score", 0)
