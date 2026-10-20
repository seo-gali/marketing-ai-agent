# 구현 및 검증 결과

검증일: 2026-10-20~21, Windows 11 / Chrome 155 / Node 24.19 / Python 3.13.14.
실제 게시와 자막·장면 검증이 남아 있으므로 과제 전체 완료로 판정하지 않습니다.

## 요구사항별 상태

| 항목 | 구현·검증 상태 |
|---|---|
| F1 영상 조회 | 실제 YouTube API로 지정 5채널, 채널당 8영상 조회. 썸네일·제목·채널·날짜·검색·필터 확인 |
| F2 고민·초안 | 실제 Ollama `qwen2.5-coder:7b` 추론. 음악 영상은 연애 고민 확인 불가, 연애 영상은 마음 변화 고민으로 구분 |
| F3 맥락·장면 | 제목·설명·공개 인기 댓글 및 출처 발췌 구현. 자막 수집 미구현, 실제 장면·발언 확인 기준 미충족 |
| F4 댓글 제약 | 서버의 40~120자·브랜드·광고 표시·링크·해시태그·금지 경험 표현·동일 댓글 검사. 모델의 의미적 사실 여부는 사용자 검토 필요 |
| F5 지정 프로필 | 앱의 지정 폴더로 `launch_persistent_context` 실행과 한국어 YouTube 접근 확인. 기본 프로필 사용 안 함 |
| F6 실제 게시 | 글자별 입력·게시·계정/본문/댓글 링크 대조·새로고침 확인 코드 구현. 로그인된 지정 프로필의 실제 YouTube 게시는 미검증 |
| F7 상태·오류 | 서버 상태 폴링·실패 원인·스크린샷·확인 불가 표시 구현. 로컬 브라우저 검사로 확인 |
| F8 게시 제한 | API 채널 재확인·영상 중복 방지·최대 10건·동시 예약·제출 직전 날짜/상한 재검사 |
| F9 이력 | SQLite 작업/단계 기록·초안/분석 저장·서버 재시작 후 DB 유지 확인 |
| F10 제출 | 제작 의도 아래 작성. 실제 게시가 포함된 2~3분 시연 영상 및 공개 링크는 미제작 |
| B1 프로필 2·3 | 선택 가점, 미구현 |
| B2 URL 입력 | 실제 메타데이터 조회와 서버 허용 목록 검사 구현·검증 |
| B3 즉석 생성 | 실제 모델 기반 신규 분석·재생성 구현·검증 |
| B4 후보 영상 탐색 | 선택 가점, 미구현 |

현재 사용자의 명시적 지시에 따라 광고 관계를 밝히고 본문 승인 후 게시합니다.
프로필 비교·인증 유지의 독립 검증·프로필 재사용 구조 변경은 범위에서 제외했습니다.

## 실행 결과

| 명령 또는 경로 | 실제 결과 |
|---|---|
| `npm.cmd ci` | 실행 중 Vite의 Windows 모듈 잠금으로 최초 실패. 해당 개발 서버 종료 후 재실행 성공, 24패키지 설치 |
| `npm.cmd run build` | TypeScript 검사 및 Vite 빌드 성공 |
| `python -m pip install -r requirements.txt` | 지정된 4개 런타임 의존성 설치 확인 |
| `python -m pip check` | No broken requirements found |
| `python -m unittest discover -s tests -v` | 14검사 통과, 31.995초. 임시 SQLite·격리된 headless Chrome 로컬 픽스처 사용 |
| `python scripts/verify_e2e.py` / 5173 | 초기 화면의 실제 앱·API E2E 통과 |
| 동일 E2E / 8000 | 사용자 참조 디자인 반영 후 실제 프로덕션 번들에서 통과 |
| `python scripts/verify_accessibility.py` | 키보드·구조·주요 대비·오류 경계·HTML 안내 문서 검사 통과 |
| `python scripts/backup_db.py` | SQLite Backup API 복사 및 무결성 검사 통과 |
| `npm.cmd audit` | 알려진 취약점 0건 |
| 개발 가상환경 `python -m pip_audit` | 알려진 취약점 0건. 최초 발견된 개발 도구 pip 취약점은 26.2.1로 수정 후 재검사 |

최종 프로덕션 E2E는 2026-10-21 00:46 KST에 통과했습니다.
확인 항목은 실제 5채널 40영상, 필터·빈 검색어 0건·API 422·명시적 전체 조회·초기화 취소,
테스트 URL 선택, 71자 광고 초안 표시·수정 저장·편집 시 승인 초기화,
만료 임시 저장 정리·새로고침 후 초안 복구·복구 시 미승인 유지,
미승인 422·금지 채널 403·외부 URL 422·외부 Origin 403,
1440·1024·390px 가로 넘침 없음·JavaScript 오류 0개입니다.
모바일의 영상 탐색·이력·환경·404, 내부 링크·로고·푸터·파비콘·제목·메타 설명도 확인했습니다.

