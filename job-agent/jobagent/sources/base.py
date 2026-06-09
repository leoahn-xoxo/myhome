"""소스 공통 유틸."""
from __future__ import annotations

import logging

import requests

log = logging.getLogger("jobagent.sources")

# 대부분의 사이트는 봇 차단이 있어 일반 브라우저 UA를 흉내 낸다.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def get(url: str, *, params=None, headers=None, timeout=15) -> requests.Response:
    h = dict(HEADERS)
    if headers:
        h.update(headers)
    return requests.get(url, params=params, headers=h, timeout=timeout)
