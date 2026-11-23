# What SQLInspect generates

> **Author:** Claude Opus 5.5 (AI-generated), 23.11.2026.
> Written from the outputs in [`raw/asset/`](raw/asset/) and [`raw/base/`](raw/base/) (SQLInspect `0.4.2.v20241021-1301`, ADempiere `4ae098f`). Checked by hand against those files.

This note explains the files that SQLInspect writes for each run, and which of them matter for this project.

## Key terms

- **Hotspot**: a place in the Java code that executes SQL, e.g. `pstmt.executeQuery()`. SQLInspect finds hotspots by looking for calls to the JDBC API (`-hotspotfinder JDBCHotspotFinder`).
- **Query**: the SQL text that SQLInspect tries to rebuild for a hotspot, by following how the string reaches the JDBC call. A hotspot can have several queries when the SQL depends on a branch (`if`). When the text cannot be rebuilt, the query value is `{{na}}` (*not available*).

## Output files

Each run writes 9 files to the output directory, prefixed with the project name (`-projectname`), e.g. `adempiere-base-*`. A log (`*.log`) is also written by our wrapper scripts.

| File | Content | Use in this project |
|---|---|---|
| **`*-queries.xml`** | **Main result.** One `<Query>` per query found: file (`ExecFile`), line (`ExecLine`), package and class, the JDBC call (`ExecString`), the call chain (`CallStack`) and the rebuilt SQL (`Value`, or `{{na}}`) | Basis of the access inventory (steps 2.1, 2.3) |
| **`*-Model.stats`** | One-line summary: number of hotspots and queries, average and maximum queries per hotspot | Headline figures |
| **`*-javametrics.xml`** | Same figures broken down by package, file and class, plus counts of `SELECT`, `INSERT`, `UPDATE` and `DELETE` | Distribution of accesses in the code (step 2.4) |
| `*-sqlmetrics.xml` | For each resolved query: number of fields, number of nested queries, nesting level | Query complexity (step 2.4) |
| `*-sqlsmells.xml` | SQL anti-patterns found in resolved queries, e.g. `IMPLICIT_COLUMNS` for `SELECT *` | Quality assessment (step 4) |
| `*-taa.xml` | Table and column accesses per statement (*Table Access Analysis*). **Empty here**: SQLInspect needs a schema (`-schema <file.sql>`) to map queries to tables | Usable once the physical schema (step 1.3) is available |
| `*-schema.xml` | Schema given with `-schema` or inferred with `-inferschema on`. Empty here | Not used |
| `*-SQLInspect.stats` | Time (ms) and memory (bytes) per analysis phase (`HOTSPOTS`, `QUERIES`, …, `ALL`). Changes on every run | Only to report run time |
| `*-androidsmells.xml` | Android-specific smells. Always empty for ADempiere | Not used |

### Example entry of `*-queries.xml`

```xml
<Query id="1">
  <Value>{{na}}</Value>                                  <!-- rebuilt SQL, here not available -->
  <HotspotFinder>JDBCHotspotFinder</HotspotFinder>
  <ExecPackage>org.compiere.asset.controller</ExecPackage>
  <ExecClass>CalloutAsset</ExecClass>
  <ExecFile>/repo/target/org.adempiere.asset/src/main/java/base/org/compiere/asset/controller/CalloutAsset.java</ExecFile>
  <ExecLine>95</ExecLine>                                <!-- line of the JDBC call -->
  <ExecString>pstmt.executeQuery()</ExecString>          <!-- the JDBC call itself -->
  <CallStack>
    <Call method="...CalloutAsset.tablePeriod(...)" methodLine="65" callLine="95"/>
  </CallStack>
</Query>
```

Paths start with `/repo/` because SQLInspect runs in Docker with the repository mounted at `/repo` (see [`tools/sqlinspect/sqlinspect.sh`](../../tools/sqlinspect/sqlinspect.sh)).

## Useful commands

Run from the repository root, with `<run>` = `asset` or `base`:

```bash
cat  02-access-analysis/sqlinspect-results/raw/<run>/*-Model.stats                 # hotspots and queries
grep -c "<Query "  02-access-analysis/sqlinspect-results/raw/<run>/*-queries.xml  # number of queries
grep -c "{{na}}"   02-access-analysis/sqlinspect-results/raw/<run>/*-queries.xml  # queries without SQL text
```

## Things to keep in mind

- **The order of entries changes between runs.** The content does not. Compare results with sorted or parsed data, not with a raw `diff`.
- **Dialect:** SQLInspect does not support PostgreSQL, so queries are parsed with the MySQL dialect. PostgreSQL-specific syntax may not be parsed.
- **`{{na}}` is very frequent on ADempiere.** Most SQL goes through `DB.prepareStatement(sql, trxName)` (`target/base/src/org/compiere/util/DB.java:742`), which returns an ADempiere `CPreparedStatement` instead of a plain JDBC `PreparedStatement`. SQLInspect only rebuilds the SQL that it sees passed to `Connection.prepareStatement(sql)`. So it finds the hotspot but not the query text, even when `base/` is part of the analysis.
- **Accesses through the ORM (`PO`, `X_*` classes) and the `Query` API are not hotspots** for SQLInspect. They are covered by step 2.2 ([`../other-accesses/`](../other-accesses/)).
