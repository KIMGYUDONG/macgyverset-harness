# MacGyverSet Harness (맥가이버셋 하네스)

평소 사용하는 요구사항 정리, TDD, 역할 위임과 검증 습관을 제공된 Codex에 가져가는 작은 공개 키트입니다. 정답 코드나 앱 완성본은 포함하지 않습니다. Python 패키지 설치, Docker, MCP, 개인 API 키가 필요하지 않습니다. 공식 스킬은 고정한 원출처에서 내려받고, 개인 session-handoff는 지원 파일과 함께 포함합니다.

## 시험 환경에서 가져오기

과제의 작업 공간 루트에서 실행합니다. 처음에는 pull 대신 clone을 사용합니다.

```sh
git clone --depth 1 --branch v0.3.3 https://github.com/KIMGYUDONG/macgyverset-harness.git macgyverset-harness
```

제공된 Codex에 다음 한 번만 요청합니다. START.md가 작업 공간 안의 스킬 등록과 지침 적용까지 이어갑니다.

```text
macgyverset-harness/START.md를 읽고 맥가이버셋 하네스를 설치한 뒤 이 과제에 적용해 줘.
```

처음 접하는 에이전트에는 주소를 포함하면 저장소를 확실히 식별할 수 있습니다.

```text
https://github.com/KIMGYUDONG/macgyverset-harness 의 맥가이버셋 하네스를 설치해 줘.
실제 과제 루트에서 clone의 START.md를 읽고 작업 공간 스킬 등록까지 진행해 줘.
```

등록 뒤에는 “맥가이버셋 하네스 설치해줘” 또는 “맥가이버셋 하네스 적용해줘”로 요청할 수 있습니다. Git clone 자체는 스크립트를 실행하지 않습니다. 이름만 처음 제시했을 때 새 에이전트가 저장소를 알아낸다고 보장하지 않습니다.

## 여러 창으로 풀기

1. 터미널 1에서 위 clone과 설치 요청을 마친다.
2. 터미널 2~5를 열고 각각 `codex`를 실행한 뒤 [창 카드](cards/README.md)의 진입문 한 줄을 붙여넣는다.
3. 창 1이 만든 담당자 질문을 오른쪽 담당자 에이전트에 직접 전달하고, 답을 `docs/board/lead.md`에 붙여넣는다.

창끼리는 `docs/board/`의 파일로만 소통한다. 단계와 완료 조건은 [작업 단계](knowledge/workflow.md)에 있다.

## 터미널에서 한 번에 준비

과제 루트에서 clone 다음 명령을 실행하면 파일 등록까지 끝납니다(Python 3.9 이상).

```sh
python3 macgyverset-harness/scripts/prepare.py --workspace "$PWD"
```

기존 AGENTS.md와 Codex 설정은 바꾸지 않습니다. 파일 배치와 현재 세션의 스킬 목록 갱신은 별개입니다. 목록에 바로 나타나지 않아도 START.md의 링크로 직접 읽어 사용합니다. 공식 스킬은 START.md에 따라 원출처에서 필요한 때 내려받습니다. session-handoff 실행은 Python 3.10 이상입니다.

이미 v0.1.0을 harness-kit 폴더에 받은 경우, 새 버전은 별도 macgyverset-harness 폴더에 위 명령으로 clone하면 됩니다. 이전 폴더나 과제 파일을 지우거나 덮어쓸 필요가 없습니다.

## 구성

- [시작 안내](START.md): 규칙, 스킬 선택, 작업 흐름.
- [공식 다운로드](README-OFFICIAL.md): 원출처, 고정 버전과 무결성 확인.
- [보고와 모델 선택](knowledge/reporting-and-routing.md): 팀장에게 보고하는 형식과 속도/품질 기준.
- [세션 인계](skills/session-handoff/SKILL.md): 기존 스킬과 writer/loader, 참고 자료와 테스트.
- [개발 원칙](knowledge/development-principles.md): 선별한 8개 원칙과 적용 조건.
- [역할 지침](agents/README.md): 메인, 탐색, 구현, 독립 검증.
- [작업 기록 양식](templates/work-record.md): 판단, 실행 증거와 남은 한계.
- [검증 기록](docs/plans/2026-10-31-harness-kit.md): 제작 범위와 실제 확인 결과.

## 세션 인계 사용

과제풀이 중 맥락 정리가 필요하면 `macgyverset-harness/skills/session-handoff/SKILL.md를 읽고 인계 문서와 시작 프롬프트를 만들어 줘`라고 요청합니다. 작성 결과는 작업 공간의 docs/handoff에 남습니다. writer/loader와 기존 회귀 테스트를 함께 포함하지만, 자동 로딩 hook은 설치하지 않습니다. 시험 중에는 클립보드와 전역 메모리를 변경하지 않습니다.

## 사용 경계

이 키트는 대회 운영팀이 인증한 도구가 아닙니다. 실제 과제 안내와 최신 운영 공지를 우선합니다. 제공된 Codex만 사용하고 Codex 업데이트, 외부 모델 연결, 개인 API 키, Computer Use와 브라우저 자동 조작을 사용하지 않습니다. 시험 문제, 파일과 결과물을 외부로 전송하거나 Git push하지 않습니다. 후속 서술형 단계에서는 AI와 복사/붙여넣기를 사용하지 않습니다.

공개 키트를 사용하는 대회에서는 결과 통지 전까지 저장소 공개 상태를 유지합니다. 시험 중 이 저장소에 문제나 작업물을 올리지 않습니다.

## 개발 검증

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check.py
python3 -m unittest discover -s skills/session-handoff/tests -v
```

12개 kit 스킬은 이 저장소를 위해 새로 작성했습니다. session-handoff는 기존 개인 스킬에서 개인 경로와 시험 적용 경계만 조정한 이식본입니다. 공식 스킬은 이 저장소에서 재작성하지 않고 원출처에서 내려받습니다. 개인 워크플로의 책임을 추려 재구성했으며, 플러그인 전용 원문, 유료 도구, 개인 기록을 배포하지 않습니다. 형식 참고: [Codex skills](https://learn.chatgpt.com/docs/build-skills), [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
