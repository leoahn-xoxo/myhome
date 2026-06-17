"""Notion 데이터베이스 1회 생성 스크립트.

채용 공고 적재용 DB를 올바른 속성 스키마로 만든다. 부모 페이지 ID와
인티그레이션 토큰이 필요하다.

사용:
  export NOTION_TOKEN=secret_xxx
  export NOTION_PARENT_PAGE_ID=xxxxxxxx   # 인티그레이션을 공유한 페이지
  python setup_notion.py

출력된 DATABASE_ID를 GitHub Secret(NOTION_DATABASE_ID)에 등록하세요.
"""
from __future__ import annotations

import os
import sys

import requests

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"

SCHEMA = {
    "포지션": {"title": {}},
    "회사": {"rich_text": {}},
    "적합도": {"number": {"format": "number"}},
    "레벨": {
        "select": {
            "options": [
                {"name": "임원·C레벨", "color": "yellow"},
                {"name": "팀장·리드", "color": "blue"},
                {"name": "실무·기타", "color": "gray"},
            ]
        }
    },
    "소스": {
        "select": {
            "options": [
                {"name": "wanted", "color": "green"},
                {"name": "linkedin", "color": "blue"},
                {"name": "saramin", "color": "orange"},
                {"name": "jobkorea", "color": "pink"},
                {"name": "remember", "color": "purple"},
            ]
        }
    },
    "지역": {"rich_text": {}},
    "URL": {"url": {}},
    "등록일": {"date": {}},
    "마감일": {"date": {}},
    "연차요구": {"number": {"format": "number"}},
    "키워드": {"multi_select": {}},
    "플래그": {
        "multi_select": {
            "options": [
                {"name": "마감임박", "color": "red"},
                {"name": "경력적합", "color": "green"},
                {"name": "스타트업", "color": "blue"},
                {"name": "대기업", "color": "purple"},
                {"name": "과스펙", "color": "gray"},
            ]
        }
    },
    "상태": {
        "select": {
            "options": [
                {"name": "신규", "color": "red"},
                {"name": "검토중", "color": "yellow"},
                {"name": "지원완료", "color": "green"},
                {"name": "보류", "color": "gray"},
            ]
        }
    },
    "지원여부": {
        "select": {
            "options": [
                {"name": "미지원", "color": "gray"},
                {"name": "지원예정", "color": "yellow"},
                {"name": "지원완료", "color": "green"},
                {"name": "관심없음", "color": "default"},
            ]
        }
    },
    "결과": {
        "select": {
            "options": [
                {"name": "미정", "color": "gray"},
                {"name": "서류접수", "color": "blue"},
                {"name": "서류합격", "color": "green"},
                {"name": "면접중", "color": "yellow"},
                {"name": "최종합격", "color": "purple"},
                {"name": "불합격", "color": "red"},
                {"name": "포기", "color": "default"},
            ]
        }
    },
}


def main() -> int:
    token = os.environ.get("NOTION_TOKEN")
    parent = os.environ.get("NOTION_PARENT_PAGE_ID")
    if not (token and parent):
        print("NOTION_TOKEN, NOTION_PARENT_PAGE_ID 환경변수가 필요합니다.")
        return 1

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": VERSION,
        "Content-Type": "application/json",
    }
    payload = {
        "parent": {"type": "page_id", "page_id": parent},
        "title": [{"type": "text", "text": {"content": "맞춤 채용 공고 트래커"}}],
        "properties": SCHEMA,
    }
    r = requests.post(f"{API}/databases", headers=headers, json=payload, timeout=20)
    if r.status_code >= 300:
        print("생성 실패:", r.status_code, r.text)
        return 1
    db_id = r.json()["id"]
    print("✅ 데이터베이스 생성 완료")
    print("DATABASE_ID =", db_id)
    print("→ 이 값을 GitHub Secret 'NOTION_DATABASE_ID' 에 등록하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
