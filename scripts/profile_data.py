#!/usr/bin/env python3
"""Profile a CSV/TSV/XLSX table with the standard library only."""

import argparse
import csv
from collections import Counter
from datetime import datetime
import io
import json
from pathlib import Path
import re
import sys

MISSING = {"", "na", "n/a", "nan", "null", "none"}
DATE = re.compile(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})")
DATETIME = re.compile(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?")
TIME = re.compile(r"(\d{1,2}):(\d{2})(?::(\d{2}))?")
INT = re.compile(r"[+-]?\d+")


def read_text(path):
    raw = Path(path).read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp949")


def read_rows(path, delimiter=None, sheet=None):
    if Path(path).suffix.lower() in (".xlsx", ".xlsm"):
        try:
            import openpyxl
        except ImportError:
            raise ImportError("openpyxl 모듈이 없어 XLSX를 읽을 수 없습니다. CSV로 저장해 다시 실행하세요.")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb[sheet] if sheet else wb.worksheets[0]
        return [["" if v is None else v.isoformat(sep=" ") if isinstance(v, datetime) else str(v)
                 for v in row] for row in ws.iter_rows(values_only=True)]
    text = read_text(path)
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(text[:65536], delimiters=",\t;|").delimiter
        except csv.Error:
            delimiter = ","
    return list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))


def classify(v):
    """Return (type, normalized value) for a stripped non-missing value."""
    if v.lower() in ("true", "false"):
        return "bool", v.lower()
    if INT.fullmatch(v):
        return "int", int(v)
    m = DATETIME.fullmatch(v)
    if m:
        y, mo, d, h, mi, s = (int(x or 0) for x in m.groups())
        return "datetime", f"{y:04d}-{mo:02d}-{d:02d} {h:02d}:{mi:02d}:{s:02d}"
    m = DATE.fullmatch(v)
    if m:
        y, mo, d = map(int, m.groups())
        return "date", f"{y:04d}-{mo:02d}-{d:02d}"
    m = TIME.fullmatch(v)
    if m:
        h, mi, s = (int(x or 0) for x in m.groups())
        return "time", f"{h:02d}:{mi:02d}:{s:02d}"
    try:
        f = float(v)
        if f == f and abs(f) != float("inf") and v.lower() not in ("nan", "inf", "infinity"):
            return "float", f
    except ValueError:
        pass
    return "text", v


def profile_rows(rows, top=5):
    header, body = rows[0], rows[1:]
    width = len(header)
    body = [r + [""] * (width - len(r)) for r in body]
    seen, dup = set(), 0
    for r in body:
        key = tuple(r)
        dup += key in seen
        seen.add(key)
    columns, warnings = [], []
    if dup:
        warnings.append(f"중복 행 {dup}개")
    for i, name in enumerate(header):
        raw = [r[i] for r in body]
        padded = sum(v != v.strip() for v in raw if v.strip())
        vals = [v.strip() for v in raw if v.strip().lower() not in MISSING]
        missing = len(raw) - len(vals)
        kinds = [classify(v) for v in vals]
        counts = Counter(k for k, _ in kinds)
        if set(counts) == {"int", "float"}:
            counts = Counter({"float": len(kinds)})
            kinds = [("float", float(n)) for _, n in kinds]
        kind = counts.most_common(1)[0][0] if counts else "text"
        col = {"name": name, "missing": missing, "distinct": len(set(vals)), "type": kind,
               "top": [[v, c] for v, c in Counter(vals).most_common(top)]}
        if kind in ("int", "float", "date", "datetime", "time"):
            nums = [n for k, n in kinds if k == kind or (kind == "float" and k == "int")]
            if nums:
                col["min"], col["max"] = min(nums), max(nums)
        if kind in ("int", "float") and col.get("min", 0) < 0:
            warnings.append(f"{name}: 음수 값 있음 (최소 {col['min']})")
        if missing:
            warnings.append(f"{name}: 결측 {missing}개")
        if len(counts) > 1:
            warnings.append(f"{name}: 타입 혼합 " + ", ".join(f"{k} {c}" for k, c in counts.most_common()))
        if padded:
            warnings.append(f"{name}: 앞뒤 공백 값 {padded}개")
        columns.append(col)
    return {"rows": len(body), "column_count": width, "duplicate_rows": dup,
            "columns": columns, "warnings": warnings}


def render(result):
    lines = [f"행: {result['rows']}", f"열: {result['column_count']}",
             f"중복 행: {result['duplicate_rows']}", ""]
    for c in result["columns"]:
        line = f"[{c['name']}] 타입 {c['type']}, 결측 {c['missing']}, 고유값 {c['distinct']}"
        if "min" in c:
            line += f", 최소 {c['min']}, 최대 {c['max']}"
        lines.append(line)
        lines.append("  상위: " + ", ".join(f"{v} ({n})" for v, n in c["top"]))
    lines += ["", "주의:"] + (["  - " + w for w in result["warnings"]] or ["  없음"])
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--delimiter")
    ap.add_argument("--sheet")
    args = ap.parse_args(argv)
    try:
        rows = read_rows(args.path, args.delimiter, args.sheet)
    except ImportError as e:
        print(e, file=sys.stderr)
        return 2
    except Exception as e:
        print(f"읽기 실패: {e}", file=sys.stderr)
        return 1
    if not rows:
        print("읽기 실패: 빈 파일", file=sys.stderr)
        return 1
    result = profile_rows(rows, args.top)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
