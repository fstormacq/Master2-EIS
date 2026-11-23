#!/usr/bin/env bash
# Step 2.1: run SQLInspect on the ADempiere asset module (org.adempiere.asset).
# Output: 02-access-analysis/sqlinspect-results/raw/asset/adempiere-asset-*
#
# - JDBC hotspots only (ADempiere does not use JPA/Spring for data access)
# - MySQL dialect: PostgreSQL is not supported by SQLInspect
# File paths in the results are container paths (/repo/target/...), so they do
# not depend on where the repository is cloned.
# Author: Claude Opus 5.5

set -euo pipefail
cd "$(dirname "$0")/../.."

OUT="02-access-analysis/sqlinspect-results/raw/asset"
mkdir -p "$OUT"

./tools/sqlinspect/sqlinspect.sh \
  -projectname adempiere-asset \
  -projectdir target/org.adempiere.asset \
  -hotspotfinder JDBCHotspotFinder \
  -dialect MySQL \
  -outdir "$OUT" \
  2>&1 | tee "$OUT/adempiere-asset.log"
