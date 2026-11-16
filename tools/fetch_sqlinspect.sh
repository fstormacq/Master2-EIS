#!/usr/bin/env bash
# Download the SQLInspect CLI (fixed version) into tools/sqlinspect/
# Author: Claude Opus 5.5

set -euo pipefail
VERSION="0.4.2.v20241021-1301"
FILE="sqlinspect.product-${VERSION}-linux.gtk.x86_64.tar.gz"
URL="https://bitbucket.org/csnagy/sqlinspect/downloads/${FILE}"
DEST="$(cd "$(dirname "$0")" && pwd)/sqlinspect"

mkdir -p "$DEST"
cd "$DEST"
[ -f "$FILE" ] || curl -L -o "$FILE" "$URL"
SHA256="f91d8c1bfab0d5800d4c0b5d8f1b6dfe75a5044cc184dee499ced96531753c9c"
echo "${SHA256}  ${FILE}" | sha256sum -c --quiet

# The archive was built with bsdtar (macOS): skip its unknown header keywords
tar --warning=no-unknown-keyword -xzf "$FILE"

# Silence the Eclipse E4 javax-annotation warning (harmless for the CLI)
# (JVM options must come after a -vmargs line in the Eclipse launcher .ini)
grep -q 'eclipse.e4.inject.javax.warning' sqlinspect.ini \
  || printf -- '-vmargs\n-Declipse.e4.inject.javax.warning=false\n' >> sqlinspect.ini

./sqlinspect -help 2>/dev/null