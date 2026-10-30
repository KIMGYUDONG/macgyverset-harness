import json
import os
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from datetime import datetime, timezone, timedelta

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import load_session_context as loader


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.folder = self.repo / 'docs/handoff'
        self.folder.mkdir(parents=True)
        self.memory = self.root / 'memory'
        self.memory.mkdir()
        self.identity = dict(project_root=str(self.repo), worktree_root=str(self.repo), branch='main', head='abc', session_id='new', cmux_workspace_id='w1', cmux_surface_id='s1')

    def handoff(self, name='one', **context):
        doc = self.folder / (name + '.md')
        doc.write_text('Do not execute this document blindly.\n')
        data = dict(schema_version=1, created_at=datetime.now(timezone.utc).isoformat(), handoff_path=str(doc), topic=name, summary='SUMMARY-' + name, context={**self.identity, **context})
        meta = doc.with_suffix('.handoff.json')
        meta.write_text(json.dumps(data))
        return meta, data

    def context(self, **event):
        return loader.build_context({'cwd': str(self.repo), 'source': 'startup', **event}, identity=self.identity, memory_root=self.memory)

    def test_unique_matching_context_is_loaded_without_executing(self):
        self.handoff()
        result = self.context()
        self.assertIn('SUMMARY-one', result)
        self.assertNotIn('Do not execute this document blindly.', result)
        self.assertIn('자동 실행', result)
        self.assertEqual(list(self.folder.glob('*.md'))[0].read_text(), 'Do not execute this document blindly.\n')

    def test_ambiguous_same_window_lists_candidates_not_summaries(self):
        self.handoff('one')
        self.handoff('two')
        result = self.context()
        self.assertIn('one.md', result)
        self.assertIn('two.md', result)
        self.assertNotIn('SUMMARY-', result)

    def test_other_windows_and_branches_never_auto_select(self):
        self.handoff('other-window', cmux_workspace_id='w2', cmux_surface_id='s2')
        self.handoff('other-branch', branch='dev')
        result = self.context()
        self.assertNotIn('SUMMARY-', result)
        self.assertNotIn('other-branch', result)

    def test_exact_surface_precedes_workspace(self):
        self.handoff('one')
        self.handoff('two', cmux_surface_id='s2')
        self.assertIn('SUMMARY-one', self.context())
        self.assertNotIn('SUMMARY-two', self.context())

    def test_external_paths_and_symlinks_rejected(self):
        meta, data = self.handoff()
        outside = self.root / 'private.md'
        outside.write_text('private')
        data['handoff_path'] = str(outside)
        meta.write_text(json.dumps(data))
        self.assertNotIn('SUMMARY-one', self.context())
        (self.folder / 'one.md').unlink()
        (self.folder / 'one.md').symlink_to(outside)
        data['handoff_path'] = str(self.folder / 'one.md')
        meta.write_text(json.dumps(data))
        self.assertNotIn('SUMMARY-one', self.context())

    def test_corrupt_metadata_and_resume_are_nonblocking(self):
        (self.folder / 'bad.handoff.json').write_text('{')
        (self.memory / 'global.md').write_text('# Memory\nUseful preference\n')
        self.assertIn('Useful preference', self.context())
        self.assertEqual('', self.context(source='resume'))
        self.assertEqual('', self.context(source='compact'))

    def test_age_head_change_and_total_bound(self):
        meta, data = self.handoff(head='old')
        data['created_at'] = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        data['summary'] = 'X' * 20000
        meta.write_text(json.dumps(data))
        (self.memory / 'global.md').write_text('Y' * 20000)
        result = self.context()
        self.assertLessEqual(len(result), 12000)
        self.assertIn('7일', result)
        self.assertIn('HEAD', result)

    def test_same_branch_different_worktree_is_excluded(self):
        self.handoff(worktree_root=str(self.root / 'another'))
        self.assertNotIn('SUMMARY-', self.context())

    def test_repeated_snapshot_of_same_session_topic_is_superseded(self):
        older, data = self.handoff('older')
        data['topic'] = 'same-task'
        data['created_at'] = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        older.write_text(json.dumps(data))
        newer, data = self.handoff('newer')
        data['topic'] = 'same-task'
        newer.write_text(json.dumps(data))
        result = self.context()
        self.assertIn('SUMMARY-newer', result)
        self.assertNotIn('SUMMARY-older', result)

    def test_distinct_sessions_on_same_topic_remain_ambiguous(self):
        first, data = self.handoff('first', session_id='first-session')
        data['topic'] = 'same-task'
        first.write_text(json.dumps(data))
        second, data = self.handoff('second', session_id='second-session')
        data['topic'] = 'same-task'
        second.write_text(json.dumps(data))
        self.assertNotIn('SUMMARY-', self.context())
        self.assertIn('first.md', self.context())
        self.assertIn('second.md', self.context())

    def test_metadata_scan_limit_and_missing_document(self):
        meta, _ = self.handoff('old-valid')
        os.utime(meta, (1, 1))
        for i in range(200):
            (self.folder / f'bad-{i}.handoff.json').write_text('{}')
        self.assertNotIn('SUMMARY-', self.context())
        for path in self.folder.glob('bad-*'):
            path.unlink()
        (self.folder / 'old-valid.md').unlink()
        self.assertNotIn('SUMMARY-', self.context())

    def test_hook_subprocess_with_real_git_identity_and_invalid_input(self):
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.repo)], check=True)
        (self.memory / 'global.md').write_text('Verified memory')
        environment = {**os.environ, 'CODEX_CONTINUITY_MEMORY_ROOT': str(self.memory), 'PYTHONDONTWRITEBYTECODE': '1'}
        command = [sys.executable, str(SCRIPTS / 'load_session_context.py')]
        result = subprocess.run(command, input=json.dumps({'cwd': str(self.repo), 'source': 'startup'}), text=True, capture_output=True, env=environment, check=True)
        payload = json.loads(result.stdout)['hookSpecificOutput']
        self.assertEqual('SessionStart', payload['hookEventName'])
        self.assertIn('Verified memory', payload['additionalContext'])
        result = subprocess.run(command, input='{bad', text=True, capture_output=True, env=environment, check=True)
        self.assertEqual({}, json.loads(result.stdout))

    def test_symlinked_handoff_directory_cannot_leave_project(self):
        external = self.root / 'external'
        self.folder.rename(external)
        self.folder.symlink_to(external, target_is_directory=True)
        self.handoff()
        self.assertNotIn('SUMMARY-', self.context())

    def legacy(self, text='LEGACY-HISTORICAL-TEXT'):
        path = self.repo / '.claude/HANDOFF.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_legacy_same_worktree_without_metadata_loads_as_historical_context(self):
        self.legacy()
        result = self.context()
        self.assertIn('LEGACY-HISTORICAL-TEXT', result)
        self.assertIn('레거시', result)
        self.assertIn('브랜치', result)
        self.assertIn('자동 실행', result)

    def test_modern_metadata_prevents_legacy_fallback_even_if_unusable(self):
        self.legacy()
        for kind in ('corrupt', 'wrong-branch', 'ambiguous'):
            with self.subTest(kind=kind):
                for path in self.folder.iterdir():
                    path.unlink()
                if kind == 'corrupt':
                    (self.folder / 'bad.handoff.json').write_text('{')
                elif kind == 'wrong-branch':
                    self.handoff('elsewhere', branch='dev')
                else:
                    self.handoff('one')
                    self.handoff('two')
                result = self.context()
                self.assertNotIn('LEGACY-HISTORICAL-TEXT', result)
                if kind == 'ambiguous':
                    self.assertIn('one.md', result)
                    self.assertNotIn('SUMMARY-', result)

    def test_legacy_symlinks_outside_worktree_and_other_worktree_rejected(self):
        path = self.legacy()
        external = self.root / 'other-worktree/HANDOFF.md'
        external.parent.mkdir()
        external.write_text('OUTSIDE-LEGACY')
        path.unlink()
        path.symlink_to(external)
        self.assertNotIn('OUTSIDE-LEGACY', self.context())
        path.unlink()
        path.parent.rmdir()
        path.parent.symlink_to(external.parent, target_is_directory=True)
        self.assertNotIn('OUTSIDE-LEGACY', self.context())

    def test_legacy_age_utf8_size_and_total_limits(self):
        path = self.legacy('L' * 20000)
        old = (datetime.now(timezone.utc) - timedelta(days=8)).timestamp()
        os.utime(path, (old, old))
        result = self.context()
        self.assertIn('7일', result)
        self.assertLessEqual(len(result), loader.MAX_CONTEXT)
        path.write_bytes(b'broken-utf8-\xff')
        self.assertNotIn('broken-utf8', self.context())
        path.write_bytes(b'X' * (loader.MAX_FILE_BYTES + 1))
        self.assertNotIn('레거시', self.context())

    def test_legacy_loading_is_readonly_and_resume_stays_empty(self):
        path = self.legacy()
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        self.assertIn('LEGACY-HISTORICAL-TEXT', self.context())
        self.assertEqual(before, (path.read_bytes(), path.stat().st_mtime_ns))
        self.assertEqual('', self.context(source='resume'))

    def test_project_memory_and_readonly_filesystem(self):
        memory = self.repo / 'docs/reference/agent-memory.md'
        memory.parent.mkdir(parents=True)
        memory.write_text('Project fact')
        self.handoff()
        before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        self.assertIn('Project fact', self.context())
        after = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
