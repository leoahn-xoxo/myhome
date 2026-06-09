"""Gmail SMTP로 채용 다이제스트 메일 발송.

필요 환경변수:
  GMAIL_USER            보내는/받는 Gmail 주소
  GMAIL_APP_PASSWORD    Google 앱 비밀번호(2단계 인증 후 발급)
  DIGEST_TO             (선택) 수신 주소. 없으면 GMAIL_USER로 보냄
"""
from __future__ import annotations

import logging
import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from ..models import Job

log = logging.getLogger("jobagent.notify.email")


def _level_color(level: str) -> str:
    return {
        "임원·C레벨": "#C9A84C",
        "팀장·리드": "#4C8FC9",
        "실무·기타": "#888880",
    }.get(level, "#888880")


def render_html(jobs: list[Job]) -> str:
    today = date.today().isoformat()
    rows = []
    for i, j in enumerate(jobs, 1):
        kw = ", ".join(j.matched_keywords[:6])
        rows.append(
            f"""
            <tr style="border-bottom:1px solid #eee;">
              <td style="padding:10px 8px;color:#aaa;">{i}</td>
              <td style="padding:10px 8px;">
                <a href="{escape(j.url)}" style="color:#111;text-decoration:none;font-weight:600;">
                  {escape(j.title)}</a><br>
                <span style="color:#666;font-size:13px;">{escape(j.company or '—')}
                  · {escape(j.location or '위치 미상')}</span><br>
                <span style="color:#999;font-size:12px;">키워드: {escape(kw)}</span>
              </td>
              <td style="padding:10px 8px;text-align:center;">
                <span style="background:{_level_color(j.level)};color:#fff;padding:3px 8px;
                  border-radius:10px;font-size:12px;white-space:nowrap;">{escape(j.level)}</span>
              </td>
              <td style="padding:10px 8px;text-align:center;font-weight:700;color:#C9A84C;">
                {j.score:.0f}</td>
              <td style="padding:10px 8px;text-align:center;color:#888;font-size:12px;">
                {escape(j.source)}</td>
            </tr>"""
        )
    return f"""
    <div style="font-family:'Apple SD Gothic Neo',sans-serif;max-width:760px;margin:0 auto;
      background:#fafafa;padding:24px;">
      <h1 style="font-size:22px;color:#111;margin:0 0 4px;">오늘의 맞춤 채용 공고</h1>
      <p style="color:#888;margin:0 0 18px;">{today} · 적합도 상위 {len(jobs)}건 · Leo Ahn 프로필 기준</p>
      <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:8px;
        overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
        <thead>
          <tr style="background:#111;color:#fff;text-align:left;font-size:13px;">
            <th style="padding:10px 8px;">#</th>
            <th style="padding:10px 8px;">포지션</th>
            <th style="padding:10px 8px;text-align:center;">레벨</th>
            <th style="padding:10px 8px;text-align:center;">적합도</th>
            <th style="padding:10px 8px;text-align:center;">소스</th>
          </tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
      <p style="color:#aaa;font-size:12px;margin-top:18px;">
        ※ 적합도 = 직무·도메인·리드 키워드 매칭 + 최신성 + 선호지역 가산점.
        이 메일은 GitHub Actions가 매일 자동 발송합니다.</p>
    </div>"""


def send(jobs: list[Job]) -> bool:
    user = os.environ.get("GMAIL_USER")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    to = os.environ.get("DIGEST_TO", user)
    if not (user and pw):
        log.info("email: GMAIL_USER/GMAIL_APP_PASSWORD 미설정 → 메일 건너뜀")
        return False
    if not jobs:
        log.info("email: 보낼 공고 없음 → 건너뜀")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[채용 다이제스트] {date.today().isoformat()} · {len(jobs)}건"
    msg["From"] = user
    msg["To"] = to
    msg.attach(MIMEText(render_html(jobs), "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(user, pw)
            s.sendmail(user, [to], msg.as_string())
        log.info("email: %s 로 %d건 발송 완료", to, len(jobs))
        return True
    except Exception as e:  # noqa: BLE001
        log.error("email 발송 실패: %s", e)
        return False
