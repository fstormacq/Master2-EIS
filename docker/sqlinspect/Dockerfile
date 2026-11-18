# SQLInspect CLI in a portable container.
# SQLInspect only ships a Linux x86_64 build (native GTK/SWT launcher), so the
# final image is always linux/amd64. On ARM hosts (Apple Silicon), Docker runs
# it through emulation (Rosetta or QEMU): slower, but identical results.

ARG SQLINSPECT_VERSION=0.4.2.v20241021-1301
ARG SQLINSPECT_SHA256=f91d8c1bfab0d5800d4c0b5d8f1b6dfe75a5044cc184dee499ced96531753c9c

# --- Stage 1: download, verify and extract on the host's native platform ---
# Done natively (no emulation) so it is fast and reliable on ARM hosts too.
# One RUN per step, so a failure points to the exact step.
FROM --platform=$BUILDPLATFORM debian:bookworm-slim AS fetch
ARG SQLINSPECT_VERSION
ARG SQLINSPECT_SHA256
ENV ARCHIVE=sqlinspect.product-${SQLINSPECT_VERSION}-linux.gtk.x86_64.tar.gz

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /fetch
RUN curl -fSL --retry 3 -o "$ARCHIVE" \
      "https://bitbucket.org/csnagy/sqlinspect/downloads/$ARCHIVE" \
 && ls -l "$ARCHIVE"

RUN echo "$SQLINSPECT_SHA256  $ARCHIVE" | sha256sum -c - \
 || { echo "Checksum mismatch, got: $(sha256sum "$ARCHIVE")"; exit 1; }

# The archive was built with bsdtar (macOS): skip its unknown header keywords
RUN mkdir /opt/sqlinspect \
 && tar --warning=no-unknown-keyword -xzf "$ARCHIVE" -C /opt/sqlinspect \
 && test -x /opt/sqlinspect/sqlinspect

# Silence the Eclipse E4 javax-annotation warning (harmless for the CLI).
# The container runs as the host user (arbitrary UID): Eclipse must be able
# to write its configuration cache.
RUN printf -- '-vmargs\n-Declipse.e4.inject.javax.warning=false\n' >> /opt/sqlinspect/sqlinspect.ini \
 && chmod -R a+rwX /opt/sqlinspect

# --- Stage 2: runtime image (must be built for linux/amd64) ---
# Platform forced to linux/amd64 by tools/sqlinspect.sh (docker build --platform)
FROM eclipse-temurin:21-jre

RUN apt-get update \
 && apt-get install -y --no-install-recommends xvfb libgtk-3-0 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=fetch /opt/sqlinspect /opt/sqlinspect

# Arbitrary UID has no home directory: give Eclipse/Java a writable one
ENV HOME=/tmp

# Runs SQLInspect under a virtual X server (see entrypoint.sh)
COPY --chmod=755 entrypoint.sh /usr/local/bin/sqlinspect-entrypoint
ENTRYPOINT ["sqlinspect-entrypoint"]
CMD ["-help"]
