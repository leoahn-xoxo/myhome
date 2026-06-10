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


_YEARS_PATTERNS = [
    re.compile(r"경력\s*(\d{1,2})\s*년\s*(?:이상|~|-|부터)?"),
    re.compile(r"(\d{1,2})\s*년\s*이상"),
    re.compile(r"(\d{1,2})\s*\+\s*years"),
    re.compile(r"(\d{1,2})\s*years?"),
    re.compile(r"min(?:imum)?\.?\s*(\d{1,2})\s*years?"),
]


def _extract_years(text: str) -> int | None:
    """공고 텍스트에서 요구 최소 경력(년)을 추출. 신입/무관이면 0/None."""
    low = (text or "").lower()
    if any(w in low for w in ("신입", "경력무관", "무관", "entry level")):
        return 0
    candidates: list[int] = []
    for pat in _YEARS_PATTERNS:
        for m in pat.findall(low):
            try:
                candidates.append(int(m))
            except (TypeError, ValueError):
                continue
    # 보통 "최소 N년"을 보므로 가장 작은 합리값을 채택
    valid = [c for c in candidates if 0 < c <= 30]
    return min(valid) if valid else None


def _score_years(job: Job, cfg: dict) -> tuple[float, list[str]]:
    """요구 연차 ↔ 내 경력 적합도. (점수, 플래그) 반환."""
    p = cfg["profile"]
    y = cfg["scoring"]["years"]
    lo, hi, mine = p["sweet_spot_min"], p["sweet_spot_max"], p["years_experience"]
    req = job.years_required
    if req is None:
        return 0.0, []
    if lo <= req <= hi:
        return y["fit_bonus"], ["경력적합"]
    if lo - 3 <= req <= hi + 3:
        return y["near_bonus"], ["경력적합"]
    if req < lo - 3:
        # 주니어 공고 → 과스펙(채용 가능성 낮음)
        return -y["overqualified_penalty"], ["과스펙"]
    if req > mine:
        # 내 경력보다 더 요구 → 언더스펙
        return -y["underqualified_penalty"], []
    return 0.0, []


def _score_company(job: Job, cfg: dict) -> tuple[float, list[str]]:
    c = cfg["scoring"]["company"]
    text = f"{job.company} {job.description}".lower()
    score, flags = 0.0, []
    if any(k.lower() in text for k in c["known_enterprises"]):
        score += c["enterprise_bonus"]
        flags.append("대기업")
    if any(k.lower() in text for k in c["startup_signals"]):
        score += c["startup_bonus"]
        flags.append("스타트업")
    return score, flags


def _score_deadline(job: Job, cfg: dict) -> tuple[float, list[str]]:
    d = cfg["scoring"]["deadline"]
    dl = _parse_date(job.deadline)
    if not dl:
        return 0.0, []
    job.days_left = (dl - date.today()).days
    if 0 <= job.days_left <= d["imminent_days"]:
        return d["imminent_bonus"], ["마감임박"]
    return 0.0, []


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

    flags: list[str] = []

    # 경력 연차 적합도 (채용 가능성의 핵심)
    job.years_required = _extract_years(body)
    ys, yf = _score_years(job, cfg)
    total += ys
    flags += yf

    # 회사 규모/유형
    cs, cf = _score_company(job, cfg)
    total += cs
    flags += cf

    # 마감 임박
    ds, df = _score_deadline(job, cfg)
    total += ds
    flags += df

    job.score = total
    job.matched_keywords = sorted(set(matched))
    job.level = _detect_level(title, sc)
    job.flags = sorted(set(flags))
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
