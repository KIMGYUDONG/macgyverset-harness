#!/usr/bin/env python3
"""Check portable skill metadata, local references and publication hygiene."""

import re
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    errors = []
    expected = {f"kit-{name}" for name in ("plan", "code", "tdd", "verify", "finish", "write", "files",
                                                    "define", "data", "debug", "test", "manual")}
    expected.update({"session-handoff", "macgyverset-harness"})
    skills = list((root / "skills").glob("*/SKILL.md"))
    if {p.parent.name for p in skills} != expected:
        errors.append("Expected twelve kit skills, session-handoff and macgyverset-harness")
    for path in sorted(root.rglob("*")):
        if any(part in {".git", "__pycache__"} for part in path.relative_to(root).parts):
            continue
        if path.is_symlink():
            errors.append(f"Symlink in distribution: {path.relative_to(root)}")
            continue
        if not path.is_file() or path.suffix not in {".md", ".py"}:
            continue
        content = path.read_text(encoding="utf-8")
        if any(chr(c) in content for c in (0x00B7, 0x2013, 0x2014)):
            errors.append(f"Forbidden punctuation: {path.relative_to(root)}")
        # Construct sensitive prefixes so this scanner itself stays portable.
        forbidden = ("/" + "Users/", "/" + "home/", "sk-" + "proj-")
        if any(token in content for token in forbidden) or re.search(r"cand_[a-z0-9]{8,}", content):
            errors.append(f"Private path or credential-shaped content: {path.relative_to(root)}")
        if path.name == "SKILL.md":
            match = re.match(r"---\nname: ([a-z0-9-]+)\ndescription: ([^\n]+)\n---\n", content)
            if not match or match[1] != path.parent.name:
                errors.append(f"Invalid skill metadata: {path.relative_to(root)}")
        if path.suffix == ".md":
            for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", content):
                if target.startswith(("https://", "http://", "#")):
                    continue
                linked = (path.parent / target.split("#", 1)[0]).resolve()
                if not linked.is_relative_to(root) or not linked.exists():
                    errors.append(f"Broken local reference: {path.relative_to(root)} -> {target}")
    for error in errors:
        print(error)
    if errors:
        return 1
    print(f"PASS: {len(skills)} skills, local references and basic publication hygiene")
    print("This heuristic check does not certify absence of secrets or runtime correctness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
