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

INDEX = """# 개발 문서

| 파일 | 담당 | 내용 |
|---|---|---|
| problem-definition.md | 1 지휘 | 문제 정의, 담당자 질문과 답 |
| prd.md | 1 지휘 | 요구사항, 핵심 흐름, 범위 밖 |
| adr.md | 1 지휘 | 기술 스택과 주요 결정 |
| edge-cases.md | 1 지휘 | 경계 입력과 기대 동작 |
| optimization.md | 1 지휘 | 성능/알고리즘 판단 |
| test-report.md | 4 테스트 | 테스트 명령과 결과 수치 |
| manuals/ | 5 실행 | 관리자, 이용자, 심사 에이전트 매뉴얼 |
| board/ | 창별 | 진행 상태(자기 파일만 수정) |

필요 없는 문서는 지우지 말고 첫 줄에 `생략: 이유`를 적는다.
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
        dst.write_text(text, encoding="utf-8")
        created.append(rel)
    print(json.dumps({"status": "ok", "created": created, "kept": kept}, ensure_ascii=False))

if __name__ == "__main__":
    main()
