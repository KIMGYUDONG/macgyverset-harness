import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/profile_data.py"


class ProfileDataTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.dir = Path(t.name)

    def write(self, name, text, encoding="utf-8"):
        p = self.dir / name
        p.write_bytes(text.encode(encoding))
        return p

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True)

    def profile(self, path, *extra):
        r = self.run_cli(path, "--json", *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def col(self, data, name):
        return next(c for c in data["columns"] if c["name"] == name)

    def test_missing_and_duplicates(self):
        p = self.write("a.csv", "id,name\n1,a\n1,a\n2,\n3,NA\n4, \n5,null\n")
        d = self.profile(p)
        self.assertEqual(d["rows"], 6)
        self.assertEqual(d["duplicate_rows"], 1)
        self.assertEqual(self.col(d, "name")["missing"], 4)
        self.assertEqual(self.col(d, "id")["missing"], 0)

    def test_numeric_types_and_negative(self):
        p = self.write("n.csv", "i,f\n1,1.5\n-2,2.5\n3,x\n4,4.5\n")
        d = self.profile(p)
        i = self.col(d, "i")
        self.assertEqual((i["type"], i["min"], i["max"]), ("int", -2, 4))
        self.assertTrue(any("음수" in w and "i" in w for w in d["warnings"]))
        self.assertEqual(self.col(d, "f")["type"], "float")
        self.assertTrue(any("혼합" in w and "f" in w for w in d["warnings"]))

    def test_dates_mixed_formats(self):
        p = self.write("d.csv", "d,dt,t\n2024-01-05,2024-01-05 10:00:00,09:30\n"
                       "2024/02/01,2024-02-01T11:00:00,10:15\n2023.12.31,2024-03-01 00:00:00,23:59\n")
        d = self.profile(p)
        c = self.col(d, "d")
        self.assertEqual((c["type"], c["min"], c["max"]), ("date", "2023-12-31", "2024-02-01"))
        self.assertEqual(self.col(d, "dt")["type"], "datetime")
        self.assertEqual(self.col(d, "t")["type"], "time")

    def test_bool_top_and_whitespace(self):
        p = self.write("b.csv", "f,s\ntrue,a\nfalse,a\ntrue, b\ntrue,a\n")
        d = self.profile(p, "--top", 1)
        self.assertEqual(self.col(d, "f")["type"], "bool")
        self.assertEqual(self.col(d, "s")["top"], [["a", 3]])
        self.assertEqual(self.col(d, "s")["distinct"], 2)
        self.assertTrue(any("공백" in w for w in d["warnings"]))

    def test_cp949(self):
        p = self.write("k.csv", "이름,나이\n홍길동,30\n김철수,40\n", "cp949")
        d = self.profile(p)
        self.assertEqual([c["name"] for c in d["columns"]], ["이름", "나이"])
        self.assertEqual(self.col(d, "나이")["max"], 40)

    def test_bom_and_tsv_sniff(self):
        p = self.write("t.tsv", "﻿a\tb\n1\tx,y\n2\tz\n")
        d = self.profile(p)
        self.assertEqual([c["name"] for c in d["columns"]], ["a", "b"])
        d = self.profile(p, "--delimiter", "\t")
        self.assertEqual(d["rows"], 2)

    def test_human_output_korean(self):
        p = self.write("h.csv", "a\n1\n")
        r = self.run_cli(p)
        self.assertEqual(r.returncode, 0)
        self.assertIn("행", r.stdout)
        self.assertIn("결측", r.stdout)

    def test_missing_file_exit_1(self):
        r = self.run_cli(self.dir / "none.csv")
        self.assertEqual(r.returncode, 1)

    def test_xlsx_without_openpyxl_or_with(self):
        p = self.dir / "x.xlsx"
        p.write_bytes(b"not a workbook")
        r = self.run_cli(p)
        self.assertIn(r.returncode, (1, 2))


if __name__ == "__main__":
    unittest.main()
