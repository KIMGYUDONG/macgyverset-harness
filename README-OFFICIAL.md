# 공식 원본 스킬을 선택적으로 내려받기

이 저장소의 `kit-*`는 시험용 지침입니다. 원본이 필요하면 아래 도구로 [obra/superpowers](https://github.com/obra/superpowers/tree/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b)의 고정 커밋에서 직접 내려받습니다. 원본을 다시 쓴 문서를 공식 원본으로 제공하지 않습니다.

대상은 `brainstorming`, `systematic-debugging`, `test-driven-development` 세 디렉터리의 모든 파일과 LICENSE입니다. 총 22개 파일, 137,233바이트이며 경로, 크기, SHA-256은 `official-skills.lock.json`에 기록되어 있습니다. 다른 superpowers 스킬, 플러그인, hook은 설치하지 않습니다.

## 실행

제공된 응시 작업 환경의 허용된 터미널에서 한 번 실행합니다. 과제 풀이 중에도 허용된 공개 자료 다운로드 범위에서 실행할 수 있습니다. 개인 PC에서 준비한 파일을 업로드하지 않습니다. `examroot`는 이미 존재하는 실제 응시 작업 폴더로 바꿉니다.

```bash
cd examroot
python3 macgyverset-harness/scripts/fetch_official.py --output harness-official
```

위 명령은 `examroot/harness-kit`에 이 저장소를 받은 배치입니다. 출력 폴더는 새로 만들거나 기존 디렉터리를 사용할 수 있으며, 부모 디렉터리는 존재해야 합니다. 다른 위치에서 실행한다면 `--output`에 원하는 실제 응시 작업 폴더의 `harness-official` 경로를 지정합니다. 상대 경로는 현재 작업 폴더 기준입니다.

이 도구는 지정 커밋의 `raw.githubusercontent.com/obra/superpowers` 파일만 GET으로 요청합니다. 주소나 커밋을 CLI 옵션이나 lock의 URL로 바꿀 수 없으며 리다이렉트도 거부합니다. 파일당 최대 1 MiB, 전체 최대 4 MiB, 요청당 20초 제한을 적용합니다. 모든 파일의 크기와 SHA-256을 검증한 뒤에만 쓰기를 시작합니다.

기존 파일은 로컬 크기와 해시로 검증합니다. 모두 같으면 네트워크 요청 없이 `unchanged`로 반환하며, 일부만 없으면 누락 파일만 내려받습니다. 기존 파일이 다르거나 대상 경로에 심볼릭 링크가 있으면 오류로 종료하며, 충돌과 다운로드/해시 오류가 있는 경우 새 파일을 만들지 않습니다. 결과는 `status`, `installed`, `unchanged`가 있는 JSON입니다. 오류는 stderr JSON과 종료 코드 1로 반환합니다.

## 원본을 읽는 방법

내려받는 위치는 자동 스킬 탐색 경로가 아닙니다. 도구는 `.agents` 아래와 이 kit checkout 내부 출력을 거부하고, 전역 설정이나 루트 지침을 바꾸지 않습니다. 다음 파일을 필요한 작업에서 직접 읽습니다.

- `harness-official/skills/brainstorming/SKILL.md`
- `harness-official/skills/systematic-debugging/SKILL.md`
- `harness-official/skills/test-driven-development/SKILL.md`

읽을 때는 먼저 `START.md`와 해당 `kit-*` 지침을 적용합니다. 이 시험용 지침과 사용자의 지시가 원본의 일반 작업 흐름보다 우선합니다. 제공된 Codex만 사용하고 다른 AI CLI, 사설 API, Computer Use, 브라우저/UI 자동화, 시험 데이터 외부 전송을 실행하지 않습니다. 저장소는 결과 발표까지 공개 상태를 유지합니다.

원본 brainstorming에는 visual companion, 문서 승인 단계, commit, `superpowers:writing-plans` 호출이 포함됩니다. 지원 파일의 완전성을 위해 visual companion 스크립트도 내려받지만 실행하지 않습니다. 승인된 작업을 반복 승인 단계로 돌리지 않고, 계획은 `kit-plan`에 따라 작성합니다. 원본에 다른 스킬 이름이 등장해도 추가 프레임워크나 provider를 설치하지 않습니다.

원본 systematic-debugging은 원인 조사 후 수정하는 디버깅 절차이며, `.sh`와 `.ts` 파일은 읽기 전용 참고자료로 실행하지 않습니다. `test-*.md`와 `CREATION-LOG.md`는 스킬 제작 기록이므로 작업에 적용하지 않습니다.

원본 TDD의 RED, GREEN, Refactor와 테스트 작성 참고자료는 `kit-tdd`, `kit-verify`의 범위 안에서 활용합니다. 원본의 예외 절차나 삭제 지시를 근거로 기존 사용자 코드를 지우지 않습니다. commit/push, 브라우저 실행, 새로운 승인 반복은 이 다운로드나 원본 읽기로 허가되지 않습니다.

응시 작업 환경에서 내려받은 뒤에는 로컬 파일만 읽습니다. 이미 모든 파일이 동일하면 도구를 다시 실행해도 네트워크 요청을 하지 않습니다. 이 도구는 선택 사항이며 시험 입력이나 풀이를 업로드하지 않습니다. 내려받은 `LICENSE`를 원본과 함께 유지합니다.
