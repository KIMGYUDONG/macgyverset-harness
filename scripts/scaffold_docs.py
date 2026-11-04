#!/usr/bin/env python3
"""Create the development docs skeleton in a task workspace without overwriting files."""
import argparse, json
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
T = KIT / "templates"

LAYOUT = {
    "docs/README.md": None,
    "docs/problem-definition.md": "problem-definition.md",
    "docs/prd.md": "prd.md",
    "docs/adr.md": "adr.md",
    "docs/edge-cases.md": "edge-cases.md",
    "docs/optimization.md": "optimization.md",
    "docs/test-report.md": None,
    "docs/manuals/admin.md": "manual-admin.md",
    "docs/manuals/user.md": "manual-user.md",
    "docs/manuals/reviewer.md": "manual-reviewer.md",
    **{f"docs/board/{r}.md": "board.md" for r in ("lead", "feature", "ui", "test", "run")},
}

INDEX = """# 개발 문서 라우팅

에이전트는 이 파일을 먼저 읽고, 아래 표에서 고른 파일만 연다. 각 문서의 첫 줄 `> 요약:`만 읽어 충분하면 본문은 열지 않는다.

| 이런 질문이면 | 읽을 파일 | 담당 |
|---|---|---|
| 무엇을 왜 만드나, 담당자가 뭐라 했나 | problem-definition.md | 1 지휘 |
| 기능 범위, 핵심 흐름, 이번에 뺀 것 | prd.md | 1 지휘 |
| 기술 스택, 구조, 왜 그렇게 정했나 | adr.md | 1 지휘 |
| 이상한 입력, 예외, 경계값 | edge-cases.md | 1 지휘 |
| 느림, 알고리즘, 부하 기준 | optimization.md | 1 지휘 |
| 테스트 명령과 결과 수치 | test-report.md | 4 테스트 |
| 실행 방법, 계정, URL | manuals/ | 5 실행 |
| 지금 누가 무엇을 하나, 배정, 요청 | board/lead.md 다음 해당 창 board | 창별 |

## 규칙

- 문서를 고치면 첫 줄 `> 요약:`(3줄 이내)도 같이 고친다.
- 한 문서가 150줄을 넘거나 주제가 둘 이상이면 `docs/<주제>/` 아래로 나누고 이 표에 한 줄 추가한다.
- 새 문서는 이 표에 등록해야 존재한다. 등록하지 않은 문서는 만들지 않는다.
- 필요 없는 문서는 지우지 말고 요약 줄을 `> 요약: 생략, 이유`로 적는다.
"""
REPORT = "# 테스트 결과\n\n| 층 | 명령 | 결과 | 비고 |\n|---|---|---|---|\n| 단위 | | | |\n| 시나리오/E2E | | | |\n| 부하 | | | |\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ws = Path(ap.parse_args().workspace).resolve()
    created, kept = [], []
    for rel, src in LAYOUT.items():
        dst = ws / rel
        if dst.exists() or dst.is_symlink():
            kept.append(rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src is None:
            text = INDEX if rel.endswith("README.md") else REPORT
        else:
            text = (T / src).read_text(encoding="utf-8")
        if not rel.endswith("README.md"):
            text = "> 요약: (3줄 이내. 본문을 고치면 같이 고친다)\n\n" + text
        dst.write_text(text, encoding="utf-8")
        created.append(rel)
    print(json.dumps({"status": "ok", "created": created, "kept": kept}, ensure_ascii=False))

if __name__ == "__main__":
    main()
