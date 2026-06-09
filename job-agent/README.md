# 맞춤 채용 취합 에이전트 (Job Listing Agent)

안정호(Leo Ahn) 프로필에 맞는 채용 공고를 **매일 자동으로** 취합해
**이메일 + Notion DB**로 보내주는 로컬 에이전트입니다.
**로그인된 크롬 세션(Playwright)**을 그대로 활용해 차단을 우회하고,
리멤버·사람인·링크드인의 *로그인해야 보이는* 맞춤·추천 공고까지 긁습니다.

```
로그인된 크롬 1회 실행 → 5개 사이트 수집 → 중복 제거 → 적합도 채점/필터
→ 신규만 추림 → 이메일·Notion 발송
```

## 동작 방식 (A안: Playwright + 전용 크롬 프로필)

- **전용 자동화 프로필**을 만들고 `--login` 한 번으로 모든 구직 사이트에 로그인 →
  세션이 프로필에 저장되어 매일 헤드리스 실행이 재사용합니다.
  (크롬 기본 프로필을 직접 쓰면 "프로필 잠금" 충돌이 나므로 전용 프로필 권장)
- **소스**: 원티드 · 링크드인 · 사람인 · 잡코리아 · 리멤버
  (한 곳이 막혀도 나머지는 그대로 진행)
- **매칭**: `config.yaml` 키워드 가중치로 *적합도 점수* + 레벨 분류
  (`임원·C레벨` / `팀장·리드` / `실무·기타`)
- **중복 방지**: `data/seen_jobs.json` 기록 → 매일 *신규만* 알림

## 설치 (Windows)

```powershell
cd job-agent
pip install -r requirements.txt
playwright install chromium      # (Chrome 미설치 시에만. 설치돼 있으면 생략 가능)
```
> `config.yaml`의 `browser.channel: chrome`은 **이미 설치된 크롬**을 씁니다.

## 1) 최초 1회 — 사이트 로그인

```powershell
scripts\login.bat          # 또는: python -m jobagent.main --login
```
탭으로 원티드·링크드인·사람인·잡코리아·리멤버가 열립니다. 각각 로그인
(자동 로그인 체크 권장) 후 터미널에 돌아와 **Enter** → 세션 저장 완료.

## 2) 발송 설정 — `.env`

```powershell
copy .env.example .env       # 그리고 값 채우기
```
| 변수 | 설명 |
|---|---|
| `GMAIL_USER` / `GMAIL_APP_PASSWORD` | Gmail 발송. [앱 비밀번호](https://myaccount.google.com/apppasswords) 16자리 |
| `DIGEST_TO` | 수신 주소(미설정 시 `GMAIL_USER`) |
| `NOTION_TOKEN` / `NOTION_DATABASE_ID` | Notion 적재. 아래 `setup_notion.py` 참고 |

이메일만, 또는 Notion만 써도 됩니다(설정 안 한 채널은 자동 skip).

### Notion DB 만들기 (선택)
```powershell
set NOTION_TOKEN=secret_xxx
set NOTION_PARENT_PAGE_ID=xxxxxxxx     # 인티그레이션을 '연결'한 페이지 ID
python setup_notion.py                 # 출력된 DATABASE_ID를 .env에 등록
```
`포지션/회사/적합도/레벨/소스/지역/URL/등록일/키워드/상태` 속성이 생성되어
매일 신규 공고가 카드로 쌓이고 `상태`로 지원 현황을 관리할 수 있습니다.

## 3) 매일 자동 실행 — 작업 스케줄러

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_task.ps1
```
매일 **오전 8시** `JobAgentDaily` 작업이 실행됩니다(시간은 스크립트의 `-At` 수정).
PC가 꺼져 있던 시간은 다음 부팅 후 1회 보충 실행됩니다.

- 즉시 테스트: `Start-ScheduledTask -TaskName JobAgentDaily`
- 로그: `job-agent\data\run.log`
- 해제: `Unregister-ScheduledTask -TaskName JobAgentDaily`

## 수동/디버깅 명령

```powershell
python -m jobagent.main             # 일일 실행(headless, 발송)
python -m jobagent.main --dry-run   # 발송 없이 결과 JSON 출력
python -m jobagent.main --headed    # 창을 보면서 실행(셀렉터 확인용)
python -m jobagent.main --no-dedupe # 신규 필터 끄고 전체 출력
```

## 폴더 구조
```
job-agent/
├─ config.yaml            # 검색어·키워드·가중치·필터·브라우저 설정
├─ .env.example           # 이메일/Notion 시크릿 템플릿
├─ setup_notion.py        # Notion DB 1회 생성
├─ scripts/
│  ├─ login.bat           # 최초 사이트 로그인
│  ├─ run.bat             # 스케줄러가 호출하는 실행 진입점
│  └─ setup_task.ps1      # 작업 스케줄러 등록
└─ jobagent/
   ├─ browser.py          # 로그인된 크롬(Playwright) 래퍼
   ├─ main.py             # 파이프라인 + --login
   ├─ scoring.py          # 적합도 채점
   ├─ dedupe.py           # 신규 공고 판별
   ├─ sources/            # wanted/linkedin/saramin/jobkorea/remember
   └─ notify/             # email_sender / notion_sender
```

## 알아두기 (솔직한 메모)

- **로컬 전용**: 로그인된 크롬은 이 PC에만 있으므로 클라우드(GitHub Actions)로는
  못 돌립니다. PC가 켜져 있을 때 작업 스케줄러가 실행합니다.
- **셀렉터 변동**: 링크드인·사람인·잡코리아·리멤버는 HTML 구조를 자주 바꿉니다.
  각 소스는 여러 셀렉터를 관대하게 시도하고 실패 시 0건으로 빠지지만, 특정
  사이트가 0건이면 `--headed`로 띄워 셀렉터를 점검하세요(소스 파일 상단에 위치 표시).
- **약관**: 링크드인·리멤버는 자동 수집을 약관상 제한합니다. 본인 계정·소량·개인
  용도라는 전제로 사용하세요.
- **커스터마이즈**: `config.yaml`의 `queries`/`scoring`/`filters`만 바꾸면 검색어와
  매칭 기준을 조정할 수 있고, 다른 사람 프로필에도 재사용 가능합니다.
```
