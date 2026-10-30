"""Stable local project, worktree and terminal identity shared by writer and loader."""
from pathlib import Path
import os
import subprocess


def git(cwd: Path, *args: str) -> str | None:
    try:
        p = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, timeout=5)
        return p.stdout.strip() or None if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def context_identity(cwd: Path) -> dict:
    cwd = cwd.expanduser().resolve()
    top = git(cwd, 'rev-parse', '--show-toplevel')
    worktree = Path(top).resolve() if top else cwd
    project = worktree
    if top:
        listing = git(cwd, 'worktree', 'list', '--porcelain')
        if listing and listing.startswith('worktree '):
            project = Path(listing.splitlines()[0][9:]).resolve()
    else:
        boundaries = {Path.home().resolve(), (Path.home() / 'code').resolve(), Path('/')}
        for candidate in (cwd, *cwd.parents):
            if candidate in boundaries:
                break
            if (candidate / 'AGENTS.md').is_file() or (candidate / 'AGENTS.override.md').is_file():
                project = worktree = candidate
                break
    return {'project_root': str(project), 'worktree_root': str(worktree),
            'branch': git(cwd, 'symbolic-ref', '--short', '-q', 'HEAD') if top else None,
            'head': git(cwd, 'rev-parse', '--verify', 'HEAD') if top else None,
            'session_id': os.environ.get('CODEX_THREAD_ID', ''),
            'cmux_workspace_id': os.environ.get('CMUX_WORKSPACE_ID', ''),
            'cmux_surface_id': os.environ.get('CMUX_SURFACE_ID', '')}
