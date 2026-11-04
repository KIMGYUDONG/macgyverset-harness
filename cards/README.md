# 창 카드

터미널 창마다 카드 하나를 맡긴다. 창끼리 대화할 수 없으므로 파일이 유일한 연락 수단이다. 카드를 건너뛰고 한 창으로 진행하면 [워크플로](../knowledge/workflow.md)의 단일 터미널 대체 절차를 따른다.

## 창별 입력 한 줄

각 창에 해당 줄을 그대로 붙여 넣는다. 경로는 실제 키트 위치에 맞춘다.

| 창 | 입력 |
|---|---|
| 1 지휘 | `macgyverset-harness/cards/1-lead.md를 읽고 이 창의 역할로 일해 줘.` |
| 2 기능 | `macgyverset-harness/cards/2-feature.md를 읽고 이 창의 역할로 일해 줘.` |
| 3 화면 | `macgyverset-harness/cards/3-ui.md를 읽고 이 창의 역할로 일해 줘.` |
| 4 테스트 | `macgyverset-harness/cards/4-test.md를 읽고 이 창의 역할로 일해 줘.` |
| 5 실행 | `macgyverset-harness/cards/5-run.md를 읽고 이 창의 역할로 일해 줘.` |

1번 창을 먼저 시작한다. 나머지는 `docs/board/lead.md`에 배정이 올라온 뒤 시작해도 된다.

## 게시판 규칙

- 각 창은 자기 파일 `docs/board/<lead|feature|ui|test|run>.md`에만 쓴다. 다른 창 파일은 읽기만 한다.
- 항목 형식: `[HH:MM] 상태 / 한 일 / 근거(명령, 결과) / 다른 창에 요청` ([양식](../templates/board.md))
- 단계가 시작될 때와 막혔을 때 `docs/board/lead.md`를 다시 읽는다.
- 다른 창에 부탁할 일은 자기 파일의 `요청`에 적는다. 지휘 창이 배정으로 전달한다.
- 결정과 배정은 지휘 창만 쓴다.

## 공통 규칙

- 위임: 창 안에서 동시 자식 3개 이하. 독립적이고 범위가 정해진 조사, 검증, 별도 파일 구현에만 쓴다. 작은 일은 직접 한다. 한 파일의 작성자는 한 명이며 자식은 재위임하지 않는다.
- 보고: 사용자(팀장)에게 [보고 방식](../knowledge/reporting-and-routing.md)대로 작업 전, 중, 후에 짧게 알린다.
- 담당 파일 밖은 수정하지 않는다. 필요하면 요청한다.
- 시험 경계(브라우저 자동 조작 금지, 외부 전송 금지, git push 금지)는 [START.md](../START.md)를 따른다.
