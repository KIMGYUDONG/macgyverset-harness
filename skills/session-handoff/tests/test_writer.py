import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/create_session_handoff.py'

class WriterTests(unittest.TestCase):
    def test_selected_handoff_preserves_digest_without_implicit_kickoff(self):
        with tempfile.TemporaryDirectory() as folder:
            digest = {'summary': '부분 완료', 'decisions': ['대안 A는 비용 때문에 제외'], 'in_progress': ['빌드 실패, 다음 확인 필요'], 'verification': ['pytest: 1 failed']}
            p = subprocess.run([sys.executable, str(SCRIPT), '--repo', folder, '--input', '-', '--artifacts', 'handoff'], input=json.dumps(digest), text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            files = list((Path(folder) / 'docs/handoff').glob('*.md'))
            self.assertEqual(len(files), 1)
            body = files[0].read_text()
            self.assertIn(digest['decisions'][0], body)
            self.assertIn(digest['in_progress'][0], body)
            self.assertIn('1 failed', body)
            meta = json.loads(files[0].with_suffix('.handoff.json').read_text())
            self.assertEqual(meta['handoff_path'], str(files[0].resolve()))
            self.assertEqual(meta['context']['worktree_root'], str(Path(folder).resolve()))


class WriterBoundaryTests(unittest.TestCase):
    def invoke(self, folder, artifacts, value=None, extra=()):
        return subprocess.run([sys.executable, str(SCRIPT), '--repo', folder, '--input', '-', '--artifacts', artifacts, *extra], input=json.dumps(value or {'summary': '근거와 실패를 보존'}), text=True, capture_output=True)

    def test_kickoff_only_is_self_contained_and_no_loader_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.invoke(folder, 'kickoff', {'summary': '설계 결정', 'decisions': ['REST 선택: 기존 팀 경험'], 'next_steps': ['URL 버전 검토']})
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertNotIn('handoff', data)
            self.assertEqual(data['clipboard'], 'not_requested')
            self.assertIn('REST 선택', Path(data['kickoff']).read_text())
            self.assertEqual(list(Path(folder).rglob('*.handoff.json')), [])

    def test_repeat_and_parallel_writes_do_not_overwrite(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as folder:
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda _: self.invoke(folder, 'handoff'), range(8)))
            paths = [json.loads(p.stdout)['handoff'] for p in results if p.returncode == 0]
            self.assertEqual(len(set(paths)), 8)
            self.assertTrue(all(Path(p).is_file() for p in paths))
            self.assertEqual(len(list(Path(folder).rglob('*.handoff.json'))), 8)

    def test_invalid_digest_does_not_create_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            for bad in [{'summary': ''}, {'summary': 'ok', 'unknown': ['do not lose me']}, {'summary': 'ok', 'completed': 'wrong type'}]:
                result = self.invoke(folder, 'handoff', bad)
                self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_copy_without_kickoff_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertNotEqual(self.invoke(folder, 'handoff', extra=['--copy']).returncode, 0)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_clipboard_failure_is_reported_honestly(self):
        from unittest.mock import patch
        sys.path.insert(0, str(SCRIPT.parent))
        import create_session_handoff as writer
        with tempfile.TemporaryDirectory() as folder, patch.object(writer.shutil, 'which', return_value=None):
            result = writer.write_artifacts(Path(folder).resolve(), writer.digest_from({'summary': '작성 완료'}), {'kickoff'}, copy=True)
            self.assertEqual(result['clipboard'], 'failed')
            self.assertTrue(Path(result['kickoff']).is_file())

    def test_context_separates_git_worktrees_and_non_git_parent(self):
        sys.path.insert(0, str(SCRIPT.parent))
        from context_identity import context_identity
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            main = root / 'main'
            main.mkdir()
            subprocess.run(['git', 'init', '-q', str(main)], check=True)
            subprocess.run(['git', '-C', str(main), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture'], check=True)
            other = root / 'other'
            subprocess.run(['git', '-C', str(main), 'worktree', 'add', '-qb', 'other', str(other)], check=True)
            left, right = context_identity(main), context_identity(other)
            self.assertEqual(left['project_root'], right['project_root'])
            self.assertNotEqual(left['worktree_root'], right['worktree_root'])
            self.assertNotEqual(left['branch'], right['branch'])
            project = root / 'plain'
            child = project / 'child'
            child.mkdir(parents=True)
            (project / 'AGENTS.md').write_text('# Project')
            self.assertEqual(context_identity(child)['worktree_root'], str(project))

if __name__ == '__main__':
    unittest.main()
