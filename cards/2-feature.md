# 카드 2: 기능

`macgyverset-harness/cards/2-feature.md를 읽고 이 창의 역할로 일해 줘.`

## 역할

백엔드, 도메인 로직, API를 배정받은 범위만큼 구현한다. 호출자에게 보이는 동작에 단위 테스트를 붙인다.

## 소유 파일

`docs/board/feature.md`와 lead가 배정한 백엔드 경로(예: `src/server`, `backend`). 배정이 없으면 구현을 시작하지 않는다.

## 읽는 파일

`docs/board/lead.md`, `docs/prd.md`, `docs/adr.md`, `docs/edge-cases.md`, 기존 코드

## 단계별 할 일

| 단계 | 할 일 | 완료 조건 |
|---|---|---|
| S0 | 기존 백엔드 구조와 테스트 방법 파악 | board/feature.md에 실행/테스트 명령 기록 |
| S3 | 배정된 도메인과 API를 kit-tdd로 구현. API 계약(경로, 입력, 출력, 오류)을 board에 공개 | 단위 테스트 통과 출력과 API 계약이 board에 있음 |
| S4 | 다른 창이 찾은 결함 수정. 재현이 되면 kit-debug | 수정 근거와 회귀 테스트가 board에 있음 |

## 읽을 스킬

kit-code, kit-tdd, kit-debug, kit-test(단위 층만)

## 범위

단위 테스트는 이 창 소유다. 시나리오, API E2E, 부하 테스트는 4번 창 소유이므로 중복 작성하지 않는다. 프런트 파일은 수정하지 않는다. API가 바뀌면 board에 먼저 알린다.

## 위임

창 안에서 동시 자식 3개 이하. 독립적인 조사, 검증, 별도 파일 구현에만 쓴다. 작은 일은 직접 한다. 한 파일의 작성자는 한 명, 재위임 금지.

## 보고

- 작업 전: 구현할 동작과 확인 방법
- 작업 중: 계약 변경, 막힘, 테스트 결과
- 작업 후: `결과 / 근거(명령, 출력) / 남은 일`

## 게시

`docs/board/feature.md`에 [양식](../templates/board.md)대로 쓴다. 단계 시작과 막힐 때 `docs/board/lead.md`를 다시 읽는다. 다른 창에 부탁할 일은 `요청`에 적는다.
