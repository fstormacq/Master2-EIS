# raw

Unmodified SQLInspect output. Nothing in this folder is edited by hand.

## adempiere-asset-*

Analysis of the ADempiere fixed assets module (`target/org.adempiere.asset`).

Regenerate from the repository root (requires Docker, see the main [README](../../../README.md#third-party-tools)):

```bash
./tools/run_sqlinspect_asset.sh
```

Command run inside the container (see [`tools/run_sqlinspect_asset.sh`](../../../tools/run_sqlinspect_asset.sh)):

```bash
sqlinspect -projectname adempiere-asset \
  -projectdir target/org.adempiere.asset \
  -hotspotfinder JDBCHotspotFinder \
  -dialect MySQL \
  -outdir 02-access-analysis/sqlinspect-results/raw
```

| | |
|---|---|
| SQLInspect | `0.4.2.v20241021-1301` (Docker image `master2-eis/sqlinspect:0.4.2`) |
| ADempiere | `4ae098f` |
| Result | 8 hotspots, 8 queries (JDBC only) |

Notes:

- File paths start with `/repo/`, the mount point of the repository in the container.
- The order of entries can change between runs. The content does not.
- `*.SQLInspect.stats` holds timings and memory usage, so it changes on every run.
- The full log is written to `adempiere-asset.log` (ignored by Git).
