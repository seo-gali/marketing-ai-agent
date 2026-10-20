# Marketing AI Agent

지정 YouTube 채널의 영상 맥락을 Ollama로 분석하고, **사용자가 승인한 홍보 고지 댓글을 전용 Chrome 프로필로 자동 입력·게시·확인**하는 Windows 로컬 대시보드입니다.

> **현재 상태: 기획·UI 시안만 제공.** React 앱, FastAPI, YouTube API, Ollama 연동, SQLite, Chrome 자동 게시 및 E2E는 아직 구현되지 않았습니다.

## 문서 및 파일

| 파일 | 역할 |
|---|---|
| `docs/reference/track-2-marketing-agent.pdf` | 최초 제공 과제 원문(로컬 참고용, 공개 Git 제외) |
| `.project/plan.md` | 기능·범위·제약·API/DB 초안·구현 순서·완료 기준 |
| `DESIGN.md` | HelpNest 스타일 대시보드 레이아웃·상태·반응형 |
| `AGENTS.md` | Codex 공통 작업 원칙 |
| `dashboard-preview.html` | 독립 실행 가능한 **디자인 시안**. 외부 API나 실제 댓글 게시 기능 없음 |
| `docs/preview-*-redesign.png` | 화면 크기별 시안 |
| `.gitignore` | 비밀정보·Chrome 프로필·DB·실패 캡처 제외 |

문서 우선순위: 현재 사용자 지시 → `.project/plan.md` → `DESIGN.md`(UI에 한정) → `AGENTS.md` → `README.md`.

## 기술 스택

React · TypeScript · Vite / Python · FastAPI / Ollama `qwen2.5-coder:7b` / YouTube Data API v3 / SQLite / Playwright (Chrome 자동 게시 및 E2E) / `.env`

`qwen3-embedding:0.6b`, OpenAI API, RAG, Redis 등은 기본 구성에 포함하지 않습니다.

## 현재 실행 가능한 것

`dashboard-preview.html` 파일을 브라우저에서 열어 영상 선택, 가상 AI 분석, 초안 편집, 승인, **게시 단계 모의 시연**을 확인합니다. 가상 데이터는 실제 영상에서 추출한 결과가 아니며 **실제 게시를 수행하지 않습니다**.

## 개발 환경 사전 확인

1. Windows 11에서 Node.js, Python, Ollama, Codex 설치 여부를 확인합니다.
2. `ollama list`에서 `qwen2.5-coder:7b`의 실제 설치 여부를 확인합니다.
3. YouTube Data API v3 키를 준비합니다. 비밀 값은 `.env`로 관리합니다.
4. `docs/reference/track-2-marketing-agent.pdf`가 있는지 확인합니다. 파일은 `.gitignore`로 공개 Git 추적에서 제외됩니다.
5. Chrome 자동화를 위해 기본 개인 프로필과 분리된 전용 프로필 디렉터리를 사용하고, 로그인은 사용자가 직접 수행합니다.

## Codex 첫 요청

```text
프로젝트 루트의 docs/reference/track-2-marketing-agent.pdf, .project/plan.md, DESIGN.md, AGENTS.md, README.md를 읽으세요.
현재는 기획 문서와 HTML 시안만 존재합니다. 구현된 기능이 있다고 가정하지 마세요.

최종 제품 범위는 영상 수집 → Ollama 분석 → 댓글 초안·수정·승인 → Playwright 전용 Chrome 프로필 자동 입력·게시·실제 확인 → 이력입니다.
수동 게시로 대체하지 마세요. 단, 시청자 위장·자동 계정 순환·광고 고지 누락은 금지합니다.

이번 첫 작업만 수행하세요.
1. Windows 11에서 React/TypeScript/Vite와 Python/FastAPI 실행 환경 구축
2. `.env.example` 및 환경 변수 로딩·필수 값 오류 처리
3. SQLite 최소 초기화
4. Ollama(qwen2.5-coder:7b) 실제 연결 진단
5. YouTube Data API v3 인증·연결 진단(API 키가 없으면 검증 불가로 표시)
6. README에 실제 실행 검증된 PowerShell 명령 작성

DESIGN.md와 dashboard-preview.html의 사이드바 + 영상 목록 + 우측 상세 패널 구조를 유지하세요.
HTML 시안의 가상 데이터를 제품 코드로 복사하지 마세요. 게시 자동화를 이번 작업에 선반영하지 마세요.
외부 서비스에 글을 게시하거나 Git push·배포하지 마세요.
실제 사용자 실행 경로를 검증한 후 수정 파일, 실행 명령, 통과/실패/미검증, 남은 제약을 보고하세요.
```

## 구현 작업 순서

1. **환경·연동:** Vite, FastAPI, `.env`, SQLite, Ollama, YouTube 연결
2. **영상 탐색:** 지정 채널 목록, 검색, 필터, 직접 URL의 채널 ID 검증
3. **AI 분석·댓글:** 근거·한계 표시, 40~120자 초안, 수정·승인
4. **운영 규칙·DB:** 허용 대상, 중복·상한·동시 실행 제한, 활동 기록
5. **Chrome 자동 게시:** 사용자 승인 → 프로필 실행 → 타이핑 → 게시 → 확인 → 실패 캡처
6. **E2E·제출:** 본인 테스트 영상에서 실제 게시 검증, 2~3분 시연 영상, 제작 의도

각 작업은 해당 기능의 실제 사용 경로가 검증된 후 완료 처리합니다.

## 과제 원문과의 차이

원문의 **자동 타이핑·게시·확인 기능은 유지**합니다. 다만 홍보 관계를 숨기는 시청자 위장형 광고와 다중 계정 순환 게시를 제외하고, 사용자가 최종 승인한 홍보 고지 댓글만 자동 게시합니다. 이 차이와 평가 영향은 최종 제출물에 명시합니다.