화면은 사용자 제공 `marketing-ai-agent-implemented`의 구성·색상·아이콘을 참고해 실제 API에 연결했습니다.
상세 보안 결과는 [보안 감사](security-audit.md), 키보드·스크린리더 관련 범위와 한계는
[접근성 검수](accessibility.md)에 기록했습니다.

브라우저 픽스처에서는 실제 키보드 입력 이벤트 수, 제출 1회, 계정과 본문 대조,
새로고침 후 확인, 확인 불가 시 중복 차단, 로그인 필요 시 입력 전 중단과 캡처를 검사했습니다.
이는 실제 YouTube 게시 결과를 대체하지 않습니다.

Playwright MCP로 초기 Windows 대시보드와 실제 한국어 YouTube 댓글 UI를 확인했습니다.
테스트 영상은 음악 영상이며 실제 UI에서 댓글 0개·댓글 입력란을 관찰했습니다.
이후 앱의 브라우저 코드는 Python Playwright로 구현했으며 MCP를 런타임에서 호출하지 않습니다.

## 로컬 증거

- `artifacts/e2e-result.json`, `artifacts/e2e-production-result.json`: 화면 E2E 결과, 외부 게시 미실행 명시
- `artifacts/live-analysis.json`: 실제 Ollama 분석 2건의 모델·시각·초안
- `artifacts/accessibility-result.json`, `artifacts/accessibility-tree.json`: 키보드·구조·대비·HTML 검사
- `artifacts/docs-overview.png`: 초보자용 HTML 안내 문서
- `artifacts/dashboard-1440.png`, `dashboard-1024.png`, `dashboard-390.png`: 실제 화면
- `artifacts/youtube-test-ui.png`: 실제 한국어 댓글 UI
- `local/screenshots/`: 브라우저 오류 캡처

인증정보·DB·캡처·과제 PDF·로컬 아티팩트는 Git에 포함하지 않았습니다.

## 실제 게시의 남은 확인

본인 테스트 영상 `DPFhGxGM8qQ`와 아래 71자 문구는 사용자 승인을 받았습니다.

> [광고] 운명원 연애 사주 콘텐츠 소개입니다. 시간여행자를 참고한 자동화 기능 테스트 댓글이며, 영상 내용과 광고는 별개입니다.

지정 프로필의 로그인된 실제 계정 접근이 확인되지 않아 이 문구의 입력·게시·확인을 완료하지 않았습니다.
실제 계정 UI의 계정 핸들·게시 버튼·댓글 링크 선택자는 추가 실계정 검증이 필요합니다.
실제 계정에서 성공을 확인하지 않은 상태를 성공으로 기록하거나 자동 재시도하지 않았습니다.

## 제작 의도

영상 목록·분석·게시를 세 단계로 구분해 초안의 근거를 확인한 후 사람이 게시 여부를 결정하게 했습니다.
로컬 Ollama를 사용해 별도 AI API 비용을 추가하지 않고, 메타데이터·공개 댓글을 실제 자료로 사용합니다.
구체적 장면이 확인되지 않으면 그 한계를 표시하고 광고 관계와 이용 경험을 꾸미지 않습니다.

운영 규칙은 프런트엔드 버튼 상태와 별개로 FastAPI·SQLite에서 다시 검사합니다.
SQLite 즉시 트랜잭션과 고유 인덱스로 동시 중복을 막고, 제출 전에 시도를 기록해
서버 중단이나 응답 불명확 상황에서 같은 댓글을 다시 게시하지 않도록 했습니다.
요청 범위를 위해 별도 작업 큐·스케줄러·외부 인프라는 도입하지 않았습니다.

## 단계별 커밋

| 단계 | 커밋 | 내용 |
|---|---|---|
| 1 | `22554f2` | 프로젝트 실행 환경 |
| 2 | `c5ec555` | 실제 YouTube 영상 조회 |
| 3 | `54d58c2` | Ollama 분석·초안 생성 |
| 4 | `68169bb` | 게시 규칙·SQLite 이력 |
| 5 | `4566573` | 지정 Chrome 자동 게시 코드·격리 검증 |
| 6 | `82e70ff` | 대시보드 API 연결 |
| 보완 | `5719864` | API 보안·입력·페이지네이션·백업 |
| 보완 | `2983fce` | 참조 디자인·모바일·사용성·접근성 |

7단계 문서 커밋 메시지: `docs: finalize setup and verification`.
해당 커밋의 해시는 최종 보고와 `git log`에서 확인할 수 있습니다.

구현 참고: [YouTube Data API](https://developers.google.com/youtube/v3),
[Ollama Chat API](https://docs.ollama.com/api/chat),
[Playwright Python](https://playwright.dev/python/docs/api/class-browsertype),
[Vite](https://vite.dev/guide/). 이 문서의 성공 판정은 실제 로컬 실행 결과에 근거합니다.
