import importlib.util
import contextlib
import io
import json
import shutil
from pathlib import Path
import tempfile
import unittest
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "prepare.py"
spec = importlib.util.spec_from_file_location("kit_prepare", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / "source checkout"
        self.workspace = self.base / "exam workspace"
        self.workspace.mkdir()
        self.skills = self.source / "skills"
        self.skills.mkdir(parents=True)
        for name in ("kit-alpha", "kit-zeta"):
            skill = self.skills / name
            (skill / "references").mkdir(parents=True)
            (skill / "SKILL.md").write_text(name + "\n")
            (skill / "references" / "notes.txt").write_bytes(b"fixture\x00content")
        self.targets = self.workspace / ".agents" / "skills"

    def snapshot(self, root):
        return {str(p.relative_to(root)): ("link", str(p.readlink())) if p.is_symlink()
                else ("dir",) if p.is_dir() else ("file", p.read_bytes())
                for p in root.rglob("*")}

    def test_copy_and_idempotence_preserve_unrelated_content(self):
        for filename in ("AGENTS.md", "config.toml", "solution.py"):
            (self.workspace / filename).write_text("existing " + filename)
        other = self.targets / "user-skill"
        other.mkdir(parents=True)
        (other / "SKILL.md").write_text("user skill")
        original = self.snapshot(self.workspace)
        result = module.prepare(self.source, self.workspace)
        self.assertEqual(result["installed"], ["kit-alpha", "kit-zeta"])
        self.assertEqual(result["unchanged"], [])
        for name in result["installed"]:
            self.assertEqual(self.snapshot(self.skills / name), self.snapshot(self.targets / name))
        for path, content in original.items():
            self.assertEqual(self.snapshot(self.workspace)[path], content)
        before = self.snapshot(self.workspace)
        result = module.prepare(self.source, self.workspace)
        self.assertEqual(result["installed"], [])
        self.assertEqual(result["unchanged"], ["kit-alpha", "kit-zeta"])
        self.assertEqual(before, self.snapshot(self.workspace))

    def test_named_entries_and_kit_skills_are_included_but_unrelated_dirs_are_ignored(self):
        for name in ("macgyverset-harness", "session-handoff", "unrelated-skill"):
            skill = self.skills / name
            skill.mkdir()
            (skill / "SKILL.md").write_text(name)
        result = module.prepare(self.source, self.workspace)
        self.assertEqual(result["installed"],
                         ["kit-alpha", "kit-zeta", "macgyverset-harness", "session-handoff"])
        self.assertTrue((self.targets / "macgyverset-harness/SKILL.md").is_file())
        self.assertTrue((self.targets / "session-handoff/SKILL.md").is_file())
        self.assertFalse((self.targets / "unrelated-skill").exists())
        repeated = module.prepare(self.source, self.workspace)
        self.assertEqual(repeated["installed"], [])
        self.assertEqual(repeated["unchanged"], result["installed"])

    def test_collision_preflight_prevents_any_new_skill(self):
        target = self.targets / "kit-zeta"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("different")
        before = self.snapshot(self.workspace)
        with self.assertRaises(ValueError):
            module.prepare(self.source, self.workspace)
        self.assertEqual(before, self.snapshot(self.workspace))

    def test_extra_file_or_empty_directory_is_a_collision(self):
        module.prepare(self.source, self.workspace)
        for extra in ("extra.txt", "empty"):
            with self.subTest(extra=extra):
                path = self.targets / "kit-zeta" / extra
                if extra == "empty":
                    path.mkdir()
                else:
                    path.write_text("extra")
                before = self.snapshot(self.workspace)
                with self.assertRaises(ValueError):
                    module.prepare(self.source, self.workspace)
                self.assertEqual(before, self.snapshot(self.workspace))
                path.rmdir() if path.is_dir() else path.unlink()

    def test_dry_run_does_not_create_agents(self):
        before = self.snapshot(self.workspace)
        result = module.prepare(self.source, self.workspace, dry_run=True)
        self.assertEqual(result["installed"], ["kit-alpha", "kit-zeta"])
        self.assertTrue(result["dry_run"])
        self.assertEqual(before, self.snapshot(self.workspace))

    def test_workspace_must_exist_and_be_a_directory(self):
        for workspace in (self.base / "missing", self.workspace / "file"):
            if workspace.name == "file":
                workspace.write_text("file")
            with self.subTest(workspace=workspace), self.assertRaises(ValueError):
                module.prepare(self.source, workspace)

    def test_source_and_workspace_cannot_overlap(self):
        for workspace in (self.source, self.skills):
            with self.subTest(workspace=workspace), self.assertRaises(ValueError):
                module.prepare(self.source, workspace)

    def test_symlink_destination_and_ancestor_are_rejected(self):
        for relative in (".agents", ".agents/skills", ".agents/skills/kit-alpha"):
            with self.subTest(relative=relative):
                path = self.workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(self.source, target_is_directory=True)
                before = self.snapshot(self.workspace)
                try:
                    with self.assertRaises(ValueError):
                        module.prepare(self.source, self.workspace)
                    self.assertEqual(before, self.snapshot(self.workspace))
                finally:
                    path.unlink()
        link = self.base / "workspace-link"
        link.symlink_to(self.workspace, target_is_directory=True)
        with self.assertRaises(ValueError):
            module.prepare(self.source, link)
        ancestor = self.base / "ancestor"
        ancestor.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(ValueError):
            module.prepare(self.source, ancestor / self.workspace.name)

    def test_internal_symlink_is_rejected_even_when_it_stays_inside(self):
        module.prepare(self.source, self.workspace)
        path = self.targets / "kit-alpha" / "references" / "alias"
        path.symlink_to(path.parent / "notes.txt")
        with self.assertRaises(ValueError):
            module.prepare(self.source, self.workspace)

    def test_source_symlink_files_and_directories_are_rejected(self):
        cases = ((self.skills / "kit-alpha" / "alias", self.skills / "kit-alpha" / "SKILL.md"),
                 (self.skills / "kit-alpha" / "linked-dir", self.skills / "kit-alpha" / "references"),
                 (self.skills / "kit-link", self.skills / "kit-alpha"),
                 (self.skills / "kit-alpha" / "outside", self.workspace))
        for link, target in cases:
            with self.subTest(link=link):
                link.symlink_to(target, target_is_directory=target.is_dir())
                with self.assertRaises(ValueError):
                    module.prepare(self.source, self.workspace)
                self.assertFalse((self.workspace / ".agents").exists())
                link.unlink()

    def test_workspace_can_contain_a_separate_source_checkout(self):
        result = module.prepare(self.source, self.base)
        self.assertEqual(result["installed"], ["kit-alpha", "kit-zeta"])
        self.assertTrue((self.base / ".agents/skills/kit-alpha/SKILL.md").is_file())

    def test_source_root_and_skills_directory_symlinks_are_rejected(self):
        link = self.base / "source-link"
        link.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError):
            module.prepare(link, self.workspace)
        self.skills.rename(self.source / "actual-skills")
        self.skills.symlink_to(self.source / "actual-skills", target_is_directory=True)
        with self.assertRaises(ValueError):
            module.prepare(self.source, self.workspace)
        self.assertFalse((self.workspace / ".agents").exists())

    def test_destination_race_is_detected_without_overwrite(self):
        original_mkdir = Path.mkdir
        target = self.targets / "kit-alpha"

        def competing_mkdir(path, *args, **kwargs):
            if path == target:
                original_mkdir(path)
                (path / "user.txt").write_text("racing writer")
            return original_mkdir(path, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", competing_mkdir):
            with self.assertRaises(FileExistsError):
                module.prepare(self.source, self.workspace)
        self.assertEqual((target / "user.txt").read_text(), "racing writer")
        self.assertFalse((target / "SKILL.md").exists())
        self.assertFalse((self.targets / "kit-zeta").exists())

    def test_cli_outputs_json_without_fixture_dependencies(self):
        output = io.StringIO()
        with mock.patch.object(module, "__file__", str(self.source / "scripts/prepare.py")):
            with contextlib.redirect_stdout(output):
                code = module.main(["--workspace", str(self.workspace), "--dry-run"])
        self.assertEqual(code, 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "dry-run")
        self.assertEqual(result["installed"], ["kit-alpha", "kit-zeta"])
        self.assertFalse((self.workspace / ".agents").exists())

    def test_cli_installs_checkout_nested_in_workspace(self):
        checkout = self.workspace / "harness-kit"
        shutil.copytree(self.source, checkout)
        output = io.StringIO()
        with mock.patch.object(module, "__file__", str(checkout / "scripts/prepare.py")):
            with contextlib.redirect_stdout(output):
                code = module.main(["--workspace", str(self.workspace)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["installed"], ["kit-alpha", "kit-zeta"])
        for name in ("kit-alpha", "kit-zeta"):
            self.assertEqual(self.snapshot(checkout / "skills" / name),
                             self.snapshot(self.targets / name))

    def test_non_directory_namespace_ancestor_is_rejected(self):
        (self.workspace / ".agents").write_text("user file")
        with self.assertRaises(ValueError):
            module.prepare(self.source, self.workspace)
        self.assertEqual((self.workspace / ".agents").read_text(), "user file")


if __name__ == "__main__":
    unittest.main()
