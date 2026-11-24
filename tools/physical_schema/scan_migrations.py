#!/usr/bin/env python3
"""Step 1.2: check that the XML migrations added after the seed dump do not
touch the studied tables.

Which migrations come after the dump is deduced, not hard-coded: the dump
records the migrations already applied in adempiere.ad_migration. The script
takes their highest SeqNo, scans every migration/**/*.xml and keeps the files
whose <Migration SeqNo="..."> is higher. It then checks that this selection is
exactly the content of --expected-dir (394lts-3.9.4.001) and prints the result.

An XML migration of type AD can change a table without naming it: a new column
is an AD_Column record that only holds the numeric ID of the table
(<Data Column="AD_Table_ID">53137</Data>), and an update of an existing column
(<PO Table="AD_Column" Action="U" Record_ID="56816">) only holds the ID of the
column. Each selected file is therefore parsed as XML, and the script reports:

  1. the value of an AD_Table_ID field that is one of the studied tables, with
     the Table of the parent PO (to sort out records of AD_Tab, AD_Process...);
  2. a record of AD_Table itself (<PO Table="AD_Table">) whose Record_ID is one
     of the studied tables;
  3. the name of a studied table as a whole word, case-insensitive, in any
     text or attribute (SQL steps included);
  4. a record of AD_Column (<PO Table="AD_Column">) whose Record_ID is a column
     of a studied table in the dump.

Rule 4 only knows the columns present in the dump: a column created by a
migration and updated later is not mapped, but its creation is found by rule 1.

A plain grep on the IDs is not used on purpose: it gives false positives, e.g.
539 (A_Asset) matches the milliseconds of timestamps such as
"2021-10-29 09:27:25.539" in 09970_Add_Import_Requisition.xml.

The IDs and SeqNo are read from the COPY blocks of adempiere.ad_table,
adempiere.ad_column and adempiere.ad_migration in the dump. This only reads
data rows, never the DDL of the dump.

Usage (from the repository root), after extracting the dump:
    unzip -p target/data/seed/Adempiere_pg.jar Adempiere_pg.dmp > workspace/ps/dump.sql
    uv run tools/physical_schema/scan_migrations.py
    # positive controls (see REPRODUCE.md 1.2 (c) for the expected results)
    uv run tools/physical_schema/scan_migrations.py --names HR_EMPLOYEE
    uv run tools/physical_schema/scan_migrations.py --names M_REQUISITIONLINE

or with plain Python (3.9 or later):
    python3 tools/physical_schema/scan_migrations.py [options]

Output: the highest SeqNo of the dump, the selected files, then one line per
selected file, "<hits> <file> [matches]" (hits = number of distinct matches).
Exit code: 0 if no file references the tables, 1 otherwise, 2 if the result
cannot be trusted (dump missing, table not found in the dump, XML file that
cannot be parsed).

Only the Python standard library is used.

Author: Claude Opus 5.5 (AI-generated), 24.11.2026. Reviewed by the group.
Prompt, model and checks: AI_USAGE.md, section "1.2 Source of the physical
schema". Commands and expected results: REPRODUCE.md, section 1.2 (c).
"""

import argparse
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

DEFAULT_TABLES = "database-scope/studied-tables.txt"
DEFAULT_DUMP = "workspace/ps/dump.sql"
DEFAULT_MIGRATIONS = "target/migration"
DEFAULT_EXPECTED_DIR = "394lts-3.9.4.001"


def read_table_names(path):
    """Table names of the studied subset, upper case (comments, also at end of line, and blank lines skipped)."""
    with open(path, encoding="utf-8") as f:
        names = (l.split("#")[0].strip() for l in f)
        return [n.upper() for n in names if n]


def read_copy(dump_path, table, keep):
    """Rows of the COPY block of adempiere.<table>, as dicts {column: value} restricted
    to the columns in `keep` (NULL, written \\N in the dump, becomes None)."""
    prefix = f"COPY adempiere.{table} ("
    rows, columns = [], None
    with open(dump_path, encoding="utf-8") as f:
        for line in f:
            if columns is None:
                if line.startswith(prefix):
                    # column order is taken from the COPY header, not hard-coded
                    columns = [c.strip() for c in line[len(prefix):line.index(")")].split(",")]
                    idx = [(c, columns.index(c)) for c in keep]
                continue
            if line.startswith("\\."):
                break
            fields = line.rstrip("\n").split("\t")
            rows.append({c: (None if fields[i] == "\\N" else fields[i]) for c, i in idx})
    if columns is None:
        raise ValueError(f"no COPY block for adempiere.{table} in {dump_path}")
    return rows


