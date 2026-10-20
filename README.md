# Marketing AI Agent

YouTube 지정 채널의 영상을 조회하고, Ollama로 영상 고민과 댓글을 생성한 뒤, **Chrome 프로필을 열어 한 글자씩 입력·게시·실제 확인**하는 Windows 로컬 대시보드 개발 프로젝트입니다.

> **현재 상태:** 기획 문서와 독립 HTML 시안만 있습니다. React/FastAPI, 실제 API 연결, Chrome 자동 게시 기능은 아직 구현되지 않았습니다.

## 파일

| 파일 | 용도 |
|---|---|
| `docs/reference/track-2-marketing-agent.pdf` | 과제 원문(로컬 참고용, 공개 Git 제외) |
| `.project/plan.md` | 전체 구현 범위, 필수·가점, 완료 기준 |
| `DESIGN.md` | HelpNest 스타일 대시보드 UI 기준 |
| `AGENTS.md` | Codex 공통 실행 원칙 |
| `dashboard-preview.html` | **모의 동작만 하는** HTML 디자인 시안 |
| `.gitignore` | 비밀정보·로컬 데이터 제외 |

## 기술 구성

React · TypeScript · Vite / Python · FastAPI / Ollama `qwen2.5-coder:7b` / YouTube Data API v3 / SQLite / Playwright / `.env`

## 개발 전 준비

1. Windows 11에서 Node.js, Python, Chrome, Ollama 설치 상태 확인.
2. `ollama list`로 `qwen2.5-coder:7b` 확인.
3. YouTube Data API v3 키 준비. 값은 추후 `.env`에 입력하고 Git에 올리지 않음.
4. 전용 Chrome 프로필 디렉터리 준비. 첫 로그인은 사용자가 직접 수행.
5. `docs/reference/track-2-marketing-agent.pdf` 확인. 공개 Git에는 포함하지 않음.

현재는 앱 실행 명령이 없습니다. Codex가 실제 실행에 성공하면 이 README에 검증된 PowerShell 명령을 추가합니다. HTML 시안은 `dashboard-preview.html`을 브라우저에서 열어 확인할 수 있습니다. **시안의 영상·분석·게시 단계는 모두 모의 데이터입니다.**

## Codex 첫 요청

```text
프로젝트 루트의 docs/reference/track-2-marketing-agent.pdf,
.project/plan.md, DESIGN.md, AGENTS.md, README.md를 읽으세요.
과제 PDF의 필수·가점을 구분하고 .project/plan.md에 명시된 구현 순서를 따르세요.

목표는 로컬 대시보드의 ① 영상 불러오기 → ② 선택·AI 고민/댓글 →
③ 전용 Chrome 프로필에서 실제 글자별 입력·게시·확인까지 완성하는 것입니다.
브라우저만 열거나 사용자가 직접 게시하게 하는 방식으로 바꾸지 마세요.

첫 작업만 수행하세요.
1. Windows 11용 React/TypeScript/Vite + Python/FastAPI 초기화
2. .env.example 및 필수 환경 변수 로딩/오류 처리
3. SQLite 초기화
4. Ollama(qwen2.5-coder:7b) 실제 연결 진단
5. YouTube Data API v3 연결 진단(키가 없으면 미검증 표시)
6. README에 실제 검증한 Windows PowerShell 실행 절차 작성

UI는 DESIGN.md와 dashboard-preview.html의 최신 HelpNest 스타일을 기준으로 하세요.
HTML 시안의 가상 데이터를 앱의 실제 영상 데이터처럼 사용하지 마세요.
게시 기능을 첫 작업에 선구현하지 말고, Git push·외부 게시·배포하지 마세요.
완료 시 수정 파일, 실행 명령, 통과/실패/미검증, 미해결 항목을 보고하세요.
```

## 개발 순서

1. 로컬 앱 초기화 및 Ollama/YouTube 연결
2. 지정 채널 5개 영상 조회·선택
3. Ollama 고민 분석·영상별 댓글 초안
4. 허용 채널·영상 중복·일일 상한·이력
5. `유튜브1` Chrome 프로필로 실제 글자별 입력·게시·확인
6. 본인 테스트 영상 E2E, 시연 영상·제작 의도
7. 선택 가점(프로필 선택·URL 입력·즉석 생성·후보 영상 탐색)

과제 PDF의 요구사항은 `.project/plan.md`에 대응시켰습니다. **원문 요구를 누락하지 않되 구현·검증 전에는 충족했다고 주장하지 않습니다.**
