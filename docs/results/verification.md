# 구현 및 검증 결과

검증일: 2026-10-20~21, Windows 11 / Chrome 155 / Node 24.19 / Python 3.13.14.
실제 YouTube 1회 게시·다른 계정의 공개 확인 및 연애 영상 2건의 화면 자막 근거 검증 완료.
2~3분 제출 영상·공개 시연 링크 미제작. 점수와 모든 영상의 분석 품질을 보장하는 판정은 아닙니다.

## 요구사항별 상태

| 항목 | 구현·검증 상태 |
|---|---|
| F1 영상 조회 | 실제 YouTube API로 지정 5채널, 채널당 8영상 조회. 썸네일·제목·채널·날짜·검색·필터 확인 |
| F2 고민·초안 | 실제 Ollama `qwen2.5-coder:7b` 추론. 음악 영상은 연애 고민 확인 불가, 연애 영상은 마음 변화 고민으로 구분 |
| F3 맥락·장면 | 공개 스크립트 UI 우선 수집. 조회 실패 시 재생된 초반 화면 자막의 Windows OCR·시각·캡처 수집. 실제 연애 영상 2건에서 인용·시각·캡처 연결 확인. 근거 미확보 영상은 메타데이터 분석 표시 |
| F4 댓글 제약 | 서버의 40~120자·브랜드·광고 표시·링크·해시태그·금지 경험 표현·동일 댓글 검사. 모델의 의미적 사실 여부는 사용자 검토 필요 |
| F5 지정 프로필 | 앱의 지정 폴더로 `launch_persistent_context` 실행과 한국어 YouTube 접근 확인. 기본 프로필 사용 안 함 |
| F6 실제 게시 | 지정 프로필에서 승인된 본문 글자별 입력·1회 게시·계정/본문/댓글 링크 대조·새로고침 확인 성공. 사용자의 다른 계정에서도 공개 확인 |
| F7 상태·오류 | 서버 상태 폴링·실패 원인·스크린샷·확인 불가 표시 구현. 로컬 브라우저 검사로 확인 |
| F8 게시 제한 | API 채널 재확인·영상 중복 방지·최대 10건·동시 예약·제출 직전 날짜/상한 재검사 |
| F9 이력 | SQLite 작업/단계 기록·초안/분석 저장·서버 재시작 후 DB 유지 확인 |
| F10 제출 | 제작 의도 아래 작성. 실제 게시가 포함된 2~3분 시연 영상 및 공개 링크는 미제작 |
| B1 프로필 2·3 | 환경 설정의 추가·선택·일반 Chrome 로그인 실행 및 게시 프로필 전달 구현. 임시 Chrome 프로필의 실제 폴더 분리 확인. 유튜브2·3의 실계정 로그인·실게시 미검증 |
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
| `python -m unittest discover -s tests -v` | 24검사 통과, 37.443초. 게시 규칙·보안·근거·프로필 폴더 분리·삭제 후 상한/중복 차단 검사 |
| `python scripts/verify_e2e.py` / 5173 | 초기 화면의 실제 앱·API E2E 통과 |
| 동일 E2E / 8000 | 사용자 참조 디자인 반영 후 실제 프로덕션 번들에서 통과 |
| `python scripts/verify_accessibility.py` | 키보드·구조·주요 대비·오류 경계·HTML 안내 문서 검사 통과 |
| `python scripts/verify_analysis_e2e.py` | 실제 연애 영상 2건의 근거·시각·캡처·서로 다른 광고 초안·미승인 상태·모바일 검사 통과. 두 번째 영상은 실제 신규 Ollama 추론 |
| `python scripts/verify_settings_e2e.py` | 격리된 SQLite와 실제 FastAPI에서 프로필 추가·설정 유지·이력별 페이지·삭제/복원·오류 재조회·모바일 검사 통과. 외부 게시 없음 |
| `python scripts/backup_db.py` | SQLite Backup API 복사 및 무결성 검사 통과 |
| `npm.cmd audit` | 알려진 취약점 0건 |
| 개발 가상환경 `python -m pip_audit` | 알려진 취약점 0건. 최초 발견된 개발 도구 pip 취약점은 26.2.1로 수정 후 재검사 |

