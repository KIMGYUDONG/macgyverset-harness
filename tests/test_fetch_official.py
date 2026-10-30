import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "fetch_official", Path(__file__).resolve().parents[1] / "scripts/fetch_official.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

PIN = "2ce8aa15d05bd57213e6f746f953aafb7ded7a8b"
REPO_LOCK = Path(__file__).resolve().parents[1] / "official-skills.lock.json"


class FetchOfficialTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "workspace with spaces" / "harness-official"
        self.output.parent.mkdir()
        self.data = json.loads(REPO_LOCK.read_text())
        self.payloads = {entry["path"]: ("fixture:" + entry["path"]).encode()
                         for entry in self.data["files"]}
        for entry in self.data["files"]:
            payload = self.payloads[entry["path"]]
            entry.update(size=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        self.lock = self.root / "lock.json"
        self.write_lock()

    def write_lock(self):
        self.lock.write_text(json.dumps(self.data))

    def response(self, request, timeout):
        url = request.full_url
        prefix = "https://raw.githubusercontent.com/obra/superpowers/" + PIN + "/"
        self.assertTrue(url.startswith(prefix))
        self.assertGreater(timeout, 0)
        return io.BytesIO(self.payloads[url[len(prefix):]])

    def run_fetch(self, response=None):
        with mock.patch.object(module, "urlopen", side_effect=response or self.response):
            return module.fetch(self.output, self.lock)

    def test_fetches_original_bytes_and_is_idempotent(self):
        result = self.run_fetch()
        self.assertEqual(len(result["installed"]), 11)
        for relative, payload in self.payloads.items():
            self.assertEqual((self.output / relative).read_bytes(), payload)
        unrelated = self.output / "existing.txt"
        unrelated.write_text("keep")
        with mock.patch.object(module, "urlopen", side_effect=AssertionError("cache must stay offline")):
            result = module.fetch(self.output, self.lock)
        self.assertEqual(result["installed"], [])
        self.assertEqual(len(result["unchanged"]), 11)
        self.assertEqual(unrelated.read_text(), "keep")
        self.assertFalse((self.output.parent / ".agents").exists())

    def test_partial_cache_fetches_only_the_missing_file(self):
        self.run_fetch()
        relative = self.data["files"][0]["path"]
        (self.output / relative).unlink()
        with mock.patch.object(module, "urlopen", side_effect=self.response) as download:
            result = module.fetch(self.output, self.lock)
        self.assertEqual(result["installed"], [relative])
        self.assertEqual(len(result["unchanged"]), 10)
        self.assertEqual(download.call_count, 1)

    def test_hash_mismatch_leaves_output_absent(self):
        last = self.data["files"][-1]["path"]
        original = self.payloads[last]
        self.payloads[last] = bytes([original[0] ^ 1]) + original[1:]
        with self.assertRaises(ValueError):
            self.run_fetch()
        self.assertFalse(self.output.exists())

    def test_network_failure_leaves_output_absent(self):
        def failing(request, timeout):
            if request.full_url.endswith(self.data["files"][-1]["path"]):
                raise OSError("offline")
            return self.response(request, timeout)
        with self.assertRaises(OSError):
            self.run_fetch(failing)
        self.assertFalse(self.output.exists())

    def test_oversized_response_leaves_no_files(self):
        first = self.data["files"][0]["path"]
        self.payloads[first] += b"extra"
        with self.assertRaises(ValueError):
            self.run_fetch()
        self.assertFalse(self.output.exists())

    def test_collision_preflight_preserves_every_existing_file(self):
        relative = self.data["files"][-1]["path"]
        path = self.output / relative
        path.parent.mkdir(parents=True)
        path.write_bytes(b"user content")
        with self.assertRaises(ValueError):
            self.run_fetch()
        self.assertEqual(path.read_bytes(), b"user content")
        self.assertEqual([p for p in self.output.rglob("*") if p.is_file()], [path])

    def test_lock_cannot_change_origin_pin_or_paths(self):
        original = copy.deepcopy(self.data)
        cases = [lambda x: x.update(repository="attacker/other"),
                 lambda x: x.update(commit="0" * 40),
                 lambda x: x["files"][0].update(path="../escape"),
                 lambda x: x["files"][0].update(path="/absolute"),
                 lambda x: x["files"][0].update(path="https://example.invalid/file"),
                 lambda x: x["files"][0].update(path="skills/brainstorming/../../escape"),
                 lambda x: x["files"][0].update(url="https://example.invalid/file"),
                 lambda x: x["files"][0].update(size=2**30),
                 lambda x: x["files"].append(copy.deepcopy(x["files"][0]))]
        for change in cases:
            self.data = copy.deepcopy(original)
            change(self.data)
            self.write_lock()
            with self.subTest(lock=self.data), self.assertRaises(ValueError):
                self.run_fetch()
            self.assertFalse(self.output.exists())

    def test_symlink_output_ancestor_and_nested_target_are_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        for location in (self.output, self.output.parent / "link"):
            location.symlink_to(outside, target_is_directory=True)
            target = location if location == self.output else location / "target"
            with mock.patch.object(module, "urlopen", side_effect=self.response):
                with self.assertRaises(ValueError):
                    module.fetch(target, self.lock)
            location.unlink()
        self.output.mkdir()
        (self.output / "skills").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_fetch()
        self.assertEqual(list(outside.iterdir()), [])

    def test_autodiscovered_agents_output_is_rejected(self):
        self.output = self.root / ".agents" / "skills"
        with self.assertRaises(ValueError):
            self.run_fetch()
        self.assertFalse((self.root / ".agents").exists())

    def test_missing_parent_and_file_output_are_rejected(self):
        for path in (self.root / "missing" / "output", self.root / "file"):
            if path.name == "file":
                path.write_text("keep")
            with mock.patch.object(module, "urlopen", side_effect=self.response):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    module.fetch(path, self.lock)


if __name__ == "__main__":
    unittest.main()
