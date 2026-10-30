#!/usr/bin/env python3
"""Copy kit skills into an explicitly selected workspace without overwrites."""

import argparse
import json
from pathlib import Path
import sys


def _plain_path(value):
    path = Path(value).expanduser().absolute()
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ValueError(f"Symlink paths are not allowed: {component}")
    return path.resolve()


def _tree(path):
    """Capture regular files and directory names, rejecting all symlinks."""
    _plain_path(path)
    if not path.is_dir():
        raise ValueError(f"Expected a directory: {path}")
    entries = {}

    def visit(directory):
        for child in sorted(directory.iterdir()):
            relative = child.relative_to(path)
            if child.is_symlink():
                raise ValueError(f"Symlink entries are not allowed: {child}")
            if child.is_dir():
                entries[relative] = ("directory", None)
                visit(child)
            elif child.is_file():
                entries[relative] = ("file", child.read_bytes())
            else:
                raise ValueError(f"Unsupported entry: {child}")

    visit(path)
    return entries


def prepare(source, workspace, dry_run=False):
    """Preflight every destination before installing any new kit directory."""
    source = _plain_path(source)
    workspace = _plain_path(workspace)
    if not source.is_dir() or not workspace.is_dir():
        raise ValueError("Source and workspace must be existing real directories")
    source_skills = _plain_path(source / "skills")
    if not source_skills.is_dir():
        raise ValueError(f"Missing source skills directory: {source_skills}")
    sources = sorted(path for path in source_skills.iterdir()
                     if path.name.startswith("kit-")
                     or path.name in {"session-handoff", "macgyverset-harness"})
    if not sources:
        raise ValueError("No kit skills found")

    destination = workspace / ".agents" / "skills"
    missing_parents = []
    for directory in (destination.parent, destination):
        _plain_path(directory)
        if directory.exists():
            if not directory.is_dir():
                raise ValueError(f"Expected a directory: {directory}")
        else:
            missing_parents.append(directory)

    pending = []
    unchanged = []
    for skill in sources:
        manifest = _tree(skill)
        target = destination / skill.name
        _plain_path(target)
        if (target == source or source in target.parents
                or target in source.parents):
            raise ValueError("Target and source checkout must not overlap")
        if target.exists():
            if _tree(target) != manifest:
                raise ValueError(f"Existing skill differs: {target}")
            unchanged.append(skill.name)
        else:
            pending.append((target, manifest))

    if not dry_run and pending:
        for directory in missing_parents:
            directory.mkdir(exist_ok=False)
        for target, manifest in pending:
            target.mkdir(exist_ok=False)
            for relative, (kind, content) in manifest.items():
                path = target / relative
                if kind == "directory":
                    path.mkdir(exist_ok=False)
                else:
                    with path.open("xb") as stream:
                        stream.write(content)

    return {
        "status": "dry-run" if dry_run else "ok",
        "dry_run": dry_run,
        "installed": [target.name for target, _ in pending],
        "unchanged": unchanged,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = prepare(Path(__file__).resolve().parents[1], args.workspace, args.dry_run)
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
