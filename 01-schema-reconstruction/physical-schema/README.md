# physical-schema



## Source of the physical schema

The commands behind every figure of this section are listed in [`REPRODUCE.md`](../../REPRODUCE.md#12-source-of-the-physical-schema), section 1.2.

### Choice: the PostgreSQL seed dump

The physical schema is extracted from the PostgreSQL seed dump shipped with ADempiere, `target/data/seed/Adempiere_pg.jar`. The jar contains a single entry, `Adempiere_pg.dmp`, dated 2023-01-17. It is a plain-SQL dump (not a `pg_restore` archive) produced by `pg_dump` 15.1, with all objects in the schema `adempiere`. Inside the dump, `AD_System` gives `Version = 2023-01-24` and `ReleaseNo = 3.9.4`.

We chose this source because it is the database actually created by an ADempiere installation: restoring it gives a real PostgreSQL catalogue, from which columns, keys, constraints and indexes can be read without interpretation. We then had to check that it is still up to date at the analysed commit `4ae098f`, that is, that no later migration changes one of our 22 tables.

### No migration has to be applied on top of the dump

**Date of the dump in the Git history.** The Git blob of the jar is `c55e6e08` at tag `3.9.4` (2023-01-24), at tag `3.9.4.001` (2023-12-11) and at `4ae098f` (2026-10-25). It was `c1d8d097` in November 2022. The jar was therefore replaced for release 3.9.4 and has not changed since. We compared blob hashes instead of reading `git log`: the submodule is a shallow clone, and `git log` attributes files to the commits at the edge of the fetched history, which gives wrong dates.

**Migrations added after the dump.** Two independent methods give the same 18 files:

- *Git:* between tag `3.9.4` and `4ae098f`, `migration/` gains 18 XML files, all in `migration/394lts-3.9.4.001/` (`09910_…` to `10320_…`), and 2 build files are modified (`build.gradle`, `build.properties`), which do not touch the schema.
- *Dump:* the dump records the migrations already applied in `adempiere.ad_migration`. Their highest `SeqNo` is 9900 (*Synchronize DB version and date version on seed with code*, release 3.9.4). Among the 978 XML files of `migration/`, exactly 18 have a higher `SeqNo` (9910 to 10320), and they are the 18 files of `394lts-3.9.4.001/`.

The second method does not depend on the Git history and shows that every migration older than the dump is already applied in it.

**None of the 18 files touches our tables.** An XML migration changes the application dictionary record by record, and can change a table without naming it. A new column is an `AD_Column` record that only holds the numeric ID of its table (`<Data Column="AD_Table_ID">53137</Data>`). An update of an existing column (`<PO Table="AD_Column" Action="U" Record_ID="56816">`) only holds the ID of the column. A search by table name is therefore not enough. We parsed each file as XML ([`tools/physical_schema/scan_migrations.py`](../../tools/physical_schema/scan_migrations.py)) and searched for:

1. one of the 22 `AD_Table_ID` values in an `AD_Table_ID` field, with the type of the record that holds it;
2. a record of `AD_Table` itself with one of these IDs;
3. the name of one of the 22 tables as a whole word, in any text or attribute, including SQL steps;
4. a record of `AD_Column` whose ID is one of the 710 columns of our tables in the dump.

All 18 files give 0 hits. Two positive controls show that the search works:

- On `M_RequisitionLine`, it finds the 2 changes of `09930_4179_AddingBusinessPartnerLocationRequisitionLine.xml`: a new column (rule 1) and an update of the existing column `C_BPartner_ID` (rule 4), which rules 1 to 3 alone did not detect.
- On `HR_Employee`, it finds the 2 files that modify it, by name.

Two limits remain, and neither changes the result:

- Rule 4 only knows the columns that exist in the dump. An update of a column created by a migration (in `09930_4179`, the length of the new column goes from 22 to 10) is not detected, but the creation of that column is, in the same file.
- Rule 1 also matches references that are not schema changes. For example, `AD_Table_ID=466` (`AD_TabCustom`) appears in an `AD_Ref_Table` record of `09930_Add_process_for_Copy_ASP_Window.xml`, which is a reference list, not a new column. This is why the script prints the type of the record. For our tables, there is no such match to sort.

A plain `grep` on the IDs would have given false positives: `539`, the ID of `A_Asset`, matches 6 times in `09970_Add_Import_Requisition.xml`, always in the milliseconds of a timestamp (`2021-10-29 09:27:25.539`).

### Columns of the Java interfaces that are not in the database

The generated interfaces `I_<Table>.java` define one `COLUMNNAME_*` constant per column of the application dictionary (`AD_Column`). Over the 22 tables, they define 710 columns, the same number as the `AD_Column` records of these tables in the dump, and the restored database contains 704 physical columns. The 6 missing columns are:

| Table | Columns |
|---|---|
| `A_ASSET_ADDITION` | `A_Life_Period_Min`, `A_Life_Period_Max` |
| `A_DEPRECIATION_WORKFILE` | `A_Expense_SL`, `A_Expense_SL_F`, `A_Life_Period_Min`, `A_Life_Period_Max` |

All 6 are **virtual columns**: their `AD_Column.ColumnSQL` is not NULL. The application evaluates this SQL expression when it reads the record (for example, `A_Life_Period_Max` is a sub-query on `A_Asset` and `A_Asset_Class`), and the column has no physical existence. They are defined in `migration/370lts-380lts/postgresql/979_FA_Stabilization.sql`. In the restored database, they are the only columns of our 22 tables with a non-NULL `ColumnSQL`, and none of them exists in `information_schema.columns`. The other direction is empty: every physical column has a constant in the interfaces.

They belong to the logical schema (section 1.5), not to the physical one, and are therefore left out of the PS.

### Discrepancy between migration scripts

Migration 979 declares **8** virtual columns on our tables, not 6. The two extra ones are `Processed` in `A_ASSET_INFO_FIN` (`AD_Column_ID` 59319) and in `A_ASSET_INFO_LIC` (59320), with `ColumnSQL = 'N'`, a constant. The next migration, `980_armen_fix_dictionary.sql` (lines 62 and 70), sets their `ColumnSQL` back to NULL, and an `ALTER TABLE … ADD COLUMN Processed CHAR(1) DEFAULT 'N'` (lines 66 and 74) makes them physical. The dump agrees with 980: both columns exist in the database.

So reading a single migration file is not enough to know the state of a column, because a later script can undo it. This is one more reason to extract the PS from the restored database rather than from the migration scripts. It is also an observation for the quality assessment (step 4): the dictionary went through an inconsistent state between two consecutive migrations.

### Pitfalls met while restoring the dump

- `unzip -p Adempiere_pg.jar` without an entry name also writes `META-INF/MANIFEST.MF` in front of the dump, and the restore fails on its first statement (`syntax error at or near "Manifest"`). Always use `unzip -p Adempiere_pg.jar Adempiere_pg.dmp`.
- The dump grants rights to a role `adempiere`, which must be created before the restore.
- The dump is plain SQL: restore it with `psql -f`, not `pg_restore`.
