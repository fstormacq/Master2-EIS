# filtered

SQLInspect results reshaped for analysis. Generated, do not edit by hand.

| File | Content |
|---|---|
| `<run>-queries.csv` | One line per query of the run: `run, id, file, line, class, method, exec_string, resolved, operation, tables_in_scope, sql`. Sorted by file and line. `tables_in_scope` lists the studied tables named in the SQL |
| [`summary.md`](summary.md) | Comparison table of all the runs |

Regenerate from the repository root, after the SQLInspect runs (see [`../raw/`](../raw/)):

```bash
uv run tools/sqlinspect/sqlinspect_summary.py
```

**No query touches the 22 studied tables** in any run (`tables_in_scope` is always empty). Most queries are `{{na}}`: ADempiere sends its SQL through `DB.prepareStatement`, whose result SQLInspect cannot follow back to the SQL string. See [`SQLINSPECT_OUTPUTS.md`](../SQLINSPECT_OUTPUTS.md#things-to-keep-in-mind). Accesses to the studied tables are therefore covered in step 2.2 ([`../../other-accesses/`](../../other-accesses/)).
