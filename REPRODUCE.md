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

Requirements: Git, Docker ([Docker Desktop](https://www.docker.com/products/docker-desktop/) on macOS/Windows, Docker Engine on Linux).

```bash
git clone --recurse-submodules --shallow-submodules https://github.com/fstormacq/Master2-EIS.git
cd Master2-EIS

# Check the analysed ADempiere version
git submodule status
# expected: 4ae098fd18065f1a658ff56de3b90e63aabfecb2 target

# Build the SQLInspect image and check it works (first run: a few minutes)
./tools/sqlinspect.sh -help
```

| Tool | Version | How it is pinned |
|---|---|---|
| ADempiere (analysed system) | `develop` @ `4ae098f` | Git submodule `target/` |
| SQLInspect | `0.4.2.v20241021-1301` | `docker/sqlinspect/Dockerfile` (SHA-256 checked) |
| Java (for SQLInspect) | Temurin 21 JRE | Docker base image `eclipse-temurin:21-jre` |

## 1. Schema reconstruction

*No command yet.*

| Result | Command | Output | Notes |
|---|---|---|---|
| | | | |

## 2. Database access analysis

### 2.1 SQLInspect

| Result | Command | Output | Notes |
|---|---|---|---|
| JDBC accesses of the asset module | `./tools/run_sqlinspect_asset.sh` | `02-access-analysis/sqlinspect-results/raw/adempiere-asset-*` | MySQL dialect (PostgreSQL unsupported). 8 hotspots, 8 queries. Entry order varies between runs, content does not. `*.SQLInspect.stats` holds timings and changes every run. |

Underlying SQLInspect command (inside the container, working directory = repository root):

```bash
sqlinspect -projectname adempiere-asset \
  -projectdir target/org.adempiere.asset \
  -hotspotfinder JDBCHotspotFinder \
  -dialect MySQL \
  -outdir 02-access-analysis/sqlinspect-results/raw
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
./tools/run_sqlinspect_asset.sh
```
