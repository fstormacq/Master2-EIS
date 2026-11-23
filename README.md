# ADempiere Fixed Assets — Database Reverse Engineering

Reverse engineering and quality assessment of the **fixed assets** database of [ADempiere](https://github.com/adempiere/adempiere), an open-source Java ERP. We recover the schema, map how the code accesses it, assess the impact of schema changes and evaluate the overall quality.

Group project for **INFOM218 — Software Evolution**, University of Namur (2026–2027), Group 4.

## At a glance

| | |
|---|---|
| **System studied** | ADempiere, `develop` branch, commit [`4ae098f`](https://github.com/adempiere/adempiere/commit/4ae098fd18065f1a658ff56de3b90e63aabfecb2) |
| **Scope** | Fixed assets functional area: 22 tables, validated by the teaching team on 2 Nov 2026 |
| **Database** | PostgreSQL |
| **Status** | In progress: step 1.1 (application overview) and step 2.1 (SQLInspect on `org.adempiere.asset` and `base`, see [`02-access-analysis/README.md`](02-access-analysis/README.md)) done. See [`ROADMAP.md`](ROADMAP.md) for detailed progress |
| **Team** | Louca Mathieu (spokesperson), Nathan Lambrechts, Florian Stormacq |

## What this project delivers

| Step | Question answered | Main outputs |
|---|---|---|
| **1. Schema recovery** | What does the database look like? | Physical, logical and conceptual schemas; foreign key inference (precision/recall); implicit foreign keys |
| **2. Database access analysis** | How does the code use the database? | Inventory of database accesses (SQLInspect + other methods), query statistics, used logical subschema |
| **3. What-if analysis** | What breaks if the schema changes? | At least 10 schema evolution scenarios with their impact on the code |
| **4. Quality assessment** | Is it well designed? | Strengths, weaknesses and recommendations for the schema and the data access code |
| *Bonus A* | How did it evolve? | Comparison across three ADempiere versions |

## Scope: the fixed assets subset

The 22 tables cover the full lifecycle of a fixed asset, from acquisition to depreciation and disposal. The list is kept in [`database-scope/studied-tables.txt`](database-scope/studied-tables.txt).

| Sub-domain | Tables |
|---|---|
| Asset and classification | `A_ASSET`, `A_ASSET_GROUP`, `A_ASSET_CLASS`, `A_ASSET_TYPE`, `A_ASSET_PRODUCT` |
| Information records | `A_ASSET_INFO_FIN`, `A_ASSET_INFO_INS`, `A_ASSET_INFO_LIC`, `A_ASSET_INFO_OTH`, `A_ASSET_INFO_TAX` |
| Asset movements | `A_ASSET_ADDITION`, `A_ASSET_DELIVERY`, `A_ASSET_DISPOSED`, `A_ASSET_SPLIT`, `A_ASSET_CHANGE` |
| Accounting | `A_ASSET_ACCT`, `A_ASSET_GROUP_ACCT` |
| Depreciation | `A_DEPRECIATION`, `A_DEPRECIATION_WORKFILE`, `A_DEPRECIATION_EXP`, `A_DEPRECIATION_METHOD`, `A_DEPRECIATION_CONVENTION` |

## Repository layout

```
ROADMAP.md                 project plan and progress tracking
REPRODUCE.md               every command used to produce the results, in order
AI_USAGE.md                every use of an LLM: model, date, prompt, how it was checked
pyproject.toml, uv.lock    Python environment for the scripts in tools/ (managed by uv)
database-scope/            list of the studied tables
tools/                     scripts used to produce every result
docker/                    Docker image for third-party tools (SQLInspect)
01-schema-reconstruction/  PS, LS, CS and foreign key inference
02-access-analysis/        database access inventories, statistics, used subschema
03-what-if-analysis/       schema evolution scenarios and impact analysis
04-quality-assessment/     quality assessment and recommendations
bonus-version-evolution/   cross-version analysis
report/                    final report and slides
target/                    ADempiere source code (Git submodule, read-only)
workspace/                 Eclipse workspace created by SQLInspect (not versioned)
```

Each folder has its own `README.md`. It explains what the folder contains and which command regenerates it. Every result in this repository is meant to be **reproducible** from the pinned source code.

## Getting started

Clone the repository together with the ADempiere source code:

```bash
git clone --recurse-submodules --shallow-submodules https://github.com/fstormacq/Master2-EIS.git
cd Master2-EIS
```

If the repository is already cloned without the submodule:

```bash
git submodule update --init --depth 1
```

Requirements depend on the step. [`REPRODUCE.md`](REPRODUCE.md#0-setup) lists them all:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS, Windows) or Docker Engine (Linux) for SQLInspect, see [Third-party tools](#third-party-tools);
- [uv](https://docs.astral.sh/uv/) for the Python scripts (it installs a suitable Python if needed);
- [cloc](https://github.com/AlDanial/cloc) for step 1.1.

Step 2.1 in four commands:

```bash
./tools/sqlinspect/sqlinspect.sh -help          # builds the image on first run, then prints the CLI help
./tools/sqlinspect/run_sqlinspect_asset.sh      # step 2.1 analysis of org.adempiere.asset
./tools/sqlinspect/run_sqlinspect_base.sh       # step 2.1 analysis of base/
uv run tools/sqlinspect/sqlinspect_summary.py   # step 2.1 per-run CSV and comparison table
```

## Analysed version

All analyses refer to a single, fixed version of ADempiere:

| | |
|---|---|
| Repository | `adempiere/adempiere` |
| Branch | `develop` |
| Commit | `4ae098fd18065f1a658ff56de3b90e63aabfecb2` |
| License | GPL v2 |

The ADempiere source is **not copied** into this repository. It is referenced as a shallow Git submodule in `target/`, pinned to the commit above. Check the pinned version with:

```bash
git submodule status
# 4ae098fd18065f1a658ff56de3b90e63aabfecb2 target
```

<details>
<summary>How the commit was pinned / how to change it</summary>

Pinning:

```bash
SHA=4ae098fd18065f1a658ff56de3b90e63aabfecb2
git submodule add --depth 1 https://github.com/adempiere/adempiere.git target
git -C target fetch --depth 1 origin "$SHA"
git -C target checkout "$SHA"
git config -f .gitmodules submodule.target.shallow true
git add .gitmodules target
git commit -m "Pin ADempiere at ${SHA:0:7}"
```

Changing the version, for example for the cross-version bonus analysis:

```bash
git -C target fetch --depth 1 origin <new-sha>
git -C target checkout <new-sha>
git add target
git commit -m "Bump ADempiere to <new-sha>"
```

Then update the table above. Results produced on another version must state that version explicitly.

</details>

## Third-party tools

Third-party tools are **not committed**. SQLInspect runs in a Docker image built from [`docker/sqlinspect/Dockerfile`](docker/sqlinspect/Dockerfile). The build downloads a pinned version and checks its integrity. Java, the virtual display and all native libraries are inside the image, so the tool behaves the same on Linux, macOS and Windows (WSL).

| Tool | Version | Source | Run |
|---|---|---|---|
| [SQLInspect](https://bitbucket.org/csnagy/sqlinspect) (Nagy & Cleve, ICSE 2018) | CLI `0.4.2.v20241021-1301`, Linux x86_64 | [Bitbucket downloads](https://bitbucket.org/csnagy/sqlinspect/downloads/) | `./tools/sqlinspect/sqlinspect.sh <args>` |

SQLInspect archive SHA-256: `f91d8c1bfab0d5800d4c0b5d8f1b6dfe75a5044cc184dee499ced96531753c9c`

**How the wrapper works.** `tools/sqlinspect/sqlinspect.sh` builds the image `master2-eis/sqlinspect:0.4.2` the first time it runs (set `SQLINSPECT_REBUILD=1` to force a rebuild). It then runs the container with the repository root mounted at `/repo` as the working directory and passes every argument to SQLInspect unchanged. Paths are therefore given relative to the repository root, and the file paths written in the results start with `/repo/`, whatever the machine. The container runs as the host user, so generated files are not owned by root.

**Requirements and known issues:**

- **Apple Silicon / ARM:** SQLInspect only ships a Linux x86_64 build with a native GTK launcher, so the image is always `linux/amd64`. On ARM, Docker Desktop emulates it with Rosetta or QEMU. This is slower but gives the same results. If the build fails on a Mac, enable *Use Rosetta for x86_64/amd64 emulation* in Docker Desktop settings.
- **Java 21** is provided by the image (`eclipse-temurin:21-jre`). The tool does not start with Java 17 (`Unresolved requirement: osgi.ee ... version=21`).
- **No display:** the CLI is an Eclipse application and crashes on exit without an X display (`gtk_init_check() failed`). The image starts a virtual X server (Xvfb) for each run. `SWT SessionManagerDBus` warnings in the log are harmless.
- **Workspace:** the tool creates a `workspace/` folder at the repository root (ignored by Git).
- **Output order:** the order of entries in the result files can change between runs. The content does not.
- **Supported SQL dialects:** MySQL, Apache Impala, SQLite and MongoDB. **PostgreSQL is not supported**, so ADempiere is analysed with the MySQL dialect. This limitation must be considered when interpreting step 2 results.

## Contribution rules

- Never modify code inside `target/`: it is a read-only reference.
- Every generated artefact must come with the command or script that produces it, listed in [`REPRODUCE.md`](REPRODUCE.md).
- Do not commit database dumps containing real data.
- When an LLM is used, document the model, the prompts, and how its output was checked against the source code, in [`AI_USAGE.md`](AI_USAGE.md). Files written by an LLM also say so in their header.

## Course context

INFOM218 — *Software Evolution*, Prof. Anthony Cleve, University of Namur.