def select_migrations(root_dir, max_seqno):
    """Parse every XML file under root_dir and keep those with a <Migration SeqNo> > max_seqno.
    Return (selected [(path, xml root)], files that cannot be parsed [(path, error)])."""
    selected, errors = [], []
    for path in sorted(glob.glob(os.path.join(root_dir, "**", "*.xml"), recursive=True)):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as e:
            errors.append((path, e))
            continue
        seqnos = [int(m.get("SeqNo")) for m in root.iter("Migration") if m.get("SeqNo")]
        if seqnos and max(seqnos) > max_seqno:
            selected.append((path, root))
    return selected, errors


def scan_file(root, ids, col_ids, name_re):
    """Return the list of matches (IDs and table names) found in one parsed XML migration."""
    hits = []
    for po in root.iter("PO"):  # every <Data> of the migrations sits inside a <PO>
        table, record = po.get("Table"), po.get("Record_ID")
        if table == "AD_Table" and record in ids:
            hits.append(f"AD_Table.Record_ID={record} ({ids[record]})")
        if table == "AD_Column" and record in col_ids:
            hits.append(f"AD_Column.Record_ID={record} ({col_ids[record]}) Action={po.get('Action')}")
        for d in po.iter("Data"):
            text = (d.text or "").strip()
            if d.get("Column") == "AD_Table_ID" and text in ids:
                hits.append(f"AD_Table_ID={text} ({ids[text]}) in PO {table} {record}")
    for e in root.iter():
        for s in [e.text or ""] + list(e.attrib.values()):
            hits += name_re.findall(s)
    return hits


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--tables", default=DEFAULT_TABLES, help=f"list of studied tables (default: {DEFAULT_TABLES})")
    p.add_argument("--dump", default=DEFAULT_DUMP, help=f"extracted SQL dump (default: {DEFAULT_DUMP})")
    p.add_argument("--migrations", default=DEFAULT_MIGRATIONS,
                   help=f"root directory of the XML migrations, searched recursively (default: {DEFAULT_MIGRATIONS})")
    p.add_argument("--expected-dir", default=DEFAULT_EXPECTED_DIR,
                   help="sub-directory of --migrations that the post-dump selection should match exactly "
                        f"(default: {DEFAULT_EXPECTED_DIR})")
    p.add_argument("--names", nargs="+", metavar="TABLE",
                   help="search these tables instead of --tables (positive control)")
    args = p.parse_args()

    if not os.path.isfile(args.dump):
        print(f"{args.dump} not found. Extract it first:\n"
              "  unzip -p target/data/seed/Adempiere_pg.jar Adempiere_pg.dmp > " + args.dump, file=sys.stderr)
        return 2
    names = [n.upper() for n in args.names] if args.names else read_table_names(args.tables)
    wanted = set(names)
    ids = {r["ad_table_id"]: r["tablename"]
           for r in read_copy(args.dump, "ad_table", ("ad_table_id", "tablename")) if r["tablename"].upper() in wanted}
    missing = sorted(wanted - {n.upper() for n in ids.values()})
    if missing:
        print(f"AD_Table_ID not found in {args.dump}: {', '.join(missing)}", file=sys.stderr)
        return 2
    col_ids = {r["ad_column_id"]: f"{ids[r['ad_table_id']]}.{r['columnname']}"
               for r in read_copy(args.dump, "ad_column", ("ad_column_id", "ad_table_id", "columnname"))
               if r["ad_table_id"] in ids}
    print(f"{len(ids)} AD_Table_ID and {len(col_ids)} AD_Column_ID found in {args.dump}")

    # Scope: migrations not yet applied in the dump
    last = max(read_copy(args.dump, "ad_migration", ("seqno", "name")), key=lambda r: int(r["seqno"]))
    max_seqno = int(last["seqno"])
    print(f"Highest SeqNo in adempiere.ad_migration: {max_seqno} ({last['name']})")
    selected, errors = select_migrations(args.migrations, max_seqno)
    for path, e in errors:
        print(f"PARSE ERROR {path}: {e}", file=sys.stderr)
    paths = {p for p, _ in selected}
    expected = set(glob.glob(os.path.join(args.migrations, args.expected_dir, "*.xml")))
    print(f"{len(selected)} files with a Migration SeqNo > {max_seqno}; "
          f"same set as {args.expected_dir}/ ({len(expected)} files): {'yes' if paths == expected else 'NO'}")
    for p in sorted(paths ^ expected):
        print(f"  {'only selected' if p in paths else 'only in ' + args.expected_dir}: {p}")

    name_re = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\b", re.I)
    touched = 0
    for path, root in selected:
        hits = sorted(set(scan_file(root, ids, col_ids, name_re)))
        touched += bool(hits)
        print(len(hits), os.path.relpath(path, args.migrations), hits or "")
    print(f"{touched} of {len(selected)} files reference the tables")
    if errors:
        print(f"{len(errors)} XML files could not be parsed: result incomplete", file=sys.stderr)
        return 2
    return 1 if touched else 0


if __name__ == "__main__":
    sys.exit(main())
