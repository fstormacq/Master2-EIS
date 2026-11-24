# Reproducing the analysis

This file lists, in order, **every command used to produce the results** in this repository. Running them from a fresh clone must give the same outputs.

Each step's README gives the details (options, known issues, how to read the results). This file is the single entry point.

## Rules for adding a command

When you produce or regenerate a result, add an entry to the matching section **in the same commit** as the result:

- **Command:** run from the repository root. Prefer a script in `tools/` over a long inline command.
- **Output:** the files written by the command.
- **Tool version:** if a third-party tool is involved.
- **Notes:** anything needed to interpret or reproduce it (manual step, nondeterminism, known limitation).

A result without an entry here is not considered reproducible. Manual steps (DB-Main, diagrams) are also listed, with the input and how the output was checked. Every use of an LLM is documented in [`AI_USAGE.md`](AI_USAGE.md) (model, date, prompt, how the output was checked).

## 0. Setup

Requirements: Git, Docker ([Docker Desktop](https://www.docker.com/products/docker-desktop/) on macOS/Windows, Docker Engine on Linux), [uv](https://docs.astral.sh/uv/) for the Python scripts, [cloc](https://github.com/AlDanial/cloc) for step 1.1.

```bash
git clone --recurse-submodules --shallow-submodules https://github.com/fstormacq/Master2-EIS.git
cd Master2-EIS

# Check the analysed ADempiere version
git submodule status
# expected: 4ae098fd18065f1a658ff56de3b90e63aabfecb2 target

# Create the Python environment (optional: uv run does it automatically)
uv sync

# Build the SQLInspect image and check it works (first run: a few minutes)
./tools/sqlinspect/sqlinspect.sh -help
```

| Tool | Version | How it is pinned |
|---|---|---|
| ADempiere (analysed system) | `develop` @ `4ae098f` | Git submodule `target/` |
| SQLInspect | `0.4.2.v20241021-1301` | `docker/sqlinspect/Dockerfile` (SHA-256 checked) |
| Java (for SQLInspect) | Temurin 21 JRE | Docker base image `eclipse-temurin:21-jre` |
| Python (for `tools/**/*.py`) | ≥ 3.9, standard library only | `pyproject.toml` / `uv.lock`, run with `uv run` |
| cloc (step 1.1) | 2.12 | Not pinned: install it with your package manager. Other versions may give slightly different counts |
| PostgreSQL (step 1.2) | 15 (same major version as the dump, `pg_dump` 15.1) | Docker image `postgres:15` |

## 1. Schema reconstruction

### 1.1 Application overview

Details and interpretation: [`01-schema-reconstruction/application-overview/README.md`](01-schema-reconstruction/application-overview/README.md).

| Result | Command | Output | Notes |
|---|---|---|---|
| Size of the whole ADempiere code | `cloc target/ --exclude-dir=.git --quiet --csv --out=01-schema-reconstruction/application-overview/cloc_total.csv` | `application-overview/cloc_total.csv` | cloc 2.12. About 35 s |
| Size of the asset module | `cloc target/org.adempiere.asset/ --quiet --csv --out=01-schema-reconstruction/application-overview/cloc_asset.csv` | `application-overview/cloc_asset.csv` | cloc 2.12 |
| Java lines of code per top-level folder | Loop below | `application-overview/structure_folder.txt` | cloc 2.12 |
| Java files that mention one of the 22 tables | Commands below | `application-overview/asset_related_files.txt` (138 files) | Whole-word match, with optional `I_` / `X_` prefix. `LC_ALL=C` makes the sort order identical on every machine |

```bash
# Java lines of code per top-level folder
for d in target/*/; do
  n=$(cloc "$d" --quiet --include-lang=Java --csv 2>/dev/null | awk -F, '$2=="Java"{print $5}')
  printf "%-45s %s\n" "$d" "${n:-0}"
done | sort -k2 -rn > 01-schema-reconstruction/application-overview/structure_folder.txt

# Java files that mention one of the 22 studied tables
tables=$(grep -oE '^A_[A-Z_]+' database-scope/studied-tables.txt | LC_ALL=C sort -u)
pattern=$(echo "$tables" | sed -E 's/.*/(^|[^A-Za-z0-9_])(I_|X_)?&([^A-Za-z0-9_]|$)/' | paste -sd'|' -)
grep -rliE "$pattern" target --include='*.java' | LC_ALL=C sort \
  > 01-schema-reconstruction/application-overview/asset_related_files.txt
```

The `grep` commands that support the *Application dictionary* section (`I_A_Asset`, `X_A_Asset`, `MAsset`) are read-only checks, listed in the README of the folder.

### 1.2 Source of the physical schema

Details and interpretation: [`01-schema-reconstruction/physical-schema/README.md`](01-schema-reconstruction/physical-schema/README.md).

These commands produce no file in the repository. They are read-only checks that support the choice of the PostgreSQL seed dump as the source of the physical schema, and show that no migration has to be applied on top of it. Expected results are given after each block. Run them from the repository root, in order.

| Check | Expected result | Notes |
|---|---|---|
| (a) The seed jar did not change since release 3.9.4 | Same blob `c55e6e08…` at tag `3.9.4` and at `HEAD`, a different one in November 2022 | Needs some Git history (the submodule is cloned shallow) |
| (b) Migrations added after the dump | 18 XML files in `migration/394lts-3.9.4.001/`, plus `build.gradle` and `build.properties` | The 2 build files do not touch the schema |
| (c) None of the migrations applied after the dump references one of the 22 tables | Highest `SeqNo` of the dump = 9900, the same 18 files as in (b), `0` for each file | XML parsing, by table name, `AD_Table_ID` and `AD_Column_ID` |
| (d) Virtual columns in the migration scripts | 8 in `979_FA_Stabilization.sql`, 2 of them set back to physical by `980_armen_fix_dictionary.sql` | |
| (e) Same check in the restored database | 22 tables, exactly 6 virtual columns, 0 extra column | PostgreSQL 15 in Docker. Restore takes about 5 min |

#### (a) and (b): date of the dump and later migrations

The submodule is cloned with `--shallow-submodules`, so it contains a single commit: `git log -- <file>` then attributes every file to that commit and cannot date anything. The first command fetches the history since October 2022 (enough to cover the dump) without changing the checked-out commit. `git log` is still unreliable at the edges of a shallow history, so we compare the *content* of the jar (its blob hash) between revisions instead, and list later migrations with `git diff` between two trees, which needs no history.

```bash
git -C target fetch --shallow-since=2022-10-01

# (a) Blob hash of the jar: identical at tag 3.9.4 (2023-01-24) and at HEAD, different before
for rev in ff9e4ef1 3.9.4 HEAD; do
  echo "$rev $(git -C target rev-parse "$rev:data/seed/Adempiere_pg.jar") $(git -C target log -1 --format=%ad --date=short "$rev")"
done

# Content of the jar and header of the dump (pg_dump 15.1, plain SQL, schema adempiere)
unzip -l target/data/seed/Adempiere_pg.jar
mkdir -p workspace/ps && unzip -p target/data/seed/Adempiere_pg.jar Adempiere_pg.dmp > workspace/ps/dump.sql
head -6 workspace/ps/dump.sql

# (b) Migration files added (A) or modified (M) between the dump and the analysed commit
git -C target diff --name-status 3.9.4 HEAD -- migration/
```

Always give the entry name `Adempiere_pg.dmp` to `unzip -p`. Without it, `META-INF/MANIFEST.MF` is written in front of the dump and the restore fails on its first statement (`syntax error at or near "Manifest"`).

#### (c): do the post-dump migrations touch our tables?

**Which migrations.** The dump records the migrations already applied in the table `adempiere.ad_migration`. Its highest `SeqNo` is 9900 (*Synchronize DB version and date version on seed with code*). The script scans every `migration/**/*.xml` (978 files, of which 6 `build.xml` files have no `<Migration>`) and keeps those whose `<Migration SeqNo="…">` is higher than 9900. It then checks that this selection is exactly the content of `394lts-3.9.4.001/`. The scope is therefore deduced from the dump, and confirms the Git result of step (b) by another way.

**How a migration can touch a table without naming it.** An XML migration of type `AD` changes the application dictionary record by record:

- a new column is an `AD_Column` record that only contains the numeric ID of its table (`<Data Column="AD_Table_ID">53137</Data>`);
- an update of an existing column (`<PO Table="AD_Column" Action="U" Record_ID="56816">`) only contains the ID of the column, neither the name nor the ID of its table.

We therefore search by name, by `AD_Table_ID` **and** by `AD_Column_ID`. A plain `grep` on the IDs gives false positives: for example, `539` (the ID of `A_Asset`) matches the milliseconds of timestamps in `09970_Add_Import_Requisition.xml`:

```bash
grep -nw 539 target/migration/394lts-3.9.4.001/09970_Add_Import_Requisition.xml | head -2
# <Data AD_Column_ID="12960" Column="Created">2021-10-29 09:27:25.539</Data>  -> false positive
```

The script [`tools/physical_schema/scan_migrations.py`](tools/physical_schema/scan_migrations.py) parses each selected file as XML and reports four kinds of matches:

1. the value of an `AD_Table_ID` field that is one of our tables, with the `Table` of the record that contains it (so that a reference from `AD_Tab`, `AD_Process` or `AD_Ref_Table` can be told apart from a new column);
2. a record of `AD_Table` itself whose `Record_ID` is one of our tables;
3. the name of one of our tables as a whole word, in any text or attribute (SQL steps included);
4. a record of `AD_Column` whose `Record_ID` is a column of one of our tables.

The IDs come from the `COPY` blocks of `adempiere.ad_table`, `adempiere.ad_column` and `adempiere.ad_migration` in the dump (data rows only, never the DDL). Rule 4 only knows the columns that exist in the dump: a column created by a migration and updated later in it is not mapped, but its creation is already found by rule 1. The script needs `workspace/ps/dump.sql` from step (a) and takes about 2 s. Script AI-generated (see [`AI_USAGE.md`](AI_USAGE.md#12-source-of-the-physical-schema)), then corrected after a review by the group.

```bash
# Main check. Expected:
#   22 AD_Table_ID and 710 AD_Column_ID found (710 = number of COLUMNNAME_* constants, see (e))
#   Highest SeqNo in adempiere.ad_migration: 9900 (Synchronize DB version and date version on seed with code)
#   18 files with a Migration SeqNo > 9900; same set as 394lts-3.9.4.001/ (18 files): yes
#   0 for each of the 18 files, then "0 of 18 files reference the tables", exit code 0
uv run tools/physical_schema/scan_migrations.py

# Positive controls: the same search on tables that the migrations do modify.
# By ID (rules 1 and 4). Expected: 1 file, 09930_4179_AddingBusinessPartnerLocationRequisitionLine.xml,
# with 2 matches: the new column 100917 (AD_Table_ID=703 in PO AD_Column 100917)
# and the update of the existing column 56816 (M_RequisitionLine.C_BPartner_ID, Action=U)
uv run tools/physical_schema/scan_migrations.py --names M_REQUISITIONLINE
# By name (rule 3). Expected: 2 files, 09990_Fix_Lenght_for_Employee_Validation_Code.xml
# and 10000_4086_Add_Garden_World_Test_Data.xml
uv run tools/physical_schema/scan_migrations.py --names HR_EMPLOYEE
```

The number at the start of each line is the number of *distinct* matches, listed after the file name. In `09930_4179`, the same file also updates the length of the new column 100917 (`FieldLength` 22 → 10). This update is not counted: column 100917 does not exist in the dump (see the limit of rule 4 above).
Exit codes: `0` if no file references the tables, `1` otherwise (expected for the positive controls), `2` if the result cannot be trusted (dump missing, table not found in it, XML file that cannot be parsed). Options: `--tables`, `--dump`, `--migrations` (root directory, searched recursively) and `--expected-dir` change the inputs (`--help` for the defaults).

#### (d): virtual columns in the migration scripts

A virtual column is an `AD_Column` record with a non-NULL `ColumnSQL`: the application computes it at query time, and it does not exist in the database. The 6 columns of the `I_*.java` interfaces that are missing from the dump are defined in migration 979. This migration also declares `Processed` virtual in `A_Asset_Info_Fin` (`AD_Column_ID` 59319) and `A_Asset_Info_Lic` (59320), and migration 980 turns them back into physical columns:

The `INSERT INTO AD_Column` statements are positional: `ColumnSQL` only appears in the column list, and its value in `VALUES (...)`. In migration 979, the 8 statements that set `ColumnSQL` all share the same column list, which starts with `AD_Client_ID, AD_Column_ID, AD_Element_ID, AD_Org_ID, AD_Reference_ID, AD_Table_ID, ColumnName, ColumnSQL`. The first command keeps those whose `ColumnSQL` value starts with a quote (that is, is not `NULL`) and prints `AD_Column_ID`, `AD_Table_ID` and `ColumnName`.

```bash
M=target/migration/370lts-380lts/postgresql

# Expected: 8 rows. AD_Table_ID 53116 = A_Depreciation_Workfile (4), 53137 = A_Asset_Addition (2),
# 53132 = A_Asset_Info_Fin and 53134 = A_Asset_Info_Lic (Processed)
grep -oE "^INSERT INTO AD_Column \(AD_Client_ID,AD_Column_ID,AD_Element_ID,AD_Org_ID,AD_Reference_ID,AD_Table_ID,ColumnName,ColumnSQL,.* VALUES \(0,[0-9]+,[0-9]+,0,[0-9]+,[0-9]+,'[A-Za-z_]+','" \
  $M/979_FA_Stabilization.sql | grep -oE "VALUES .*"

# No UPDATE of migration 979 sets a non-NULL ColumnSQL (expected: 0)
grep -c "UPDATE AD_Column SET.*ColumnSQL='" $M/979_FA_Stabilization.sql

# Migration 980 sets ColumnSQL back to NULL for the two Processed columns (expected: lines 62 and 70)
grep -nE 'AD_Column_ID=(59319|59320)$' $M/980_armen_fix_dictionary.sql
```

#### (e): same check in the restored database

The dump grants rights to a role `adempiere`, which must exist before the restore. The restore uses `psql -f` (the dump is plain SQL, not a `pg_restore` archive).

```bash
docker run -d --name ps-check -e POSTGRES_PASSWORD=check -e POSTGRES_DB=adempiere \
  -v "$PWD/workspace/ps/dump.sql:/dump.sql:ro" postgres:15
until docker exec ps-check pg_isready -U postgres -q; do sleep 2; done; sleep 3
docker exec ps-check psql -U postgres -d adempiere -q -c 'CREATE ROLE adempiere'
docker exec ps-check psql -U postgres -d adempiere -q -f /dump.sql > workspace/ps/restore.log 2>&1
grep -c ERROR workspace/ps/restore.log   # expected: 0
```

Then query the catalogue. `TABLES` holds the 22 table names, comma-separated. The function `psql_ps` runs `psql` in the container and passes `TABLES` as the psql variable `:'tables'`. A function is used rather than a variable such as `PSQL="docker exec …"`, because zsh (the default shell on macOS) does not split `$PSQL` into words and fails with `file name too long`. The commands work the same in bash and zsh.

```bash
TABLES=$(grep -oE '^A_[A-Z_]+' database-scope/studied-tables.txt | paste -sd, -)
psql_ps() { docker exec -i ps-check psql -U postgres -d adempiere -At -F, -v tables="$TABLES" "$@"; }

# Number of tables found in the database (expected: 22)
psql_ps <<'EOF'
SELECT count(*) FROM information_schema.tables
WHERE table_schema = 'adempiere' AND upper(table_name) = ANY (string_to_array(:'tables', ','));
EOF

# Virtual columns of the 22 tables, and whether they physically exist
# (expected: 6 rows, the 6 columns of section (d) without Processed, all with physical = 0)
psql_ps <<'EOF'
SELECT t.tablename, c.columnname,
       (SELECT count(*) FROM information_schema.columns ic
        WHERE ic.table_schema = 'adempiere' AND ic.table_name = lower(t.tablename)
          AND ic.column_name = lower(c.columnname)) AS physical
FROM adempiere.ad_column c JOIN adempiere.ad_table t USING (ad_table_id)
WHERE upper(t.tablename) = ANY (string_to_array(:'tables', ',')) AND c.columnsql IS NOT NULL
ORDER BY 1, 2;
EOF
```

Finally, compare the `COLUMNNAME_*` constants of the 22 interfaces with the columns of the database. The interface files use mixed case (`I_A_Asset_Info_Fin.java`), hence the case-insensitive `grep -ix` to find them. `LC_ALL=C` is required for `sort` and `comm` to use the same order.

```bash
export LC_ALL=C
D=target/base/src/org/adempiere/core/domains/models
for t in $(echo "$TABLES" | tr , ' '); do
  f=$(ls $D | grep -ix "I_$t.java")
  grep -oE 'COLUMNNAME_[A-Za-z0-9_]+ *= *"[^"]+"' "$D/$f" | sed -E 's/.*"(.*)"/\1/' | awk -v t=$t '{print t"\t"tolower($0)}'
done | sort -u > workspace/ps/java_cols.tsv
psql_ps -F$'\t' <<'EOF' | sort -u > workspace/ps/db_cols.tsv
SELECT upper(table_name), column_name FROM information_schema.columns
WHERE table_schema = 'adempiere' AND upper(table_name) = ANY (string_to_array(:'tables', ','));
EOF
wc -l workspace/ps/java_cols.tsv workspace/ps/db_cols.tsv     # expected: 710 and 704
comm -23 workspace/ps/java_cols.tsv workspace/ps/db_cols.tsv  # in Java, not in the DB: the 6 virtual columns
comm -13 workspace/ps/java_cols.tsv workspace/ps/db_cols.tsv  # in the DB, not in Java: expected empty

docker rm -f ps-check   # when done
```

## 2. Database access analysis

### 2.1 SQLInspect

| Result | Command | Output | Notes |
|---|---|---|---|
| JDBC accesses of the asset module | `./tools/sqlinspect/run_sqlinspect_asset.sh` | `02-access-analysis/sqlinspect-results/raw/asset/adempiere-asset-*` | MySQL dialect (PostgreSQL unsupported). 8 hotspots, 8 queries, all `{{na}}`. About 3 s. |
| JDBC accesses of the core module `base/` | `./tools/sqlinspect/run_sqlinspect_base.sh` | `02-access-analysis/sqlinspect-results/raw/base/adempiere-base-*` | Same options. 620 hotspots, 633 queries, 598 `{{na}}`. About 40 s and 1 GB of memory. |
| Per-run query CSV and comparison table | `uv run tools/sqlinspect/sqlinspect_summary.py` | `02-access-analysis/sqlinspect-results/filtered/<run>-queries.csv`, `filtered/summary.md` | Reads every run in `raw/`. Run after the two commands above. Script AI-generated (see [`AI_USAGE.md`](AI_USAGE.md)), outputs checked against `raw/`. |

For all SQLInspect runs: entry order varies between runs, content does not (the CSVs are sorted, so they are stable). `*-SQLInspect.stats` holds timings and changes every run. The `*.log` files are ignored by Git. What each output file contains is explained in [`SQLINSPECT_OUTPUTS.md`](02-access-analysis/sqlinspect-results/SQLINSPECT_OUTPUTS.md).

Underlying SQLInspect command (inside the container, working directory = repository root), with `<run>` = `asset` (`-projectdir target/org.adempiere.asset`) or `base` (`-projectdir target/base`):

```bash
sqlinspect -projectname adempiere-<run> \
  -projectdir <projectdir> \
  -hotspotfinder JDBCHotspotFinder \
  -dialect MySQL \
  -outdir 02-access-analysis/sqlinspect-results/raw/<run>
```

### 2.2 Accesses not detected by SQLInspect

*No command yet.*

### 2.3 Structured access inventory

*No command yet.*

### 2.4 Statistics

*No command yet.*

### 2.5 Used logical subschema

*No command yet.*

## 3. What-if analysis

*No command yet.*

## 4. Quality assessment

*No command yet.*

## Bonus A. Version evolution

*No command yet.* Results produced on another ADempiere version must state the commit used (see the main [README](README.md#analysed-version)).

## Full re-run

Commands to regenerate every result, in order. Keep this list in sync with the sections above.

```bash
# 0. Setup: build the SQLInspect image
./tools/sqlinspect/sqlinspect.sh -help

# 1. Schema reconstruction
# 1.1: run the commands of section 1.1 above (cloc, Java files per table)
# 1.2: run the checks of section 1.2 above (read-only, no output file in the repository),
#      including: uv run tools/physical_schema/scan_migrations.py

# 2. Database access analysis
./tools/sqlinspect/run_sqlinspect_asset.sh
./tools/sqlinspect/run_sqlinspect_base.sh
uv run tools/sqlinspect/sqlinspect_summary.py

# 3. What-if analysis

# 4. Quality assessment
```
