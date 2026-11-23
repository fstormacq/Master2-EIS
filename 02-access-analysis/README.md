# Database access analysis

This README explains the results of step 2 and the conclusions we draw from them. The other READMEs of this folder describe the files and how to regenerate them; this one explains **why** we did each run and **what we learn** from it.

The goal of step 2 is to find **where and how the code accesses the 22 studied tables** ([`database-scope/studied-tables.txt`](../database-scope/studied-tables.txt)).

```
02-access-analysis/
|- sqlinspect-results/   # 2.1  database accesses found by SQLInspect            done
|- other-accesses/       # 2.2  accesses SQLInspect cannot see (ORM, Query API)  to do
|- statistics/           # 2.4  statistics on all the accesses                   to do
|- logical-subschema/    # 2.5  part of the logical schema actually used         to do
```

The structured inventory of step 2.3 (`accesses_sqlinspect.csv`, `accesses_other.csv`) will merge the results of 2.1 and 2.2.

## 2.1 SQLInspect analysis

### Approach

> *Section written with Claude Opus 5.5 (AI-generated), 23.11.2026; see [`AI_USAGE.md`](../AI_USAGE.md).*

We used [SQLInspect](https://bitbucket.org/csnagy/sqlinspect) (Nagy & Cleve, ICSE 2018), CLI version `0.4.2.v20241021-1301`. It statically analyses Java code: it looks for the places where SQL is executed (*hotspots*) and tries to rebuild the SQL string sent to the database (*queries*). The tool runs in a Docker image so that it behaves the same on every machine. The exact commands are in [`REPRODUCE.md`](../REPRODUCE.md#21-sqlinspect), and what each output file contains is explained in [`SQLINSPECT_OUTPUTS.md`](sqlinspect-results/SQLINSPECT_OUTPUTS.md).

Two options had to be chosen:

| Option | Value | Why |
|---|---|---|
| Hotspot finder | `JDBCHotspotFinder` only | ADempiere does not use JPA or Spring for data access. All SQL reaches the database through JDBC, wrapped by ADempiere's own `DB` class (`target/base/src/org/compiere/util/DB.java`) |
| SQL dialect | `MySQL` | SQLInspect supports MySQL, Apache Impala, SQLite and MongoDB, but **not PostgreSQL**, ADempiere's main database. MySQL is the closest supported dialect; PostgreSQL-specific syntax may not be parsed |

No schema was given to SQLInspect (`-schema`), because the physical schema of step 1.3 is not available yet. As a result, SQLInspect cannot map queries to tables and columns (`*-taa.xml` is empty). Instead, our script [`sqlinspect_summary.py`](../tools/sqlinspect/sqlinspect_summary.py) searches the rebuilt SQL for the names of the 22 tables.

### Two runs: why `asset`, then `base`

The first run was on the `org.adempiere.asset` module, which contains the fixed-asset code. This module was selected as the first run because of its small size and its relevance to our study. This analysis found 8 hotspots, all of which were marked as `{{na}}`. For example, `CalloutAsset.java:94-95` builds the SQL in a `String`, then calls `DB.prepareStatement(SQL, null)`. At first glance, it seemed that SQLInspect could not rebuild the SQL because it was passed to `DB.prepareStatement`, which is defined in the `base/` module and was not analysed in this run.

To test this hypothesis, we ran SQLInspect a second time on the `base/` module. This run found 620 hotspots, but 598 out of 633 queries were still marked as `{{na}}`. This refuted our initial hypothesis. To understand the actual cause, we examined the `DB.prepareStatement` method (`DB.java:742`). It returns ADempiere's own `CPreparedStatement` instead of a plain JDBC `PreparedStatement`. Our explanation is that SQLInspect only rebuilds the SQL when the string is passed directly to a JDBC method, such as `Connection.prepareStatement(sql)` or `Statement.executeQuery(sql)`. It loses track of the string when it goes through `DB.prepareStatement`. For example, in `SmjReportLogic.java:46-47`, inside `base/`, the SQL is built and passed to `DB.prepareStatement`, and the query is still `{{na}}`. The results support this explanation: in all 35 resolved queries, the SQL string is passed directly to JDBC, either to `conn.prepareStatement(sql)` (e.g. `MSequence.java:142`) or to `stmt.executeQuery(sql)`. The latter holds even when the `Statement` itself comes from the wrapper, as with `DB.createStatement()` in `MCountry.java:138-139`.

### Results

The Python script [`sqlinspect_summary.py`](../tools/sqlinspect/sqlinspect_summary.py) converts each run into a CSV with one line per query (`sqlinspect-results/filtered/asset-queries.csv` and `base-queries.csv`). In each CSV, the `tables_in_scope` column lists the studied tables named in the SQL. The script also writes a comparison table of the runs, [`summary.md`](sqlinspect-results/filtered/summary.md).

Our key finding is that **no query on the 22 studied tables was found in either run**. The 35 resolved queries are direct JDBC calls, mostly in infrastructure code (e.g., `MSequence`, with 17 queries for ID generation, `ReplicationLocal`, `ColumnEncryption`, `JdbcTest*`, `TestConnection`, `DB_PostgreSQL/MySQL/MariaDB`) and a few business classes outside our scope (e.g., `MCountry`, `MRegion`, `InventoryCountCreate`). None of them comes from fixed-asset code or names a studied table. The list of resolved queries can be found in `sqlinspect-results/filtered/base-queries.csv` (column `resolved = True`).

Three queries are partially resolved: the structure of the SQL is known but the table name is built at runtime, e.g. `PO_LOB.java:146` (`UPDATE {{na}} SET {{na}}={{question}} WHERE {{na}}`).

Each run has 4 hotspots in files of the fixed-asset list of step 1.1, all `{{na}}`: `CalloutAsset` (×2), `MDepreciationMethod` and `MDepreciationConvention` in `asset`; `CreateAdempiere` (×3) and `MIssueProject` in `base`. The latter only mention a studied table and are not fixed-asset business code.

### Limitations

> *Limitations identified with the help of Claude Opus 5.5 (23.11.2026), then checked against the code and the results; see [`AI_USAGE.md`](../AI_USAGE.md).*

After examining the results, we identified several limitations of SQLInspect that explain why it did not find any queries on the 22 studied tables. These limitations are:

1. **ORM accesses**: SQLInspect does not analyse Object-Relational Mapping (ORM) accesses, such as `MAsset`, `X_*` getters/setters, `saveEx()`, and `new MAsset(...)`. These are common ways to access the database in ADempiere, and they are not hotspots for SQLInspect.

2. **Query API**: SQLInspect does not analyse ADempiere's `Query` API, another common way to access the database, e.g. `new Query(ctx, I_A_Asset.Table_Name, whereClause, trxName)`. Only the WHERE clause is written in the calling code; the table is passed as a parameter and the full SQL is built at runtime inside the `Query` class.

3. **`DB.*` wrapper**: The `DB.*` wrapper hides the SQL string: SQLInspect cannot follow it back to the query, which leaves about 95 % of the queries of `base` (598 out of 633) as `{{na}}`.

4. **MySQL dialect**: We had to use the MySQL dialect, because SQLInspect does not support PostgreSQL. PostgreSQL-specific syntax may be parsed incorrectly. The impact is small here, since only 35 queries were resolved and parsed.

5. **No schema given**: SQLInspect was run without a schema, so it cannot map queries to tables and columns. This is because the physical schema of step 1.3 is not available yet.

6. **Limited analysis scope**: SQLInspect was only run on the `base/` and `org.adempiere.asset/` modules, and not on other modules such as `client/`, `zkwebui/`, or other custom modules.

7. **Static analysis only**: SQLInspect performs static analysis, so it cannot know SQL that is built from runtime values.

### Consequences for the next steps

As a consequence of these limitations, a custom analysis is needed to find the accesses to the 22 studied tables. This will be done in step 2.2, where we will write our own detection scripts for the missed cases. The results of this custom analysis will be merged with the SQLInspect results in step 2.3, and the final inventory will be used to generate statistics and a logical subschema in steps 2.4 and 2.5.

An improvement is planned: once the physical schema of step 1.3 is available, we will rerun SQLInspect with the `-schema` option, so that the resolved queries are mapped to tables and columns (`*-taa.xml`). This will not resolve the `{{na}}` queries.