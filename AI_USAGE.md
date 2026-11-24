# AI usage

This file lists every use of an AI model in this project: the model, the date, the prompt, what was produced and how it was checked against the source code or the raw results.

Files written by an AI also say so in their header (`Author: Claude Opus 5.5 (AI-generated), <date>`).

## 1.2 Source of the physical schema

### Check that no migration has to be applied on top of the seed dump

| | |
|---|---|
| Model | Claude Opus 5.5 (Claude Code) |
| Date | 24.11.2026 |
| Output | The checks of [`REPRODUCE.md`](REPRODUCE.md#12-source-of-the-physical-schema), section 1.2 (commands and expected results), the script [`tools/physical_schema/scan_migrations.py`](tools/physical_schema/scan_migrations.py) (search of the post-dump XML migrations, step (c); header `Author: Claude Opus 5.5`), and the section *Source of the physical schema* of [`01-schema-reconstruction/physical-schema/README.md`](01-schema-reconstruction/physical-schema/README.md). No result file was produced. |
| Check | Every command of `REPRODUCE.md` section 1.2 re-run, and its output compared with the expected results. Line numbers and IDs quoted in the README (`979_FA_Stabilization.sql`, `980_armen_fix_dictionary.sql` lines 62, 66, 70 and 74, `AD_Column_ID` 59319 and 59320) opened in `target/`. False positive of the plain `grep` (`539` in `09970_Add_Import_Requisition.xml`) checked by hand. `scan_migrations.py` reviewed by the group (see *Review of `scan_migrations.py`* below), then run on the 22 tables (highest `SeqNo` 9900, 0 hits in 18 files) and on two positive controls, `M_RequisitionLine` (2 matches, by `AD_Table_ID` and `AD_Column_ID`) and `HR_Employee` (2 files, by name), with the matches checked in the XML files. The error cases (XML file that cannot be parsed, selection different from `394lts-3.9.4.001/`, comment at the end of a line in the table list) tested on a modified copy of the migrations. |

**Why we used an AI for this step.** The check means reading a lot of material for a yes/no answer: a 260 MB SQL dump, 978 XML migration files, 18 of them applied after the dump (14,367 lines for `09970_Add_Import_Requisition.xml` alone), a 40,000-line migration script (`979_FA_Stabilization.sql`), and 22 Java interfaces with 710 column constants. Reading them by hand was not realistic, and simple text searches are unreliable here: an XML migration can refer to a table only through its numeric `AD_Table_ID`, and a search for these numbers matches unrelated values such as timestamps. We used the model to write and run targeted searches (XML parsing instead of `grep`, positive controls, comparison with the restored database catalogue), so that we only had to read the relevant lines and could rule out false positives.

**Review.** We reviewed this work closely, and the model was told not to modify any file without our agreement. The review changed the result: the hypothesis in our prompt said 6 virtual columns, defined in migration 979. The model found 8 in that migration and showed that 2 of them are made physical again by migration 980. We checked this in both files before accepting it. The model also corrected its own first commands: `git log` is unreliable on the shallow submodule (replaced by a comparison of blob hashes), `unzip -p` without an entry name corrupts the dump, and a first version of the command that lists virtual columns returned nothing because `INSERT` statements are positional.

Prompt (original, in French; the context and part 1 of a two-part prompt. Part 2, the extraction pipeline, is documented in its own entry):

```md
Contexte : projet universitaire INFOM218 (reverse engineering de base de données).
Repo `Master2-EIS`, avec ADempiere en submodule figé sur le commit `4ae098f`.
Sous-ensemble : 22 tables de la gestion des immobilisations, listées dans
`database-scope/studied-tables.txt`.

IMPORTANT : je veux écrire le code moi-même. Tu peux lire le repo, lancer des
commandes de vérification et me montrer de petits extraits (<=15 lignes) pour
illustrer un point. Tu n'écris PAS le script complet et tu ne modifies aucun
fichier sans que je le demande. Avance étape par étape et attends ma validation
avant de passer à la suivante.

## Partie 1 : vérifier que les migrations ne sont pas nécessaires

Hypothèse à confirmer ou réfuter, preuves à l'appui :
- La source du schéma physique (PS) est le dump PostgreSQL
  `data/seed/Adempiere_pg.jar` (pg_dump 15.1 en SQL texte, schéma `adempiere`,
  daté de janvier 2023).
- Les seules migrations postérieures au dump sont des XML dans
  `migration/394lts-3.9.4.001/`, et aucune ne touche nos 22 tables.
- 6 colonnes présentes dans les interfaces `I_*.java` mais absentes du dump
  (2 dans `A_ASSET_ADDITION`, 4 dans `A_DEPRECIATION_WORKFILE`) sont des
  colonnes virtuelles : `AD_Column.ColumnSQL` non NULL. Elles sont définies dans
  `migration/370lts-380lts/postgresql/979_FA_Stabilization.sql`.

Vérifie :
1. Avec `git log`, la date du dernier changement du jar seed, et tous les
   fichiers de `migration/` ajoutés ou modifiés depuis.
2. Pour chacun de ces fichiers, s'il touche une de nos tables. Teste par le
   nom de table ET par l'`AD_Table_ID`, car une migration XML de type AD ajoute
   une colonne via un enregistrement `AD_Column` qui ne contient que l'ID de la
   table. Méfie-toi des faux positifs (ex. `AD_Column_ID="53265"` qui matche un
   motif numérique).
3. Que les 6 colonnes ont bien un `ColumnSQL`, d'abord dans la migration 979,
   puis dans la base restaurée.
4. Donne-moi les commandes exactes pour que je puisse tout refaire, ainsi qu'un
   paragraphe pour `01-schema-reconstruction/physical-schema/README.md` qui justifie le choix de la
   source.

Si quelque chose contredit l'hypothèse, arrête-toi et explique-le.
```

The model stopped once, because `git log` cannot date a file in the shallow submodule, and proposed three ways to get the history. We chose to fetch the history since October 2022 (`git fetch --shallow-since=2022-10-01`, now the first command of `REPRODUCE.md` section 1.2). 

**Review of `scan_migrations.py`.** The group reviewed the script. The conclusion was right (0 of 18 files touch our tables), but the review found gaps in the method, which the model then corrected in a targeted way, without rewriting the script:

- *Blind spot.* An update of an existing column (`<PO Table="AD_Column" Action="U" Record_ID="…">`) holds neither the name nor the ID of its table, and was not detected. Rule 4 now maps every `AD_Column_ID` of the dump to its table.
- *Unjustified scope.* The directory `394lts-3.9.4.001/` was hard-coded. The scope is now deduced: highest `SeqNo` of `adempiere.ad_migration` in the dump (9900), then every `migration/**/*.xml` with a higher `SeqNo`, checked against that directory.
- *Minor points.* Comments at the end of a line in the table list are ignored. The number of matches counts distinct matches, so it agrees with the list printed. A file that cannot be parsed is reported instead of stopping the script. Rule 1 prints the type of the record that holds the `AD_Table_ID`.

While applying the review, the model checked its expectations against the files and corrected one of them. The review expected the 2 matches for `M_RequisitionLine` to be the creation of column 100917 and the update of its `FieldLength`. In fact, column 100917 is created by the migration and is not in the dump, so rule 4 cannot map its update. The second match is the update of the existing column 56816 (`C_BPartner_ID`). This limit is documented in the script, in `REPRODUCE.md` and in the README. The model also replaced the positive control `AD_TabCustom`: the new message of rule 1 showed that its match was a reference list (`AD_Ref_Table`), not a schema change.

## 2.1 SQLInspect analysis

### Python script `tools/sqlinspect/sqlinspect_summary.py`

| | |
|---|---|
| Model | Claude Opus 5.5 (Claude Code) |
| Date | 23.11.2026 |
| Output | [`tools/sqlinspect/sqlinspect_summary.py`](tools/sqlinspect/sqlinspect_summary.py) |
| Check | Figures compared with `*-Model.stats` and `*-javametrics.xml` of each run (hotspots, queries, SELECT/UPDATE counts) and with `grep` on `*-queries.xml`. Edge cases inspected by hand: 3 partially resolved queries, 1 empty query. |

Prompt:

```md
Generate a Python script to analyse one or more raw SQLInspect runs, producing one CSV file per run, as well as a comprehensive comparative summary table.

- **Input:** One or more directories under `raw/<run>`.
- **One CSV per run:** `filtered/<run>-queries.csv`, containing the following columns: `run`, `id`, `file`, `line`, `class`, `method`, `exec_string`, `resolved`, `operation`, `tables_in_scope`, `sql`. Each row represents one query.
- **Comparative Markdown summary:** `filtered/summary.md`, containing a comprehensive comparison across all runs, including:
  - Hotspots.
  - Total number of queries.
  - Number of `{{na}}` entries.
  - Number of resolved queries, broken down by operation.
  - Number of queries involving the 22 target tables.
  - Hotspots in files related to fixed assets (based on the list from section 1.1).
  - Run duration.
```

### Note `02-access-analysis/sqlinspect-results/SQLINSPECT_OUTPUTS.md`

| | |
|---|---|
| Model | Claude Opus 5.5 (Claude Code) |
| Date | 23.11.2026 |
| Output | [`SQLINSPECT_OUTPUTS.md`](02-access-analysis/sqlinspect-results/SQLINSPECT_OUTPUTS.md): description of each file generated by SQLInspect |
| Check | Each file description compared with the actual files in `raw/asset/` and `raw/base/`. The explanation of `{{na}}` was checked in `target/base/src/org/compiere/util/DB.java:742` and `target/base/src/org/adempiere/excel/SmjReportLogic.java:46-47`. |

Prompt (translated from French): *"Add a markdown note that explains what SQLInspect generates"*

### Wrapper scripts `tools/sqlinspect/sqlinspect.sh` and `tools/sqlinspect/run_sqlinspect_asset.sh`

Written with Claude Opus 5.5 (header `Author: Claude Opus 5.5`). Checked by running the full chain on Linux on 23.11.2026 (`REPRODUCE.md`, "Full re-run"): the results were identical to the previous runs, except for the timings.

### Section "2.1 SQLInspect analysis > Approach" of `02-access-analysis/README.md`

| | |
|---|---|
| Model | Claude Opus 5.5 (Claude Code) |
| Date | 23.11.2026 |
| Output | Section *Approach* of [`02-access-analysis/README.md`](02-access-analysis/README.md), and the TODO outline of the following sections (the text of those sections is written by the group) |
| Check | Options compared with `tools/sqlinspect/run_sqlinspect_*.sh` and `./tools/sqlinspect/sqlinspect.sh -help` (supported dialects). File and line references checked in `target/`. |

Prompt (translated from French): *"Check section 1 and add section 2. Prepare sections 3, 4, 5 and 6, which I will write and you will review."*

### Section "Limitations" and review of `02-access-analysis/README.md`

| | |
|---|---|
| Model | Claude Opus 5.5 (Claude Code) |
| Date | 23.11.2026 |
| Output | List of limitations of SQLInspect (section *Limitations*), then a review of the sections written by the group, with factual and language corrections applied |
| Check | Each limitation checked against the code (`DB.java:742`, `Query` API usage) and the results (`filtered/summary.md`). The explanation of `{{na}}` was checked on all 35 resolved queries: each one passes its SQL string directly to a JDBC method (`conn.prepareStatement(sql)` or `stmt.executeQuery(sql)`). |

Prompts (translated from French): no prompt were given, but the model provided the text limitations based on the results and the ADempiere codebase.
