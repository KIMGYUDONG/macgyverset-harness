#!/usr/bin/env python3
"""Download pinned official references without activating workspace skills."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.request import HTTPRedirectHandler, Request, build_opener

COMMIT = "2ce8aa15d05bd57213e6f746f953aafb7ded7a8b"
BASE_URL = "https://raw.githubusercontent.com/obra/superpowers/" + COMMIT + "/"
ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "official-skills.lock.json"
MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 4 * MAX_FILE_BYTES
TIMEOUT_SECONDS = 20
ALLOWED_PATHS = {
    "LICENSE",
    "skills/brainstorming/SKILL.md",
    "skills/brainstorming/builder-check-prompt.md",
    "skills/brainstorming/scripts/frame-template.html",
    "skills/brainstorming/scripts/helper.js",
    "skills/brainstorming/scripts/server.cjs",
    "skills/brainstorming/scripts/start-server.sh",
    "skills/brainstorming/scripts/stop-server.sh",
    "skills/brainstorming/visual-companion.md",
    "skills/test-driven-development/SKILL.md",
    "skills/test-driven-development/writing-good-tests.md",
}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


urlopen = build_opener(_NoRedirect()).open


def _plain_path(value):
    path = Path(value).expanduser().absolute()
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ValueError(f"Symlink paths are not allowed: {component}")
    return path.resolve()


def _load_lock(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if (not isinstance(data, dict)
            or set(data) != {"schema_version", "repository", "commit", "files"}
            or data["schema_version"] != 1
            or data["repository"] != "obra/superpowers" or data["commit"] != COMMIT
            or not isinstance(data["files"], list)):
        raise ValueError("Invalid official skills lock metadata")
    paths = []
    for entry in data["files"]:
        if (not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size"}
                or not isinstance(entry.get("path"), str)
                or entry["path"] not in ALLOWED_PATHS
                or not isinstance(entry.get("sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is None
                or type(entry.get("size")) is not int
                or not 0 <= entry["size"] <= MAX_FILE_BYTES):
            raise ValueError("Invalid official skills lock entry")
        paths.append(entry["path"])
    if set(paths) != ALLOWED_PATHS or len(paths) != len(ALLOWED_PATHS):
        raise ValueError("Lock must contain exactly the selected upstream files")
    if sum(entry["size"] for entry in data["files"]) > MAX_TOTAL_BYTES:
        raise ValueError("Official skills payload is too large")
    return data["files"]


def _matches(payload, entry):
    return (len(payload) == entry["size"]
            and hashlib.sha256(payload).hexdigest() == entry["sha256"])


def _preflight(output, entries):
    installed, unchanged = [], []
    for entry in entries:
        target = output / entry["path"]
        _plain_path(target)
        for parent in target.parents:
            if parent.exists() and not parent.is_dir():
                raise ValueError(f"Expected a directory: {parent}")
            if parent == output:
                break
        if target.exists():
            if (not target.is_file() or target.stat().st_size != entry["size"]
                    or not _matches(target.read_bytes(), entry)):
                raise ValueError(f"Existing file differs: {target}")
            unchanged.append(entry["path"])
        else:
            installed.append(entry["path"])
    return installed, unchanged


def fetch(output, lock_path=None):
    """Verify every response before creating any output files or directories."""
    entries = _load_lock(LOCK_PATH if lock_path is None else lock_path)
    output = _plain_path(output)
    if ".agents" in output.parts:
        raise ValueError("Official references must stay outside .agents")
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Official references must stay outside the kit checkout")
    if not output.parent.is_dir() or (output.exists() and not output.is_dir()):
        raise ValueError("Output must be a directory with an existing real parent")
    expected_installed, unchanged = _preflight(output, entries)
    payloads = {}
    for entry in entries:
        if entry["path"] not in expected_installed:
            continue
        request = Request(BASE_URL + entry["path"], headers={"User-Agent": "macgyverset-harness-official-fetch/1"})
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = response.read(entry["size"] + 1)
        if not _matches(payload, entry):
            raise ValueError(f"Size or SHA-256 mismatch: {entry['path']}")
        payloads[entry["path"]] = payload

    installed, unchanged = _preflight(output, entries)
    if installed != expected_installed:
        raise ValueError("Output changed during download; retry without overwriting files")
    missing_directories = set()
    for relative in installed:
        for parent in (output / relative).parents:
            if not parent.exists():
                missing_directories.add(parent)
            if parent == output:
                break
    for directory in sorted(missing_directories, key=lambda item: (len(item.parts), str(item))):
        directory.mkdir(exist_ok=False)
    for relative in installed:
        with (output / relative).open("xb") as stream:
            stream.write(payloads[relative])
    return {"status": "ok", "commit": COMMIT, "installed": installed, "unchanged": unchanged}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path,
                        help="Reference directory outside .agents and the kit checkout")
    args = parser.parse_args(argv)
    try:
        result = fetch(args.output)
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
