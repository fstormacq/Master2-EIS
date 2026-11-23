# raw

Unmodified SQLInspect output. Nothing in this folder is edited by hand. One subfolder per run:

| Run | Analysed code | Script | Result |
|---|---|---|---|
| [`asset/`](asset/) | `target/org.adempiere.asset` (fixed assets module) | [`tools/sqlinspect/run_sqlinspect_asset.sh`](../../../tools/sqlinspect/run_sqlinspect_asset.sh) | 8 hotspots, 8 queries |
| [`base/`](base/) | `target/base` (ADempiere core: `DB` helper, generated `X_*`/`I_*` classes) | [`tools/sqlinspect/run_sqlinspect_base.sh`](../../../tools/sqlinspect/run_sqlinspect_base.sh) | 620 hotspots, 633 queries |

What each generated file contains: see [`SQLINSPECT_OUTPUTS.md`](../SQLINSPECT_OUTPUTS.md). The comparison of the runs is in [`../filtered/summary.md`](../filtered/summary.md).

Regenerate from the repository root (requires Docker, see the main [README](../../../README.md#third-party-tools)):

```bash
./tools/sqlinspect/run_sqlinspect_asset.sh
./tools/sqlinspect/run_sqlinspect_base.sh
```

Command run inside the container, with `<run>` = `asset` or `base`:

```bash
sqlinspect -projectname adempiere-<run> \
  -projectdir <target/org.adempiere.asset | target/base> \
  -hotspotfinder JDBCHotspotFinder \
  -dialect MySQL \
  -outdir 02-access-analysis/sqlinspect-results/raw/<run>
```

| | |
|---|---|
| SQLInspect | `0.4.2.v20241021-1301` (Docker image `master2-eis/sqlinspect:0.4.2`) |
| ADempiere | `4ae098f` |
| Hotspot finder | JDBC only (ADempiere does not use JPA or Spring for data access) |

Notes:

- File paths start with `/repo/`, the mount point of the repository in the container.
- The order of entries can change between runs. The content does not.
- `*-SQLInspect.stats` holds timings and memory usage, so it changes on every run.
- Each run also writes `adempiere-<run>.log` (ignored by Git).
