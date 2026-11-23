#!/usr/bin/env bash
# Step 2.1: run SQLInspect on the ADempiere core module (target/base).
# Output: 02-access-analysis/sqlinspect-results/raw/base/adempiere-base-*
#
# Same options as run_sqlinspect_asset.sh. base/ is analysed because most
# ADempiere SQL goes through the DB helper class (org.compiere.util.DB) and
# the generated X_*/I_* model classes, which live in base/, not in the asset
# module. Takes about 35 s and 1 GB of memory.

set -euo pipefail
cd "$(dirname "$0")/../.."

OUT="02-access-analysis/sqlinspect-results/raw/base"
mkdir -p "$OUT"

./tools/sqlinspect/sqlinspect.sh \
  -projectname adempiere-base \
  -projectdir target/base \
  -hotspotfinder JDBCHotspotFinder \
  -dialect MySQL \
  -outdir "$OUT" \
  2>&1 | tee "$OUT/adempiere-base.log"
