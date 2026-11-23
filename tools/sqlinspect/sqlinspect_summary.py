#!/usr/bin/env python3
"""Step 2.1: summarise one or more raw SQLInspect runs.

For each run directory (e.g. 02-access-analysis/sqlinspect-results/raw/base),
write one CSV with one line per query, then one markdown table comparing all
the runs.

Usage (from the repository root), with uv (recommended, uses pyproject.toml):
    uv run tools/sqlinspect/sqlinspect_summary.py            # every run in raw/
    uv run tools/sqlinspect/sqlinspect_summary.py \
        02-access-analysis/sqlinspect-results/raw/asset \
        02-access-analysis/sqlinspect-results/raw/base       # chosen runs

or with plain Python (3.9 or later):
    python3 tools/sqlinspect/sqlinspect_summary.py [run_dir ...]

Outputs (in --out, default 02-access-analysis/sqlinspect-results/filtered):
    <run>-queries.csv   run,id,file,line,class,method,exec_string,resolved,
                        operation,tables_in_scope,sql
    summary.md          comparison table of all the runs given

Only the Python standard library is used.

Author: Claude Opus 5.5 (AI-generated), 23.11.2026. Reviewed by the group.
"""

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # tools/sqlinspect/<this file> -> repository root
RESULTS = REPO / "02-access-analysis" / "sqlinspect-results"
TABLES_FILE = REPO / "database-scope" / "studied-tables.txt"
ASSET_FILES = REPO / "01-schema-reconstruction" / "application-overview" / "asset_related_files.txt"

NA = "{{na}}"
CONTAINER_PREFIX = "/repo/"  # repository mount point inside the SQLInspect container
OPERATIONS = ["SELECT", "INSERT", "UPDATE", "DELETE"]
CSV_FIELDS = ["run", "id", "file", "line", "class", "method", "exec_string",
              "resolved", "operation", "tables_in_scope", "sql"]


def load_tables():
    """The 22 studied tables (comments and blank lines ignored)."""
    lines = TABLES_FILE.read_text(encoding="utf-8").splitlines()
    return [l.strip().upper() for l in lines if l.strip() and not l.startswith("#")]


def load_asset_files():
    """Java files related to the fixed assets (list produced in step 1.1)."""
    if not ASSET_FILES.exists():
        return set()
    return {l.strip() for l in ASSET_FILES.read_text(encoding="utf-8").splitlines() if l.strip()}


def find_one(run_dir, suffix):
    """The single file of the run ending with `suffix` (e.g. '-queries.xml')."""
    matches = sorted(run_dir.glob(f"*{suffix}"))
    if len(matches) != 1:
        sys.exit(f"error: expected one *{suffix} in {run_dir}, found {len(matches)}")
    return matches[0]


def read_stats_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def method_name(query, exec_file):
    """Name of the method containing the hotspot, taken from the call stack."""
    calls = query.findall("CallStack/Call")
    exec_line = query.findtext("ExecLine")
    # Prefer the call located at the hotspot itself, else the first one
    for call in calls:
        if call.get("file") == exec_file and call.get("callLine") == exec_line:
            break
    else:
        call = calls[0] if calls else None
    if call is None:
        return ""
    full = call.get("method", "")          # pkg.Class.method(arg types)
    return full.split("(")[0].rsplit(".", 1)[-1]


def operation_of(sql):
    """First SQL keyword (SELECT, UPDATE, ...), or '' if none."""
    m = re.match(r"\s*\(?\s*([A-Za-z]+)", sql)
    return m.group(1).upper() if m else ""


def parse_queries(run, queries_xml, table_re):
    rows = []
    for q in ET.parse(queries_xml).getroot().findall("Query"):
        exec_file = q.findtext("ExecFile", "")
        sql = (q.findtext("Value") or "").strip()
        resolved = bool(sql) and sql != NA
        tables = sorted({t.upper() for t in table_re.findall(sql)}) if resolved else []
        rows.append({
            "run": run,
            "id": int(q.get("id")),
            "file": exec_file.removeprefix(CONTAINER_PREFIX),
            "line": int(q.findtext("ExecLine", "0")),
            "class": q.findtext("ExecClass", ""),
            "method": method_name(q, exec_file),
            "exec_string": q.findtext("ExecString", ""),
            "resolved": resolved,
            "operation": operation_of(sql) if resolved else "",
            "tables_in_scope": ";".join(tables),
            "sql": " ".join(sql.split()),   # one line per query in the CSV
        })
    # SQLInspect's output order changes between runs: sort for stable diffs
    rows.sort(key=lambda r: (r["file"], r["line"], r["sql"], r["id"]))
    return rows


