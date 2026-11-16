# ADempiere Fixed Assets — Database Reverse Engineering

Reverse engineering and quality assessment of the **fixed assets** database of [ADempiere](https://github.com/adempiere/adempiere), an open-source Java ERP. We recover the schema, map how the code accesses it, assess the impact of schema changes and evaluate the overall quality.

Group project for **INFOM218 — Software Evolution**, University of Namur (2026–2027), Group 4.

## At a glance

| | |
|---|---|
| **System studied** | ADempiere, `develop` branch, commit [`4ae098f`](https://github.com/adempiere/adempiere/commit/4ae098fd18065f1a658ff56de3b90e63aabfecb2) |
| **Scope** | Fixed assets functional area: 22 tables, validated by the teaching team on 2 Nov 2026 |
| **Database** | PostgreSQL |
| **Status** | In progress. See [`ROADMAP.md`](ROADMAP.md) for detailed progress |
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

The 22 tables cover the full lifecycle of a fixed asset, from acquisition to depreciation and disposal. The list is kept in [`subset/tables.txt`](subset/tables.txt).

| Sub-domain | Tables |
|---|---|
| Asset and classification | `A_ASSET`, `A_ASSET_GROUP`, `A_ASSET_CLASS`, `A_ASSET_TYPE`, `A_ASSET_PRODUCT` |
| Information records | `A_ASSET_INFO_FIN`, `A_ASSET_INFO_INS`, `A_ASSET_INFO_LIC`, `A_ASSET_INFO_OTH`, `A_ASSET_INFO_TAX` |
| Asset movements | `A_ASSET_ADDITION`, `A_ASSET_DELIVERY`, `A_ASSET_DISPOSED`, `A_ASSET_SPLIT`, `A_ASSET_CHANGE` |
| Accounting | `A_ASSET_ACCT`, `A_ASSET_GROUP_ACCT` |
| Depreciation | `A_DEPRECIATION`, `A_DEPRECIATION_WORKFILE`, `A_DEPRECIATION_EXP`, `A_DEPRECIATION_METHOD`, `A_DEPRECIATION_CONVENTION` |

## Repository layout

```
ROADMAP.md        project plan and progress tracking
subset/           list of the studied tables
tools/            scripts used to produce every result
step1-schemas/    PS, LS, CS and foreign key analysis
step2-accesses/   database access inventories, statistics, used subschema
step3-whatif/     schema evolution scenarios and impact analysis
step4-quality/    quality assessment and recommendations
bonus-versions/   cross-version analysis
report/           final report and slides
target/           ADempiere source code (Git submodule, read-only)
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

Requirements depend on the step. Each folder's README lists its own (Python 3, Java for SQLInspect, …).

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

## Contribution rules

- Never modify code inside `target/`: it is a read-only reference.
- Every generated artefact must come with the command or script that produces it.
- Do not commit database dumps containing real data.
- When an LLM is used, document the model, the prompts, and how its output was checked against the source code.

## Course context

INFOM218 — *Software Evolution*, Prof. Anthony Cleve, University of Namur.
