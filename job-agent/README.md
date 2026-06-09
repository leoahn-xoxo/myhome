# 맞춤 채용 취합 에이전트 (Job Listing Agent)

안정호(Leo Ahn) 프로필에 맞는 채용 공고를 **매일 자동으로** 취합해
**이메일 + Notion DB**로 보내주는 에이전트입니다. GitHub Actions가 매일
아침 8시(KST)에 알아서 실행합니다.

```
소스 수집 → 중복 제거 → 적합도 채점/필터 → 신규만 추림 → 이메일·Notion 발송
```

## 무엇을 하나요

- **소스**: 원티드 · 링크드인 · 사람인 · 잡코리아 · 리멤버
  (사이트별 모듈. 한 곳이 막혀도 나머지는 그대로 진행)
- **매칭**: `config.yaml`의 키워드 가중치로 *적합도 점수* 계산
  - 직무(마케팅/그로스/퍼포먼스/브랜드/CRM/RMN) · 도메인(이커머스/핀테크/미디어/AI)
    · 리드/시니어 신호 · 최신성 · 선호 지역
- **레벨 분류**: `임원·C레벨` / `팀장·리드` / `실무·기타`
- **중복 방지**: `data/seen_jobs.json`에 이미 본 공고를 기록 → 매일 *신규만* 알림

## 폴더 구조

```
job-agent/
├─ config.yaml              # 검색어·키워드·가중치·필터 (여기만 고치면 커스터마이즈)
├─ requirements.txt
├─ setup_notion.py          # Notion DB 1회 생성
└─ jobagent/
   ├─ main.py               # 파이프라인 엔트리포인트
   ├─ scoring.py            # 적합도 채점
   ├─ dedupe.py             # 신규 공고 판별(seen store)
   ├─ sources/              # wanted/linkedin/saramin/jobkorea/remember
   └─ notify/               # email_sender / notion_sender
.github/workflows/job-agent.yml   # 매일 08:00 KST cron
```

## 빠른 시작 (로컬 테스트)

```bash
cd job-agent
pip install -r requirements.txt

# 발송 없이 수집·채점 결과만 콘솔로 확인
python -m jobagent.main --dry-run --no-dedupe
```

## 매일 자동화 (GitHub Actions)

`.github/workflows/job-agent.yml`이 매일 23:00 UTC(=08:00 KST)에 실행됩니다.
GitHub 저장소 **Settings → Secrets and variables → Actions**에 아래를 등록하세요.

| Secret | 필수 | 설명 |
|---|---|---|
| `GMAIL_USER` | 이메일용 | 보내는 Gmail 주소 (예: leoflyagain@gmail.com) |
| `GMAIL_APP_PASSWORD` | 이메일용 | Google [앱 비밀번호](https://myaccount.google.com/apppasswords) (2단계 인증 후 발급, 16자리) |
| `DIGEST_TO` | 선택 | 수신 주소(미설정 시 `GMAIL_USER`로 발송) |
| `NOTION_TOKEN` | Notion용 | Notion [인티그레이션](https://www.notion.so/my-integrations) 시크릿 |
| `NOTION_DATABASE_ID` | Notion용 | 공고 적재 DB ID (`setup_notion.py` 출력값) |
| `SARAMIN_API_KEY` | 선택 | 사람인 [오픈 API](https://oapi.saramin.co.kr/guide) 키(무료) |

설정 후 **Actions 탭 → 워크플로우 → Run workflow**로 즉시 테스트할 수 있습니다.

### Notion DB 만들기

```bash
export NOTION_TOKEN=secret_xxx
export NOTION_PARENT_PAGE_ID=xxxxxxxx   # 인티그레이션을 '연결'한 페이지 ID
python setup_notion.py                  # 출력된 DATABASE_ID를 Secret에 등록
```
DB에는 `포지션/회사/적합도/레벨/소스/지역/URL/등록일/키워드/상태` 속성이
생성되며, 매일 신규 공고가 카드로 쌓이고 `상태`로 지원 현황을 관리할 수 있습니다.

## 소스별 안정성 메모 (중요)

채용 사이트들은 데이터센터 IP를 자주 차단합니다. 실측 기준:

| 소스 | 방식 | 안정성 |
|---|---|---|
| **사람인** | 공식 오픈 API(키 필요) | ⭐⭐⭐ 가장 안정적 — **키 발급 강력 권장** |
| 원티드 | 공개 JSON API | ⭐⭐ 간헐적 403 가능 |
| 링크드인 | 게스트 검색 | ⭐⭐ 레이트리밋/지역 차단 가능 |
| 잡코리아 | HTML 스크래핑 | ⭐ 마크업 변경/차단 시 자동 skip |
| 리멤버 | 공개 API 없음 | ✖ 토큰 필요 — 기본 비활성 안내 |

> 한 소스가 막혀도 파이프라인은 멈추지 않고 나머지로 다이제스트를 만듭니다.
> **안정적인 일일 수집을 원하면 `SARAMIN_API_KEY`를 백본으로 두는 것을 추천**합니다.

## 커스터마이즈

`config.yaml`에서 바로 조정:
- `queries`: 검색어 추가/변경
- `scoring.*.keywords` / `weight`: 매칭 키워드와 가중치
- `filters.min_score` / `max_results`: 컷오프와 다이제스트 크기
- `filters.exclude_keywords`: 제외할 직무
- `sources.*`: 켜고 끌 소스

다른 사람이 쓰려면 `config.yaml`의 키워드만 그 사람 커리어에 맞게 바꾸면 됩니다.
```

CLI 옵션:
```bash
python -m jobagent.main              # 전체 실행(발송 + 신규기록)
python -m jobagent.main --dry-run    # 발송 없이 결과만 출력
python -m jobagent.main --no-dedupe  # 신규 필터 끄고 전체 출력
```
