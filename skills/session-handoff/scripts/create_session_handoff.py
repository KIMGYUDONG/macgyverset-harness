#!/usr/bin/env python3
"""Write selected continuation artifacts from a verified JSON session digest."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

from context_identity import context_identity, git

SECTIONS = {'completed': '완료', 'in_progress': '진행 중', 'blockers': '차단과 확인 필요',
            'next_steps': '다음 단계', 'key_files': '핵심 파일', 'decisions': '결정과 이유',
            'rejected_alternatives': '제외한 대안', 'lessons': '교훈',
            'verification': '검증', 'constraints': '제약과 보존할 작업'}


def clean(text: str) -> str:
    return text.replace('\u00b7', ',').replace('\u2013', '-').replace('\u2014', '-')


def digest_from(value: object) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get('summary'), str) or not value['summary'].strip():
        raise ValueError('digest.summary must be a nonempty string')
    if set(value) - {'summary', 'topic', *SECTIONS}:
        raise ValueError('Unknown digest fields: ' + ', '.join(sorted(set(value) - {'summary', 'topic', *SECTIONS})))
    result = {'summary': clean(value['summary'].strip()), 'topic': clean(value.get('topic', '세션 인계')) if isinstance(value.get('topic', ''), str) else None}
    if result['topic'] is None:
        raise ValueError('digest.topic must be a string')
    for key in SECTIONS:
        items = value.get(key, [])
        if not isinstance(items, list) or any(not isinstance(item, str) or not item.strip() for item in items):
            raise ValueError(f'digest.{key} must be a list of nonempty strings')
        result[key] = [clean(item.strip()) for item in items]
    return result


def render_digest(digest: dict) -> str:
    chunks = [digest['summary']]
    for key, label in SECTIONS.items():
        if digest[key]:
            chunks.append('## ' + label + '\n\n' + '\n'.join('- ' + item.replace('\n', '\n  ') for item in digest[key]))
    if not digest['verification']:
        chunks.append('## 검증\n\n검증 결과가 제공되지 않았습니다.')
    return '\n\n'.join(chunks)


def atomic_new(path: Path, body: str) -> None:
    """Publish a fully written file without ever replacing an existing path."""
    fd, name = tempfile.mkstemp(prefix='.handoff-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(name, path)
    finally:
        os.unlink(name)


def copy_clipboard(body: str) -> bool:
    for command in [['pbcopy'], ['xclip', '-selection', 'clipboard'], ['xsel', '-ib'], ['clip']]:
        if shutil.which(command[0]):
            try:
                if subprocess.run(command, input=body, text=True, capture_output=True, timeout=5).returncode == 0:
                    return True
            except (OSError, subprocess.TimeoutExpired):
                pass
    return False


def write_artifacts(repo: Path, digest: dict, selections: set[str], output_dir: Path | None = None, copy: bool = False) -> dict:
    if not repo.is_dir():
        raise ValueError(f'Working directory does not exist: {repo}')
    if not selections or selections - {'handoff', 'kickoff'}:
        raise ValueError('Select handoff and/or kickoff explicitly')
    if copy and 'kickoff' not in selections:
        raise ValueError('--copy requires kickoff')
    context = context_identity(repo)
    output_dir = output_dir or Path(context['worktree_root']) / 'docs/handoff'
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone()
    stamp = now.strftime('%Y-%m-%d-%H%M%S-%f') + '-' + uuid.uuid4().hex[:12]
    topic = re.sub(r'[^\w-]+', '-', digest['topic']).strip('-')[:60] or 'session'
    base = output_dir / f'{stamp}-{topic}'
    handoff = base.with_name(base.name + '-session-handoff.md')
    kickoff = base.with_name(base.name + '-kickoff-prompt.md')
    snapshot = f"작성 시각: {now.isoformat()}\n작업 폴더: `{context['worktree_root']}`\n브랜치: `{context['branch'] or '없음'}`\nHEAD: `{context['head'] or '없음'}`"
    status = git(repo, 'status', '--short', '--branch')
    body = f"# 세션 인계 - {digest['topic']}\n\n{snapshot}\n\n{render_digest(digest)}\n"
    if status:
        body += '\n## 작성 당시 로컬 Git 상태\n\n' + '\n'.join('    ' + clean(line) for line in status.splitlines()) + '\n'
    result = {'context': context, 'clipboard': 'not_requested'}
    if 'handoff' in selections:
        atomic_new(handoff, body)
        metadata = {'schema_version': 1, 'created_at': now.isoformat(), 'handoff_path': str(handoff),
                    'summary': digest['summary'], 'topic': digest['topic'], 'context': context}
        # Metadata is published last, so the loader never sees an incomplete Markdown file.
        try:
            atomic_new(handoff.with_suffix('.handoff.json'), json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
        except Exception:
            handoff.unlink()
            raise
        result['handoff'] = str(handoff)
    if 'kickoff' in selections:
        prompt = f"작업 디렉터리는 `{context['worktree_root']}`입니다.\n\n{snapshot}\n\n{render_digest(digest)}\n\n"
        if 'handoff' in selections:
            prompt += f'전체 인계: `{handoff}`\n\n'
        prompt += '적용되는 AGENTS.md와 현재 파일 상태를 먼저 확인하세요. 위 기록은 작성 당시의 상태이며 최신 사용자 지시가 우선합니다. 기존 사용자 변경을 보존하고, 다음 단계가 명시되어 있으면 그 범위에서 진행하세요. 다음 단계가 없으면 새 작업을 추측하지 마세요.\n'
        atomic_new(kickoff, prompt)
        result['kickoff'] = str(kickoff)
        if copy:
            result['clipboard'] = 'copied' if copy_clipboard(prompt) else 'failed'
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default=os.getcwd())
    parser.add_argument('--input', help='JSON digest path, or - for stdin')
    parser.add_argument('--artifacts', required=True, help='handoff,kickoff or either alone')
    parser.add_argument('--summary', default='', help='Legacy compact digest input; do not combine with --input')
    parser.add_argument('--next-focus', default='')
    parser.add_argument('--output-dir', default='')
    parser.add_argument('--copy', action='store_true', help='Copy the selected kickoff prompt to clipboard')
    args = parser.parse_args()
    try:
        if args.input and (args.summary or args.next_focus):
            raise ValueError('--input cannot be combined with --summary or --next-focus')
        if args.input:
            raw = sys.stdin.read() if args.input == '-' else Path(args.input).expanduser().read_text(encoding='utf-8')
            value = json.loads(raw)
        else:
            value = {'summary': args.summary, 'next_steps': [args.next_focus] if args.next_focus else []}
        digest = digest_from(value)
        result = write_artifacts(Path(args.repo).expanduser().resolve(), digest,
                                 set(args.artifacts.split(',')),
                                 Path(args.output_dir).expanduser().resolve() if args.output_dir else None, args.copy)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
