# Writer 인터페이스

`python3 scripts/create_session_handoff.py --repo <작업 폴더> --input <JSON 경로 또는 -> --artifacts handoff,kickoff [--copy]`

`--input -`는 stdin JSON을 읽는다. `--artifacts`는 `handoff`, `kickoff`, `handoff,kickoff`를 명시한다. `--copy`는 kickoff 선택 시에만 허용한다. 기존 `--summary`와 `--next-focus`는 `--input` 없이 간단한 다이제스트를 만들 때만 사용할 수 있다. `--output-dir`는 명시적 사용자 경로 또는 격리 테스트용이며 기본 자동 로더 검색 위치 밖에 쓰면 자동 발견되지 않을 수 있다.

## 입력

최상위 JSON 객체이며 `summary`는 비어 있지 않은 문자열이다. `topic`은 선택 문자열이다. 나머지 필드는 선택적인 문자열 배열이다. 모르는 필드는 오류로 처리하여 조용히 정보를 누락하지 않는다.

```json
{
  "topic": "로그인 검증",
  "summary": "로그인 수정은 구현됐으나 만료 테스트 두 개가 실패한다.",
  "completed": ["login.ts:42 await 추가, 파일에서 확인"],
  "in_progress": ["만료 테스트 2개 수정 필요"],
  "blockers": [],
  "next_steps": ["가짜 시계 설정을 확인하고 만료 테스트 재실행"],
  "key_files": ["tests/auth/login.test.ts:88"],
  "decisions": ["기존 라이브러리 유지, 호출부 오류로 확인"],
  "rejected_alternatives": ["새 라이브러리 도입은 원인 해결에 불필요"],
  "lessons": [],
  "verification": ["테스트 명령: 3 passed, 2 failed"],
  "constraints": ["사용자가 작성한 미커밋 변경 보존"]
}
```

summary는 자동 시작 시 읽는 짧은 사실 요약이다. 실행 명령을 summary에 넣지 않는다. 검증을 제공하지 않으면 결과 미제공이라고 명시한다. writer는 판단이나 원격 조회를 수행하지 않는다.

## 출력과 원자성

stdout JSON은 `context`, `clipboard`와 선택한 `handoff`/`kickoff` 절대 경로를 반환한다. `clipboard`는 `not_requested`, `copied`, `failed` 중 하나다. 파일은 작성 시각, 랜덤 접미사로 충돌을 피하고 완성 후 덮어쓰기 없이 게시한다. 메타데이터는 Markdown을 게시한 다음 게시된다.

handoff를 선택하면 `docs/handoff/<고유 이름>-session-handoff.md`와 동일 stem의 `.handoff.json`이 생성된다. kickoff만 선택하면 handoff나 메타데이터는 생성되지 않는다. 자동 로더는 kickoff를 읽지 않는다.

메타데이터는 `schema_version: 1`, timezone 포함 ISO `created_at`, 절대 `handoff_path`, 문자열 `summary`, `topic`, `context`를 갖는다. `context_identity(cwd: Path)`는 다음 dict를 반환한다.

- `project_root`: Git main worktree 경로, 비Git은 가장 가까운 프로젝트 AGENTS 폴더 또는 cwd
- `worktree_root`: 현재 Git top-level 또는 비Git 프로젝트 폴더
- `branch`, `head`: Git 값, 없으면 null
- `session_id`: CODEX_THREAD_ID, 없으면 빈 문자열
- `cmux_workspace_id`, `cmux_surface_id`: 대응 CMUX 환경변수, 없으면 빈 문자열

모든 경로는 실경로로 정규화한다. 비Git 탐색은 부모 방향만 사용하며 home, home/code, 루트 경계에서는 더 올라가지 않는다. 전역 AGENTS를 모든 비Git 폴더의 프로젝트로 취급하지 않는다.

## 자동 로더와 레거시 호환

`load_session_context.py`는 startup과 clear에서만 과거 맥락을 준비한다. 같은 worktree와 브랜치의 schema 1 metadata를 검사하며, 세션과 주제의 반복 snapshot은 최신 기록으로 좁힌다. CMUX workspace와 surface가 맞는 후보를 우선하지만 모호하면 요약 대신 후보 목록만 제공한다. 다른 창에 묶인 기록을 조용히 자동 선택하지 않는다.

검색 metadata는 최신 파일 200개, 각 파일은 131072바이트로 제한한다. 주입 맥락은 12000자 이하이며 7일 이상 지난 기록과 변경된 HEAD를 경고한다. kickoff는 자동 로드하지 않는다. 로더는 파일을 변경하지 않으며 오류가 나도 새 세션을 막지 않는다.

`docs/handoff/`에 `.handoff.json` 후보 파일이 하나도 없을 때만 같은 worktree 내부의 기존 `.claude/HANDOFF.md`를 읽는다. 레거시 파일은 branch, session, window 일치를 검증할 metadata가 없다는 경고와 함께 제한된 역사 참고 자료로 제공한다. 파일 크기, UTF-8, worktree 내부 경로를 확인하며 외부 symlink는 거부한다. 현대 후보가 손상됐거나 다른 브랜치에 속하거나 모호하면 레거시 본문으로 우회하지 않는다. 인계 맥락은 새 작업을 실행하거나 재개를 먼저 제안할 권한이 아니다.

Claude의 기존 Node 훅과 설치 asset은 공유 Python 로더를 호출하는 얇은 어댑터다. 기존 등록 명령과 timeout을 유지하며 Python 실패, 비정상 출력, 시간 초과에도 세션을 계속한다. writer와 loader의 오프라인 검사 통과는 실제 새 native 세션의 로딩 성공과 구분한다.
