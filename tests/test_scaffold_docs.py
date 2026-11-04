import json, subprocess, sys, tempfile, unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scaffold_docs.py"

def run(ws):
    r = subprocess.run([sys.executable, str(SCRIPT), "--workspace", str(ws)], capture_output=True, text=True)
    return r.returncode, json.loads(r.stdout)

class ScaffoldTest(unittest.TestCase):
    def test_creates_structure_and_keeps_existing(self):
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d)
            (ws / "docs").mkdir()
            (ws / "docs/prd.md").write_text("mine")
            code, out = run(ws)
            self.assertEqual(code, 0)
            for rel in ["docs/board/lead.md", "docs/board/test.md", "docs/adr.md",
                        "docs/edge-cases.md", "docs/manuals/admin.md", "docs/README.md"]:
                self.assertTrue((ws / rel).is_file(), rel)
            self.assertEqual((ws / "docs/prd.md").read_text(), "mine")
            self.assertIn("docs/prd.md", out["kept"])
            code, out2 = run(ws)
            self.assertEqual(out2["created"], [])

if __name__ == "__main__":
    unittest.main()