def summarise(run_dir, table_re, asset_files, out_dir):
    run = run_dir.name
    rows = parse_queries(run, find_one(run_dir, "-queries.xml"), table_re)

    csv_path = out_dir / f"{run}-queries.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    model = read_stats_csv(find_one(run_dir, "-Model.stats"))[0]
    timing = read_stats_csv(find_one(run_dir, "-SQLInspect.stats"))
    total_ms = next((int(r["Diff"]) for r in timing
                     if r["Kind"] == "Time" and r["Key"].endswith(":ALL")), None)

    resolved = [r for r in rows if r["resolved"]]
    asset_hotspots = {(r["file"], r["line"]) for r in rows if r["file"] in asset_files}
    stats = {
        "Hotspots": int(model["Hotspots"]),
        "Queries": len(rows),
        "Unresolved queries (`{{na}}` or empty)": sum(not r["resolved"] for r in rows),
        "Resolved queries": len(resolved),
        "&nbsp;&nbsp;of which partially (contain `{{na}}`)": sum(NA in r["sql"] for r in resolved),
    }
    for op in OPERATIONS:
        stats[f"&nbsp;&nbsp;{op}"] = sum(r["operation"] == op for r in resolved)
    stats["&nbsp;&nbsp;other"] = sum(r["operation"] not in OPERATIONS for r in resolved)
    stats["Queries on the 22 studied tables"] = sum(bool(r["tables_in_scope"]) for r in rows)
    stats["Hotspots in fixed-asset files (step 1.1 list)"] = len(asset_hotspots)
    stats["Run time (s)"] = f"{total_ms / 1000:.1f}" if total_ms is not None else "?"

    print(f"{run}: {len(rows)} queries -> {csv_path.relative_to(REPO)}")
    return run, stats


def write_summary(results, out_dir, inputs):
    runs = [run for run, _ in results]
    metrics = list(results[0][1])
    lines = [
        "# SQLInspect runs: comparison",
        "",
        "Generated by [`tools/sqlinspect/sqlinspect_summary.py`](../../../tools/sqlinspect/sqlinspect_summary.py) "
        "(`uv run tools/sqlinspect/sqlinspect_summary.py`). Do not edit by hand.",
        "",
        "Inputs: " + ", ".join(f"`{p}`" for p in inputs),
        "",
        "| Metric | " + " | ".join(runs) + " |",
        "|---|" + "---:|" * len(runs),
    ]
    for m in metrics:
        lines.append(f"| {m} | " + " | ".join(str(s[m]) for _, s in results) + " |")
    lines += [
        "",
        "- A *query* is the SQL rebuilt by SQLInspect for a hotspot; `{{na}}` means the text could not be rebuilt.",
        "- *Partially resolved*: the SQL structure is known but some parts (often the table name) are `{{na}}`, "
        "e.g. `UPDATE {{na}} SET {{na}}={{question}} WHERE {{na}}`.",
        "- *Queries on the 22 studied tables*: resolved queries whose SQL names one of the tables of "
        "[`database-scope/studied-tables.txt`](../../../database-scope/studied-tables.txt) (case-insensitive, whole word).",
        "- *Hotspots in fixed-asset files*: distinct (file, line) hotspots located in one of the files of "
        "[`asset_related_files.txt`](../../../01-schema-reconstruction/application-overview/asset_related_files.txt).",
        "- Run time is the `ALL` phase of `*-SQLInspect.stats`; it varies between runs and machines.",
        "",
    ]
    path = out_dir / "summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"summary -> {path.relative_to(REPO)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("runs", nargs="*", type=Path,
                        help="raw run directories (default: every directory in raw/)")
    parser.add_argument("--out", type=Path, default=RESULTS / "filtered",
                        help="output directory (default: %(default)s)")
    args = parser.parse_args()

    run_dirs = args.runs or sorted(p for p in (RESULTS / "raw").iterdir() if p.is_dir())
    run_dirs = [p.resolve() for p in run_dirs]
    for p in run_dirs:
        if not p.is_dir():
            sys.exit(f"error: {p} is not a directory")
    if not run_dirs:
        sys.exit("error: no run directory found")

    tables = load_tables()
    table_re = re.compile(r"\b(" + "|".join(map(re.escape, tables)) + r")\b", re.IGNORECASE)
    asset_files = load_asset_files()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    results = [summarise(p, table_re, asset_files, out_dir) for p in run_dirs]
    write_summary(results, out_dir, [str(p.relative_to(REPO)) for p in run_dirs])


if __name__ == "__main__":
    main()
