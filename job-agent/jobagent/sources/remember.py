"""리멤버 커리어(Remember) 소스 — 안내용 스텁.

리멤버 커리어는 공개/게스트 API가 없고 앱 로그인 토큰이 있어야 채용 데이터에
접근할 수 있다. 자동 수집을 켜려면 인증 토큰이 필요하므로, 기본은 0건을 반환하고
README에 수동 연동 방법을 안내한다.

REMEMBER_AUTH_TOKEN 환경변수가 주어지면 향후 여기에 호출 로직을 추가할 수 있다.
"""
from __future__ import annotations

import logging
import os

from ..models import Job

log = logging.getLogger("jobagent.sources.remember")


def fetch(queries: list[str], **_) -> list[Job]:
    token = os.environ.get("REMEMBER_AUTH_TOKEN")
    if not token:
        log.info(
            "remember: 공개 API 없음 → 건너뜀. "
            "리멤버 앱은 인증 토큰이 필요합니다(README 참고)."
        )
        return []
    # 토큰 기반 연동은 사용자의 계정/약관 확인 후 추가 예정.
    log.info("remember: 토큰 감지됨이나 연동 미구현 → 0건")
    return []
