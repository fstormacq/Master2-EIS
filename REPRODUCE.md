# Reproducing the analysis

This file lists, in order, **every command used to produce the results** in this repository. Running them from a fresh clone must give the same outputs.

Each step's README gives the details (options, known issues, how to read the results). This file is the single entry point.

## Rules for adding a command

When you produce or regenerate a result, add an entry to the matching section **in the same commit** as the result:

- **Command:** run from the repository root. Prefer a script in `tools/` over a long inline command.
- **Output:** the files written by the command.
- **Tool version:** if a third-party tool is involved.
- **Notes:** anything needed to interpret or reproduce it (manual step, nondeterminism, known limitation).

A result without an entry here is not considered reproducible. Manual steps (DB-Main, diagrams, LLM prompts) are also listed, with the input and how the output was checked.

## 0. Setup

Requirements: Git, Docker ([Docker Desktop](https://www.docker.com/products/docker-desktop/) on macOS/Windows, Docker Engine on Linux), [uv](https://docs.astral.sh/uv/) for the Python scripts.

```bash
git clone --recurse-submodules --shallow-submodules https://github.com/fstormacq/Master2-EIS.git
cd Master2-EIS

# Check the analysed ADempiere version
git submodule status
# expected: 4ae098fd18065f1a658ff56de3b90e63aabfecb2 target

# Creates the environment
uv sync

# Build the SQLInspect image and check it works (first run: a few minutes)
./tools/sqlinspect/sqlinspect.sh -help
```

| Tool | Version | How it is pinned |
|---|---|---|
| ADempiere (analysed system) | `develop` @ `4ae098f` | Git submodule `target/` |
| SQLInspect | `0.4.2.v20241021-1301` | `docker/sqlinspect/Dockerfile` (SHA-256 checked) |
| Java (for SQLInspect) | Temurin 21 JRE | Docker base image `eclipse-temurin:21-jre` |
| Python (for `tools/**/*.py`) | ≥ 3.14, standard library only | `pyproject.toml` / `uv.lock`, run with `uv run` |

## 1. Schema reconstruction

*No command yet.*

| Result | Command | Output | Notes |
|---|---|---|---|
| | | | |

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

### 2.3 Statistics and used logical subschema

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

# 2. Database access analysis
./tools/sqlinspect/run_sqlinspect_asset.sh
./tools/sqlinspect/run_sqlinspect_base.sh
uv run tools/sqlinspect/sqlinspect_summary.py

# 3. What-if analysis

# 4. Quality assessment
```
