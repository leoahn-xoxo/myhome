"""로그인된 크롬 세션을 쓰기 위한 Playwright 브라우저 래퍼.

Windows에서 크롬 기본 프로필(Default)을 직접 열면 잠금 충돌이 나므로,
기본값은 '전용 자동화 프로필'을 쓴다. 최초 1회 `--login`으로 각 구직
사이트에 로그인해두면 세션이 이 프로필에 저장되어 매일 재사용된다.

config.yaml 의 browser 섹션:
  user_data_dir: auto        # auto = 전용 프로필. 또는 실제 경로 직접 지정
  channel: chrome            # 설치된 Chrome 사용(별도 다운로드 불필요)
  headless: true             # 일일 실행은 headless, --login/--headed 시 창 표시
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

log = logging.getLogger("jobagent.browser")


def _default_profile_dir() -> Path:
    """전용 자동화 프로필 경로 (OS별)."""
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":  # macOS
        base = Path.home() / "Library/Application Support"
    else:
        base = Path.home() / ".config"
    return base / "job-agent" / "chrome-profile"


class Browser:
    """persistent context 컨텍스트 매니저. context/page/request 노출."""

    def __init__(self, cfg: dict, headless: bool | None = None):
        b = cfg.get("browser", {})
        udd = b.get("user_data_dir", "auto")
        self.user_data_dir = _default_profile_dir() if udd in (None, "auto") else Path(udd)
        self.profile_directory = b.get("profile_directory") or None  # 예: "Profile 1"
        self.channel = b.get("channel", "chrome")
        self.headless = b.get("headless", True) if headless is None else headless
        self._pw = None
        self.context = None

    def __enter__(self) -> "Browser":
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self._pw = sync_playwright().start()
        log.info("크롬 실행: dir=%s profile=%s headless=%s",
                 self.user_data_dir, self.profile_directory or "(persistent)", self.headless)
        args = ["--disable-blink-features=AutomationControlled"]
        if self.profile_directory:
            # 실제 크롬의 특정 계정 프로필(예: leoflyagain = "Profile 1")을 그대로 사용
            args.append(f"--profile-directory={self.profile_directory}")
        opts = dict(
            user_data_dir=str(self.user_data_dir),
            headless=self.headless,
            viewport={"width": 1366, "height": 900},
            locale="ko-KR",
            args=args,
        )
        try:
            self.context = self._pw.chromium.launch_persistent_context(channel=self.channel, **opts)
        except Exception as e:  # noqa: BLE001
            # 설치된 Chrome이 없으면 Playwright 번들 chromium으로 폴백
            log.warning("channel=%s 실행 실패(%s) → 번들 chromium으로 폴백 "
                        "(로그인 세션은 유지됨). `playwright install chromium` 권장", self.channel, e)
            self.context = self._pw.chromium.launch_persistent_context(**opts)
        return self

    def __exit__(self, *exc):
        try:
            if self.context:
                self.context.close()
        finally:
            if self._pw:
                self._pw.stop()

    def new_page(self):
        return self.context.new_page()

    @property
    def request(self):
        """컨텍스트 쿠키를 공유하는 APIRequestContext (인증된 JSON 호출용)."""
        return self.context.request
