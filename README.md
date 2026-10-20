# Marketing AI Agent

지정된 YouTube 영상의 연애 고민을 분석하고, Ollama로 마케팅 댓글 **초안**을 생성·검토하는 Windows 로컬 대시보드입니다.

> **현재 상태: 기획·UI 시안만 작성됨.** React 앱, FastAPI 서버, YouTube 연동, Ollama 연동, SQLite 저장 및 E2E는 아직 구현되지 않았습니다.

## 개발 기준 문서

| 파일 | 용도 |
| --- | --- |
| `docs/reference/track-2-marketing-agent.pdf` | 사용자 제공 과제 원문. 구현 전 요구사항 대조 기준(로컬 제공, Git 추적 제외) |
| `.project/plan.md` | 제품 범위, 과제와의 차이, 기술 구성, 기능·API·DB, 완료 기준 |
| `DESIGN.md` | HelpNest 참조 스타일, 사이드바·목록·상세 패널, 반응형·상태 UI |
| `AGENTS.md` | Codex가 항상 지킬 실행·검증 규칙 |
| `dashboard-preview.html` | 독립 HTML UI 시안. 실제 서비스 코드가 아닌 디자인 참고 자료 |
| `docs/preview-*-redesign.png` | 화면 크기별 시안 검토 자료 |

충돌 시 **현재 사용자 지시 → `.project/plan.md` → `DESIGN.md`(UI에 한정) → `AGENTS.md` → `README.md`** 순으로 판단합니다. 기능 범위의 기준은 `.project/plan.md`입니다.

## 기술 구성

- React · TypeScript · Vite
- Python · FastAPI
- Ollama `qwen2.5-coder:7b` (이미 보유한 로컬 생성 모델 사용)
- YouTube Data API v3 · SQLite
- 브라우저 검토 흐름 및 Playwright E2E
- `.env` 기반 설정. `qwen3-embedding:0.6b` 및 OpenAI API는 기본 구성에 사용하지 않음

## 시작 전 준비

1. Windows 11에 Node.js, Python, Ollama, Codex가 설치되어 있는지 확인합니다.
2. `docs/reference/track-2-marketing-agent.pdf` 파일이 있는지 확인합니다. 원문은 `.gitignore`로 Git 업로드에서 제외되므로 다른 PC에서 Git clone 후에는 직접 복사해야 합니다.
3. `ollama list`에서 `qwen2.5-coder:7b` 설치 여부를 확인합니다. 설치 여부를 추정하지 않습니다.
4. YouTube Data API v3 사용 가능한 API 키를 준비합니다. 키는 **나중에 생성할** `.env`에 보관하고 Git에 포함하지 않습니다.
5. `dashboard-preview.html`을 브라우저로 열어 확정된 UI 구조를 확인합니다. 현재 시연 데이터는 가상 데이터입니다.
6. 이 디렉터리에서 Codex를 실행하고 아래 첫 요청을 전달합니다.

## Codex 첫 요청

```text
프로젝트 루트의 docs/reference/track-2-marketing-agent.pdf, .project/plan.md, DESIGN.md, AGENTS.md, README.md를 먼저 읽으세요.
PDF를 요구사항의 원문으로 사용하되, .project/plan.md의 의도적인 범위 조정 및 현재 사용자 지시를 구분하세요.
프로젝트는 현재 기획서와 독립 HTML 시안만 존재합니다. 실제 기능이 구현된 것으로 가정하지 마세요.

첫 작업 범위:
- Windows 11에서 React/TypeScript/Vite와 Python/FastAPI의 로컬 실행 환경 구축
- .env.example 작성 및 환경 변수 로딩·필수 값 오류 처리 구현
- SQLite 연결 및 최소 초기화
- Ollama(qwen2.5-coder:7b) 연결 상태 확인 기능 구현
- YouTube Data API v3 인증·기본 연결 확인 기능 구현
- README에 실제 검증된 실행 명령과 사전 준비 사항 작성

제약:
- DESIGN.md와 dashboard-preview.html의 최신 HelpNest형 사이드바 + 영상 목록 + 우측 상세 패널 구조를 유지할 것
- UI 시안의 가상 영상·분석 결과를 실제 서비스 데이터로 복사하지 말 것
- 댓글 생성·게시 기능 등 첫 작업 외 기능은 미리 구현하지 말 것
- 실제 로컬 실행 경로를 검증하고 검증 명령, 통과/실패, 제약을 보고할 것
- 접근 불가능한 외부 API 키 또는 환경이 있으면 연결 검증을 통과했다고 주장하지 말 것
- 사용자 요청 없이 배포, Git push, 외부 서비스 쓰기 작업은 하지 말 것

첫 작업 완료 후 변경 파일, 실행 방법, 검증 결과, 남은 제약을 보고하세요.
```

## 이후 구현 순서

1. 지정 채널 5개의 실제 영상 조회·검색·선택
2. 접근 가능한 근거 수집 및 Ollama 영상 맥락 분석
3. 마케팅 댓글 초안 생성·검증·수정
4. 채널 허용·중복·일일 상한 검사와 SQLite 작업 이력
5. 브라우저에서 직접 게시하고 결과를 기록하는 흐름
6. Windows E2E 검증, 실패 기록, 시연 영상 및 문서 정리

**매 작업을 마칠 때 실제 사용자 실행 경로를 검증한 후 다음 작업으로 진행합니다.** 상세 완료 조건은 `.project/plan.md`를 따릅니다.

## 과제 원문과의 차이

원문은 Chrome 프로필로 시청자 위장형 댓글을 자동 입력·게시·확인하도록 요구합니다. 현재 설계는 광고 관계를 밝힌 댓글을 생성하고 사용자가 직접 게시하도록 제한합니다. 이 차이로 원문의 자동 게시 관련 항목을 충족하지 못할 수 있으며, 완료·제출 시 명시해야 합니다.
