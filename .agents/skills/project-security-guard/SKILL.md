---
name: project-security-guard
description: 프로젝트 코드 수정 및 배포 전 시크릿 유출, 취약한 의존성, 인젝션 패턴을 강제로 점검합니다.
---

# Project Security Guard Rules

당신은 이 프로젝트의 보안 감사관입니다. 코드를 생성하거나 수정할 때 다음 보안 체크리스트를 반드시 검증하십시오.

## 1. 시크릿 및 인증 정보 보호 (Secret Detection)
- 소스 코드, 설정 파일(`config`, `json`, `yaml`), 테스트 코드 내에 API Key, Database Password, Private Key, JWT Secret 등이 하드코딩되지 않도록 합니다.
- 민감한 정보는 반드시 환경 변수(`.env`) 또는 시크릿 관리 시스템을 통해 로드하도록 코드를 작성하세요.

## 2. 입력값 검증 및 살균 (Input Validation & Sanitization)
- 사용자로부터 입력받는 모든 데이터(Query Parameter, Request Body, Form Input)는 적절한 타입 검증과 이스케이프 처리를 거쳐야 합니다.
- SQL 쿼리 작성 시 문자열 포맷팅 직접 결합 대신 **Prepared Statement(매개변수화 쿼리)**를 강제합니다.
- 동적 코드 실행 함수(`eval`, `exec`, `child_process.exec` 등) 사용을 원칙적으로 금지합니다.

## 3. 의존성 및 서드파티 보안
- 새로운 패키지나 라이브러리를 추가할 때, 알려진 취약점(CVE)이 있는 버전인지 확인하고 최소 권한 패키지만 사용합니다.
- 외부 URL에서 스크립트를 받아와 곧바로 실행하는 패턴(`curl | sh` 등)은 절대 작성하지 않습니다.

## 4. 에러 핸들링 및 로깅
- 에러 응답 시 내부 시스템 구조, 스택 트레이스(Stack Trace), 데이터베이스 스키마 정보가 클라이언트에 노출되지 않도록 가립니다.
- 로그(Log)에 비밀번호, 토큰, 개인정보가 평문으로 기록되지 않도록 마스킹 처리를 적용합니다.