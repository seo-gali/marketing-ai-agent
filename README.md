# Marketing AI Agent

YouTube 영상 조회·Ollama 분석·광고 댓글 검토·Chrome 게시용 Windows 11 로컬 대시보드

- 검증 완료: 실제 API 조회·Ollama 추론·초안 저장·게시 규칙·실제 YouTube 입력·게시·댓글 확인
- 영상 근거: 공개 자막 우선 · 조회 실패 시 초반 네 구간의 화면 자막·시각·캡처 수집 · 연애 영상 2건 검증
- 미완료: 2~3분 실게시 시연 영상·스크린리더 실기기 검수
- 운영 방식: 광고 표시·본문 승인 후 게시

## 기술 구성

| 구분 | 구성 |
|---|---|
| 프런트엔드 | React 19 · TypeScript · Vite 8 |
| 백엔드 | FastAPI · Python 3.13 |
| 저장소 | SQLite · WAL |
| 모델 | Ollama · qwen2.5-coder:7b |
| 영상 정보 | YouTube Data API v3 |
| 브라우저 | Playwright Python · 지정 Chrome 프로필 |

## 준비 환경

- Windows 11 · Node 24 · Python 3.13 · Google Chrome
- Windows 한국어 OCR 언어 · 영상 화면 문구 수집용
- Ollama 실행 및 `qwen2.5-coder:7b` 설치
- YouTube Data API v3 활성화 및 API 키
- 본인 소유 테스트 영상 ID

## 설치·설정

프로젝트 루트 PowerShell 기준

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
npm.cmd ci
if (!(Test-Path .env)) { Copy-Item .env.example .env }
ollama list
```

`.env` 직접 입력 항목

| 변수 | 용도·기본값 |
|---|---|
| `YOUTUBE_API_KEY` | 영상·댓글 조회용 API 키 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` |
| `DATABASE_URL` | `sqlite:///./data/marketing-agent.db` |
| `CHROME_USER_DATA_DIR` | `./local/chrome-profiles/youtube1` |
| `DAILY_MAX_COMMENTS` | 일일 상한 10건, 최대 10건 |
| `COMMENT_MIN_CHARS` / `COMMENT_MAX_CHARS` | 40 / 120 |
| `TEST_VIDEO_IDS` | 본인 소유 영상 ID, 쉼표 구분 |

예시 테스트 영상: `DPFhGxGM8qQ` · Google OAuth 클라이언트 ID/Secret 불필요

## 실행

```powershell
npm.cmd run build
./.venv/Scripts/python.exe scripts/serve.py
```

- 대시보드: http://127.0.0.1:8000
- 상태: http://127.0.0.1:8000/api/health
- API 문서: http://127.0.0.1:8000/docs
- 개발 화면: 별도 터미널의 `npm.cmd run dev` · http://127.0.0.1:5173
- Windows 파일 잠금 예방: `npm ci` 실행 전 Vite 종료
- 실행 조건: 서버 1프로세스 · loopback 전용 · 외부 프록시 공개 제외

## 최초 로그인

환경 설정 → Chrome 프로필 → 로그인·계정 관리 → YouTube 직접 로그인 → 해당 Chrome 창 종료

- 유튜브2·3: 추가 버튼으로 등록 · 계정별 독립 폴더 · 게시 프로필 선택
- 유튜브1: 기존 지정 폴더 유지
- 로그인 창: 자동 제어 옵션 없는 일반 Chrome · 기본 Chrome 프로필과 분리
- 유튜브2·3의 실제 Google 계정 로그인·게시: 사용자 계정 미등록으로 미검증

유튜브1 최초 로그인의 터미널 실행 방법

```powershell
$loginProfilePath=(./.venv/Scripts/python.exe -c "from backend.config import PROFILE_PATH; print(PROFILE_PATH)").Trim()
& "$env:ProgramFiles/Google/Chrome/Application/chrome.exe" "--user-data-dir=$loginProfilePath" "--profile-directory=Default" "https://www.youtube.com/?hl=ko"
```

1. 앱의 전용 Chrome 종료
2. 위 명령의 지정 프로필에서 YouTube 직접 로그인
3. 해당 프로필의 Chrome 창 전체 종료
4. 앱의 전용 Chrome 열기·게시 진행

인증 처리: 사용자 직접 입력 · 동일 지정 프로필 · 기본 프로필 변경·쿠키 복사·보안 우회 옵션 없음

## 사용 순서

1. 영상 불러오기: 지정 5채널 최신 영상 · 채널 필터 · 제목 검색 · URL 입력
2. 영상 선택: 자막·화면 근거 수집 · 고민/초안 생성 · 시각/캡처 확인 · 초안 편집
3. 댓글 달기: 지정 Chrome 로그인 · 광고 본문 승인 · 글자별 입력 · 게시 · 결과 확인

추가 동작

