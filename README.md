# Marketing AI Agent

Windows 11 로컬 React · FastAPI · SQLite · Ollama · Chrome 대시보드입니다. 광고 관계가 명시된 댓글만 검토·승인 후 게시합니다.

## 실행

PowerShell, 저장소 루트에서 실행합니다. Node 24, Python 3.13, Chrome, Ollama가 필요합니다.

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
npm.cmd ci
# .env가 없다면 .env.example을 .env로 복사하고 YOUTUBE_API_KEY 설정
ollama list
./.venv/Scripts/python.exe scripts/serve.py
```

다른 터미널에서 `npm.cmd run dev`, http://127.0.0.1:5173 을 엽니다.
`npm.cmd run build`로 프로덕션 번들을 생성합니다.

## 검증 현황

- 2026-10-20: Windows에서 Vite·FastAPI·SQLite 기동, Playwright MCP로 대시보드/health 확인.
- Ollama `qwen2.5-coder:7b` 설치·연결 확인. YouTube는 키 설정 여부만 확인, 실제 API 호출은 다음 단계에서 검증합니다.
- `npm.cmd run build`, `npm.cmd audit`, 가상환경 `python -m pip_audit` 통과. 개발 도구 pip 취약점은 26.2.1로 갱신 후 재검사했습니다.
- 캡처·API 키·DB·브라우저 프로필은 Git 제외. 증거 파일은 `artifacts/`와 `local/`에 보관합니다.

## 기준

과제 PDF(로컬 전용), `.project/plan.md`, `DESIGN.md`, `dashboard-preview.html`을 따릅니다. 현재 사용자 요청에 따라 광고 표시와 게시 승인을 적용합니다.

### 영상 조회 검증
- 실제 YouTube Data API로 지정 채널 5개 × 8개 = 40개 조회 성공.
- Playwright MCP: 채널 필터 8개, 검색 빈 결과, 테스트 URL 상세 선택, 잘못된 호스트 URL 422 확인.
- `npm.cmd run build` 통과. `artifacts/02-discovery.png` 저장.

### AI 분석 검증
- 실제 Ollama 추론: 테스트 음악 영상은 연애 고민 확인 불가, 71자 광고 기능 테스트 초안 생성.
- 실제 연애 영상 `akn-AvCeHBI`는 남자의 마음 변화 고민과 별도 광고 초안 생성, 공개 인기 댓글 수집 확인.
- 근거 인용은 모델이 재작성하지 않고 선택한 출처의 실제 원문을 서버에서 발췌합니다.
- 자막 미확보/장면·발언 미검증을 화면에 명시합니다. F3의 실제 장면 확인은 아직 미충족입니다.
- Playwright MCP에서 초안 표시·수정 저장 확인. `python -m unittest discover -s tests -v` 2개, 빌드 통과.

### 게시 규칙·이력 검증
- SQLite 즉시 트랜잭션과 고유 인덱스로 동시 중복 요청 차단, 일일 상한 10건(진행·불확실 포함), 승인·프로필·채널 허용 검증.
- 제출 클릭 전에 시도를 영속 기록합니다. 재시작 시 제출 이후 중단 작업은 확인 불가로 고정하고 재게시를 차단합니다.
- 별도 임시 SQLite DB에서 동시 요청·허용 목록·상한·날짜 변경·중단 복구를 포함한 6개 검사 통과. 실제 게시 성공을 대신하는 검증은 아닙니다.
- 실제 서버 재시작 후 API/MCP로 기존 71자 초안 유지와 이력 API·화면을 확인했습니다. 빌드 통과.

### Chrome 게시 흐름
- FastAPI + Playwright Python의 지정 경로 `local/chrome-profiles/youtube1` / `launch_persistent_context` 사용. 기본 Chrome·MCP 프로필로 전환하거나 인증정보를 복사하지 않습니다.
- 전용 Chrome 실제 실행 및 한국어 YouTube 접근 확인. 수동 로그인은 사용자가 수행합니다.
- 서버 승인 검증 → 글자별 입력 → 입력 본문 대조 → 게시 시도 영속 기록 → 계정 핸들·본문·댓글 링크 확인 → 페이지 새로고침 후 재확인 흐름 구현.
- 타임아웃·CAPTCHA·미로그인·기존 본문·불확실 게시에서 중단하고 캡처/이력 기록. 불확실 상태 자동 재게시는 없습니다.
- 9개 검사 통과: 임시 DB 규칙 6개 + 로컬 HTML 브라우저 픽스처 3개(입력·검증·불확실·미로그인). 픽스처 결과는 실제 YouTube 게시 성공을 뜻하지 않습니다.
- 실제 게시: 본문 승인 완료, 앱 지정 프로필에서 로그인된 상태의 게시 검증은 미실시. 로그인된 MCP 프로필을 앱으로 이관하지 않습니다.
- 최신 범위: MCP/앱 프로필 비교, 인증 유지의 독립 검증, 프로필 재사용 구조 변경은 제외합니다.