프로덕션 E2E는 2026-10-21 실제 앱에서 통과했습니다.
확인 항목은 실제 5채널 40영상, 필터·빈 검색어 0건·API 422·명시적 전체 조회·초기화 취소,
허용 채널 URL 선택, 광고 초안 표시·수정 저장·편집 시 승인 초기화,
만료 임시 저장 정리·새로고침 후 초안 복구·복구 시 미승인 유지,
미승인 422·금지 채널 403·외부 URL 422·외부 Origin 403,
1440·1024·390px 가로 넘침 없음·JavaScript 오류 0개입니다.
모바일의 영상 탐색·이력·환경·404, 내부 링크·로고·푸터·파비콘·제목·메타 설명도 확인했습니다.
추가 UI 수정 후 아이콘 중앙 정렬·저장소 푸터·번호 페이지 이동 검사 및 게시 규칙 7건을 재실행해 통과했습니다.
루트 HTML 코드 정렬 후 TypeScript·Vite 빌드도 통과했습니다.

화면은 사용자 제공 `marketing-ai-agent-implemented`의 구성·색상·아이콘을 참고해 실제 API에 연결했습니다.
상세 보안 결과는 [보안 감사](security-audit.md), 키보드·스크린리더 관련 범위와 한계는
[접근성 검수](accessibility.md)에 기록했습니다.

브라우저 픽스처에서는 실제 키보드 입력 이벤트 수, 제출 1회, 계정과 본문 대조,
새로고침 후 확인, 확인 불가 시 중복 차단, 로그인 필요 시 입력 전 중단과 캡처를 검사했습니다.
실제 YouTube 게시 결과는 아래 별도 항목에 기록했습니다.

Playwright MCP로 초기 Windows 대시보드와 실제 한국어 YouTube 댓글 UI를 확인했습니다.
테스트 영상은 음악 영상이며 실제 UI에서 댓글 0개·댓글 입력란을 관찰했습니다.
이후 앱의 브라우저 코드는 Python Playwright로 구현했으며 MCP를 런타임에서 호출하지 않습니다.

## 로컬 증거

- `artifacts/e2e-result.json`, `artifacts/e2e-production-result.json`: 화면 E2E 결과, 외부 게시 미실행 명시
- `artifacts/live-analysis.json`: 실제 Ollama 분석 2건의 모델·시각·초안
- `artifacts/grounded-e2e-result.json`: 연애 영상 2건의 화면 자막 인용·시각·캡처·서로 다른 초안
- `artifacts/settings-e2e-result.json`: 격리 DB의 실제 설정·이력 API/화면 검증
- `artifacts/settings-light.png`, `settings-dark.png`, `settings-mobile.png`: 테마·프로필 설정 화면
- `artifacts/history-posting.png`, `history-activities.png`: 분리된 게시 작업·활동 기록
- `artifacts/live-posting-result.json`: 승인된 1회 게시의 실제 성공 결과
- `artifacts/live-posting-other-account.png`: 사용자가 다른 계정에서 확인한 공개 댓글
- `artifacts/accessibility-result.json`, `artifacts/accessibility-tree.json`: 키보드·구조·대비·HTML 검사
- `artifacts/docs-overview.png`: 초보자용 HTML 안내 문서
- `artifacts/docs-e2e-result.json`: 프로젝트 소개·탭·Markdown 팝업의 로컬 검증
- `artifacts/docs-pages-result.json`: `DOCS_URL` 지정 시 공개 Pages 검증 결과
- `artifacts/dashboard-1440.png`, `dashboard-1024.png`, `dashboard-390.png`: 실제 화면
- `artifacts/youtube-test-ui.png`: 실제 한국어 댓글 UI
- `local/screenshots/`: 브라우저 오류 캡처

인증정보·DB·캡처·과제 PDF·로컬 아티팩트는 Git에 포함하지 않았습니다.

## 프로젝트 소개 페이지

공개 주소: https://seo-gali.github.io/marketing-ai-agent/

기본 탭은 프로젝트 소개, 별도 탭은 앱 점검 현황입니다. README·구현 결과·보안 감사·접근성 문서는
공개 저장소 원문을 가져와 팝업 안에서 제목·표·목록·코드·인용·링크로 표시합니다.
새 패키지 없이 저장소 문서에 사용된 Markdown 문법을 처리하며, 원문의 HTML은 실행하지 않습니다.

`python scripts/verify_docs.py`의 로컬 검증은 통과했습니다. 실제 문서 4개의 조회·서식,
키보드 탭 이동·팝업 포커스 순환·Escape·닫은 뒤 포커스 복귀, 390/1440px 넘침을 확인했습니다.
조회 오류와 위험한 HTML·링크의 차단은 브라우저 응답 픽스처로 검사했습니다.

공개 배포본 검증 명령:

```powershell
$env:DOCS_URL='https://seo-gali.github.io/marketing-ai-agent/'
./.venv/Scripts/python.exe scripts/verify_docs.py
Remove-Item Env:DOCS_URL
```

Pages는 정적 소개 페이지입니다. FastAPI·Ollama·Chrome 게시 앱의 실행 환경은 Windows 로컬입니다.

## 환경 설정·이력 정리