- 빈 검색어: 목록 0건·입력 안내, API 422 · 전체 목록 버튼 별도
- 댓글 오류: blur·저장 시 검증 · 오류 필드 포커스
- 임시 저장: 영상별 localStorage · 7일 만료 · 앱 시작/영상 선택 시 만료본 삭제
- 환경 설정: 라이트·다크 테마 · 브라우저별 테마·게시 프로필 선택 유지
- 연결 상태: 사이드바의 Ollama·YouTube·API 상태등 · 확인 버튼의 HTTP 200 응답 확인 · 실패 시 빨간불·재확인
- 채널 추가 탭: YouTube 영상 링크 입력·조회 결과 별도 표시 · 지정 채널 목록·검색 상태 유지
- 검색·필터: 브라우저 저장 · 초기화·실행 취소
- 모바일: 메뉴 열기/닫기 · 단일 열 · 키보드 포커스
- 이력: 게시 작업·활동 기록별 독립 페이지 · 개별/전체 삭제 · 실행 취소 · 연결 오류 재조회
- 이력 삭제: 표시 이력 제거 · 게시 댓글·중복 방지·일일 상한 유지
- 임시 초안 삭제: 이 브라우저의 작성 중 댓글만 삭제 · 서버 저장 초안·테마·검색 상태 유지
- 사용자용 404 · 클릭 가능한 로고 · 파비콘·메타 설명

## 게시 규칙

- 지정 5채널 및 등록 테스트 영상만 허용
- API 조회 기반 실제 채널 ID 재확인
- 40~120자 · `[광고]`·`운명원` 필수
- 링크·해시태그·허위 이용/시청 경험 표현 차단
- 영상당 1건 · 동일 댓글 중복 차단 · 일일 최대 10건
- 진행·확인 불가 작업 포함 상한 계산
- 게시 클릭 전 제출 시도 저장 · 계정/본문/댓글 링크 대조
- 확인 불가 상태의 성공 처리·자동 재게시 금지
- CAPTCHA·인증·플랫폼 제한 우회 금지
- 기본 Chrome 프로필 수정·쿠키 복사 제외

## 보안·검증

```powershell
./.venv/Scripts/python.exe -m unittest discover -s tests -v
./.venv/Scripts/python.exe scripts/verify_e2e.py
./.venv/Scripts/python.exe scripts/verify_accessibility.py
./.venv/Scripts/python.exe scripts/verify_analysis_e2e.py
./.venv/Scripts/python.exe scripts/verify_settings_e2e.py
./.venv/Scripts/python.exe scripts/verify_docs.py
npm.cmd run build
npm.cmd audit
./.venv/Scripts/python.exe -m pip check
```

- Python 검사: 24건 통과 · 게시 규칙·동시성·인용 위조 차단·보안 경계·프로필 분리·삭제 후 게시 제한
- 화면 E2E: 실제 5채널 40영상 · 편집/임시 저장 · 빈 검색어 · 승인 초기화 · 차단 응답 · 반응형
- 접근성: 키보드 메뉴·본문 이동·포커스·접근성 트리·레이블·주요 텍스트 대비
- 소개 페이지: 탭·실제 Markdown 문서 4개·팝업 포커스·모바일·오류 복구·HTML 실행 차단
- 방어: 경로별 요청 제한·16KB 본문 상한·Host/Origin/접속 주소 검사·CSP·프레임 차단
- 의존성 검사: 알려진 취약점 0건 · 별도 개발 도구 `pip-audit` 검사 포함
- 검사 한계: NVDA/JAWS 실기기·공개 배포 침투·대규모 부하 미검증
- 자동 검증의 외부 댓글 게시: 미실행
- 설정·이력 E2E: 격리된 SQLite·검증용 5173 포트의 실제 FastAPI · 실제 계정/게시 기록 변경 없음
- 실계정 별도 검증: 승인 본문 1회 게시·새로고침 확인·사용자의 다른 계정 공개 확인

## 로컬 데이터·백업

| 경로 | 내용 |
|---|---|
| `data/marketing-agent.db` | 영상·분석·초안·작업·단계별 이력 |
| `local/chrome-profiles/` | 지정 프로필의 인증 상태 |
| `local/screenshots/` | 오류·입력·확인 캡처 |
| `local/backups/` | SQLite 일관 백업 |
| `artifacts/` | E2E·접근성 결과 및 화면 |

```powershell
./.venv/Scripts/python.exe scripts/backup_db.py
```

백업 검사: SQLite Backup API · 무결성 확인 · 원본 DB 변경 없음

Git 제외: `.env`·API 키·Chrome 인증정보·DB·캡처·로컬 백업·과제 PDF

## 결과 문서

- [프로젝트 소개 · GitHub Pages](https://seo-gali.github.io/marketing-ai-agent/)
- [구현·실행 결과 및 제작 의도](docs/results/verification.md)
- [보안 감사](docs/results/security-audit.md)
- [접근성·사용성 검수](docs/results/accessibility.md)

공개 안내: 프로젝트 소개·앱 점검 현황 탭 · Markdown 문서 팝업 · 앱의 로컬 실행 절차

## 남은 항목

- 2~3분 실제 게시 시연 영상
- 자막·OCR 인용과 실제 화면의 사용자 대조 · 전체 영상 장면 분석 제외
- 프로필 2·3의 실계정 로그인·실게시 검증
- 가점: 뜨기 직전 영상 탐색
- 모델의 의미적 사실성에 대한 사용자 검토
- 인터넷 공개 전 별도 인증·권한 설계

기준: 과제 PDF · `.project/plan.md` · `DESIGN.md` · `AGENTS.md`
화면 참조: 사용자 제공 `marketing-ai-agent-implemented`의 프런트엔드
