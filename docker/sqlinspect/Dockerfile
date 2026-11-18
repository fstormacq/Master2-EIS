# SQLInspect CLI in a portable container.
# SQLInspect only ships a Linux x86_64 build (native GTK/SWT launcher), so the
# image is always linux/amd64. On ARM hosts (Apple Silicon), Docker runs it
# through emulation (Rosetta or QEMU): slower, but identical results.
FROM --platform=linux/amd64 eclipse-temurin:21-jre

ARG SQLINSPECT_VERSION=0.4.2.v20241021-1301
ARG SQLINSPECT_SHA256=f91d8c1bfab0d5800d4c0b5d8f1b6dfe75a5044cc184dee499ced96531753c9c

RUN apt-get update \
 && apt-get install -y --no-install-recommends xvfb libgtk-3-0 curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/sqlinspect
RUN set -eu; \
    file="sqlinspect.product-${SQLINSPECT_VERSION}-linux.gtk.x86_64.tar.gz"; \
    curl -fsSL -o "$file" "https://bitbucket.org/csnagy/sqlinspect/downloads/${file}"; \
    echo "${SQLINSPECT_SHA256}  ${file}" | sha256sum -c --quiet; \
    # The archive was built with bsdtar (macOS): skip its unknown header keywords
    tar --warning=no-unknown-keyword -xzf "$file"; \
    rm "$file"; \
    # Silence the Eclipse E4 javax-annotation warning (harmless for the CLI)
    printf -- '-vmargs\n-Declipse.e4.inject.javax.warning=false\n' >> sqlinspect.ini; \
    # The container runs as the host user (arbitrary UID): Eclipse must be able
    # to write its configuration cache
    chmod -R a+rwX /opt/sqlinspect

# Arbitrary UID has no home directory: give Eclipse/Java a writable one
ENV HOME=/tmp

# Runs SQLInspect under a virtual X server (see entrypoint.sh)
COPY entrypoint.sh /usr/local/bin/sqlinspect-entrypoint
RUN chmod 755 /usr/local/bin/sqlinspect-entrypoint
ENTRYPOINT ["sqlinspect-entrypoint"]
CMD ["-help"]