- 사이드바 연결 상태등·API 확인 버튼·소형 새로고침 통합, 푸터의 중복 상태 링크·설정 화면의 연결 정보 카드 제거
- API 확인: 새 창 없이 `/api/health` 호출, HTTP 200 초록불·503 빨간불·재확인 복구 검증. 푸터 저장소 링크 오른쪽 정렬
- API 확인 중·실패·복구 시 Ollama/YouTube의 표시 문구·상태등 유지 확인. 상단 새로고침만 전체 상태 갱신
- 영상 불러오기와 채널 목록 사이 URL 입력 제거. ‘채널 추가’ 탭의 URL 입력·조회 목록과 지정 채널의 기존 목록·검색 상태 분리
- 환경 설정: Chrome 프로필·라이트/다크 테마·작성 중인 댓글 보관의 세 영역
- 유튜브2·3 등록과 선택 저장, 유튜브1 기존 폴더 유지. 로그인 버튼은 지정 폴더의 일반 Chrome 실행
- 게시 작업·활동 기록별 독립 페이지 수, 데이터 로딩·오류·빈 목록 구분 및 재조회
- 개별/전체 이력 삭제·실행 취소. SQLite 표시 제외 방식이며 실제 댓글·일일 상한·중복 차단 기록 유지
- 키보드 프로필 선택·삭제 취소·다크 모드 전환, 모바일 메뉴의 연결 상태 접근 확인
- 다크 모드 대비 표본: 제목 13.68:1 · 안내 8.84:1 · 선택 버튼 9.58:1

설정·이력 E2E는 5173 포트의 임시 FastAPI 및 별도 SQLite에서 수행했습니다.
검증용 게시 결과는 픽스처이며, 기존 실게시 기록의 삭제나 추가 YouTube 게시를 실행하지 않았습니다.
유튜브2·3 실제 Google 계정은 등록하지 않았으므로 해당 계정의 로그인·실게시는 미검증입니다.

## 실제 게시 결과

본인 테스트 영상 `DPFhGxGM8qQ`와 아래 71자 문구는 사용자 승인을 받았습니다.

> [광고] 운명원 연애 사주 콘텐츠 소개입니다. 시간여행자를 참고한 자동화 기능 테스트 댓글이며, 영상 내용과 광고는 별개입니다.

2026-10-21 18:39 KST, 지정 프로필 `유튜브1`에서 실제 글자별 입력·게시·새로고침 후 계정/본문 확인 성공.
작업 ID: `2dfb3701ce7f44c39f4471256ec3ea35` · 제출 시도 1회 · 최종 상태 `success`.
[게시된 댓글](https://www.youtube.com/watch?v=DPFhGxGM8qQ&lc=Ugw1fcik3bEx8RozpCB4AaABAg).
사용자가 다른 계정에서도 공개 댓글을 확인하고 화면을 제공했습니다.

최초 Google 로그인 거부는 동일 지정 폴더의 일반 Chrome에서 사용자가 직접 로그인하는 절차로 처리했습니다.
기본 프로필 변경·쿠키 복사·자동화 탐지 우회는 적용하지 않았습니다.
이 영상은 이미 게시 완료 상태이므로 중복 차단을 유지합니다. 새 게시 촬영에는 별도 본인 테스트 영상과 본문 승인이 필요합니다.

## 영상 근거와 초안

실제 검사 영상: `akn-AvCeHBI` · `DvxMfC_KjX0`.
첫 영상의 0:33 화면 문구, 두 번째 영상의 0:38 화면 문구를 각각 인용하고 원본 시각 링크와 캡처를 표시했습니다.
공개 스크립트 응답은 `400 FAILED_PRECONDITION`으로 실패해 접근 제한을 우회하지 않고 화면 OCR 경로를 사용했습니다.
버퍼링 중 과거 프레임에 이동 시각을 붙이지 않도록 임의 탐색을 없애고 실제 디코딩된 프레임을 정지한 뒤 수집합니다.
수집 범위는 초반 네 구간이며 전체 영상 분석·음성 인식은 아닙니다. 화면 자막이 없으면 근거 미확보 경고를 표시합니다.
OCR 띄어쓰기·문자 오류가 가능하므로 게시 전 캡처와 인용문 대조가 필요합니다.

모델은 실제 출처에서 인용문을 선택하고 영상의 고민을 요약합니다. 서버는 원문 일치·길이·광고 표시·금지 표현을 검사하고
운명원 연애 사주를 살펴보는 문구를 조합합니다. 이용 경험·적중·고민 해결 보장은 포함하지 않습니다.
관심 유도 문구의 평가 점수와 의미적 정확성은 자동 검사만으로 보장하지 않습니다.

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
