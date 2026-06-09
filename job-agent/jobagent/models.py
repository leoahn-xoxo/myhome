"""채용 공고 데이터 모델."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


def _norm(text: str) -> str:
    """비교용 정규화: 공백/특수문자 제거 + 소문자."""
    return re.sub(r"[\s\W_]+", "", (text or "").lower())


@dataclass
class Job:
    """하나의 채용 공고. 모든 소스는 이 형태로 정규화해서 반환한다."""

    source: str                      # wanted / linkedin / saramin / jobkorea / remember
    title: str
    company: str
    url: str
    location: str = ""
    posted: Optional[str] = None     # ISO 날짜 문자열(YYYY-MM-DD) 가능하면
    description: str = ""
    external_id: str = ""

    # 채점 결과(파이프라인이 채움)
    score: float = 0.0
    level: str = ""                  # 신규/주니어, 팀장·리드, 임원·C레벨
    matched_keywords: list = field(default_factory=list)

    @property
    def key(self) -> str:
        """중복 제거용 안정 키. external_id가 없으면 회사+직무 해시."""
        if self.external_id:
            base = f"{self.source}:{self.external_id}"
        else:
            base = f"{_norm(self.company)}:{_norm(self.title)}"
        return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "location": self.location,
            "posted": self.posted,
            "score": round(self.score, 1),
            "level": self.level,
            "matched_keywords": self.matched_keywords,
            "key": self.key,
        }
