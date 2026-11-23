#!/usr/bin/env bash
# Run the SQLInspect CLI inside Docker (works on Linux, macOS and Windows/WSL,
# x86_64 and ARM). All arguments are passed to SQLInspect unchanged.
#
# The repository root is mounted at /repo and used as working directory, so
# paths relative to the repository root work as-is, e.g.:
#   ./tools/sqlinspect/sqlinspect.sh -help
#   ./tools/sqlinspect/sqlinspect.sh -projectdir target/org.adempiere.asset -outdir out/ ...
#
# Set SQLINSPECT_REBUILD=1 to force a rebuild of the image.
# Author: Claude Opus 5.5

set -euo pipefail

IMAGE="master2-eis/sqlinspect:0.4.2"
PLATFORM="linux/amd64"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if ! command -v docker >/dev/null 2>&1; then
  echo "error: docker not found. Install Docker Desktop (macOS/Windows) or Docker Engine (Linux)." >&2
  exit 1
fi

if [ "${SQLINSPECT_REBUILD:-0}" = "1" ] || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Building $IMAGE (first run only, may take a few minutes)..." >&2
  docker build --platform "$PLATFORM" -t "$IMAGE" "$REPO_ROOT/docker/sqlinspect" >&2
fi

# Allocate a TTY only when attached to a terminal
TTY_FLAG=""
[ -t 0 ] && [ -t 1 ] && TTY_FLAG="-t"

# Run as the host user so generated files are not owned by root on Linux
exec docker run --rm -i $TTY_FLAG --init \
  --platform "$PLATFORM" \
  --user "$(id -u):$(id -g)" \
  -v "$REPO_ROOT:/repo" \
  -w /repo \
  "$IMAGE" "$@"
