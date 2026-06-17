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

## 1) 사이트 로그인 — 두 가지 방식 중 선택

### 방식 ①: 전용 프로필 + 1회 로그인 (기본, 권장)
```powershell
scripts\login.bat          # 또는: python -m jobagent.main --login
```
탭으로 원티드·링크드인·사람인·잡코리아·리멤버가 열립니다. 각각 로그인
(자동 로그인 체크 권장) 후 터미널에 돌아와 **Enter** → 세션 저장 완료.
충돌이 없어 스케줄 실행에 가장 안정적입니다.

### 방식 ②: 내 크롬 계정(leoflyagain) 그대로 쓰기 — 재로그인 불필요
평소 크롬에서 `leoflyagain@gmail.com`으로 이미 로그인돼 있다면 그 프로필을 직접 가리킬 수 있습니다.

1. 크롬에서 **leoflyagain 계정으로 전환** → 주소창에 `chrome://version` → **"프로필 경로"** 확인
   - 예: `C:\Users\Leo\AppData\Local\Google\Chrome\User Data\Profile 1`
   - 여기서 `User Data` 까지가 **user_data_dir**, 마지막 `Profile 1` 이 **profile_directory**.
2. `config.yaml` 수정:
   ```yaml
   browser:
     user_data_dir: "C:/Users/Leo/AppData/Local/Google/Chrome/User Data"
     profile_directory: "Profile 1"
   ```
3. 끝. `--login` 없이 바로 `python -m jobagent.main --debug` 실행하면 기존 로그인을 그대로 씁니다.

> ⚠️ **방식 ②는 실행 중 크롬을 완전히 종료**해야 합니다(프로필 잠금). 따라서 매일 8시
> 자동 실행 시 그 시각에 크롬이 떠 있으면 충돌할 수 있습니다. 자동화 안정성을 최우선으로
> 한다면 방식 ①(전용 프로필)을 권장합니다. "재로그인이 귀찮다"가 우선이면 방식 ②.

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

### Notion DB (이미 생성됨)
**`🎯 맞춤 채용 공고 트래커`** DB가 이미 만들어져 있습니다 —
ID `5bca349c161f48448db241fe47df6412` (`.env.example`에 기본값으로 들어있음).
연결만 하면 됩니다:
1. https://www.notion.so/my-integrations 에서 **내부 인티그레이션** 생성 → 시크릿 복사 → `.env`의 `NOTION_TOKEN`
2. Notion에서 해당 DB(또는 상위 페이지) 우상단 **⋯ → 연결 추가**로 그 인티그레이션 연결
3. 끝. `NOTION_DATABASE_ID`는 이미 채워져 있습니다.

> 직접 새로 만들고 싶으면 `python setup_notion.py` (NOTION_TOKEN + NOTION_PARENT_PAGE_ID 필요).

DB 속성: `포지션/회사/적합도/레벨/소스/지역/URL/등록일/마감일/연차요구/키워드/플래그/상태`.
매일 신규 공고가 카드로 쌓이고, `상태`로 지원 현황(신규→검토중→지원완료)을 관리합니다.

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
python -m jobagent.main --debug     # 창 표시 + 각 사이트 첫 화면 캡처(발송 안 함)
python -m jobagent.main --no-dedupe # 신규 필터 끄고 전체 출력
```

## 첫 실행 점검 절차 (셀렉터 튜닝)

처음에는 로그인 직후 한 번 진단을 돌려 각 사이트가 실제로 긁히는지 확인하세요.

```powershell
scripts\login.bat                  # ① 5개 사이트 로그인
python -m jobagent.main --debug    # ② 창 뜨고 각 사이트 첫 화면을 캡처
```
- 콘솔 끝에 `소스별 수집: {'wanted': 12, 'saramin': 8, ...}` 형태로 사이트별 건수가 찍힙니다.
- 각 사이트마다 `data/debug/<사이트>.{png, html, outline.txt}` 3종이 저장됩니다.
  - **outline.txt** — 공고 카드 후보 요소의 tag/class/text만 추린 작은 파일. **이걸 공유하면 됨**(붙여넣기 쉬움)
  - png — 로그인 여부·화면 확인용 / html — 전체 마크업(대용량, 보통 불필요)

### 캡처 공유 방법 (둘 중 하나)
```powershell
# (간편) outline.txt 내용을 그대로 복사해 채팅에 붙여넣기
type data\debug\linkedin.outline.txt

# (전체) 디버그 파일을 브랜치에 올려서 직접 보게 하기
git add -f data\debug
git commit -m "debug capture"
git push
```

> 사이트들은 로그인 벽·동적 로딩·A/B 마크업이 있어 첫 1회 튜닝이 거의 필요합니다.
> 평소엔 `data/debug/` 가 git에 올라가지 않습니다(`-f`로 강제 추가).

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

## 적합도 점수는 어떻게 매기나

"나에게 맞는 정도 + 채용 가능성"을 하나의 숫자로 환산합니다(`config.yaml`에서 조정):

- **직무·도메인 매칭**: 마케팅/그로스/퍼포먼스/브랜드/RMN + 이커머스/핀테크/미디어/AI
  (제목 매칭은 가중)
- **경력 연차 적합도** ← *채용 가능성의 핵심*: 공고의 요구 경력을 추출해 안정호님
  경력(17년, sweet spot 8~20년)과 대조
  - sweet spot 안 → **경력적합** 가산 / 주니어 공고 → **과스펙** 감점 / 17년 초과 요구 → 언더스펙 감점
- **회사 규모·유형**: 알려진 대기업(삼성·롯데·쿠팡·네카오·토스…) → **대기업**,
  투자단계·스타트업 신호 → **스타트업** 가산
- **마감 임박**: 마감 3일 이내면 **마감임박** 플래그 + D-day 표시(빨리 움직이라는 신호)
- **최신성·선호지역**: 최근 3일 공고, 서울/원격 가산

플래그(경력적합/과스펙/대기업/스타트업/마감임박)는 이메일 배지와 Notion `플래그`
속성으로 함께 표시됩니다.

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
