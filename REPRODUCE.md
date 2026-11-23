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

## 1. Schema reconstruction

### 1.1 Application overview

Details and interpretation: [`01-schema-reconstruction/application-overview/README.md`](01-schema-reconstruction/application-overview/README.md).

> **Reconstructed commands, to be confirmed by the author of step 1.1.** They are deduced from the README of the folder and from the files it contains. In particular, the `--csv --out` options of the `cloc` commands are inferred from the format of `cloc_*.csv` and were not re-run with cloc 2.12. The list of Java files was re-run and gives the same 138 files.

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

# 2. Database access analysis
./tools/sqlinspect/run_sqlinspect_asset.sh
./tools/sqlinspect/run_sqlinspect_base.sh
uv run tools/sqlinspect/sqlinspect_summary.py

# 3. What-if analysis

# 4. Quality assessment
```
