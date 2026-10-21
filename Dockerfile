# syntax=docker/dockerfile:1
# This amd64 manifest has production's exact image ID:
# sha256:3de31768a5ed5bb14157679c1048465d3f5425347c37c1a9f6ff7207ad1f7e54
ARG BASE_IMAGE=nextcloud@sha256:a6281e8046ba1a15bfd4225c8027daee7fd2fff6c593b446f4cd4983a432eef1
FROM ${BASE_IMAGE} AS original

FROM original AS build
ARG EXPECTED_ORIGINAL_PHP=8.5.10
ARG PATCHED_PHP=8.5.12
ARG PHP_SOURCE_SHA256=08bc2eba2a588654ade1357174aa646b761556c862dda0678345ee29ed481209
ARG DEBIAN_SNAPSHOT=20260919T040000Z
ENV PHP_VERSION=${PATCHED_PHP} \
    PHP_URL=https://www.php.net/distributions/php-${PATCHED_PHP}.tar.xz \
    PHP_ASC_URL=https://www.php.net/distributions/php-${PATCHED_PHP}.tar.xz.asc \
    PHP_SHA256=${PHP_SOURCE_SHA256}
COPY build/rebuild-php.sh build/pecl.sha256 /build/
RUN bash /build/rebuild-php.sh

# Test-only CGI and zend_test never enter the published image.
FROM build AS regression
COPY build/test-upstream.sh /build/test-upstream.sh
RUN bash /build/test-upstream.sh

FROM original AS runtime
ARG BASE_IMAGE
ARG BASE_DIGEST=sha256:a6281e8046ba1a15bfd4225c8027daee7fd2fff6c593b446f4cd4983a432eef1
ARG RELEASE_VERSION=34.0.4
ARG EXPECTED_NEXTCLOUD_VERSION=34.0.4.1
ARG PATCHED_PHP=8.5.12
ARG PHP_SOURCE_SHA256=08bc2eba2a588654ade1357174aa646b761556c862dda0678345ee29ed481209
ENV PHP_VERSION=${PATCHED_PHP} \
    PHP_URL=https://www.php.net/distributions/php-${PATCHED_PHP}.tar.xz \
    PHP_ASC_URL=https://www.php.net/distributions/php-${PATCHED_PHP}.tar.xz.asc \
    PHP_SHA256=${PHP_SOURCE_SHA256}
COPY --from=build /usr/local/ /usr/local/
COPY --from=build /usr/lib/apache2/modules/libphp.so /usr/lib/apache2/modules/libphp.so
COPY --from=build /usr/src/php.tar.xz /usr/src/php.tar.xz
COPY --from=regression /test-results/ /usr/local/share/php2shell/upstream/
RUN set -eu; \
    test "$(php -r 'echo PHP_VERSION;')" = "$PATCHED_PHP"; \
    test "$(php -r 'require "/usr/src/nextcloud/version.php"; echo implode(".", $OC_Version);')" = "$EXPECTED_NEXTCLOUD_VERSION"; \
    php -m; \
    apache2ctl -t; \
    for file in /usr/local/bin/php /usr/lib/apache2/modules/libphp.so /usr/local/lib/php/extensions/*/*.so; do \
        ldd "$file" > /tmp/php2shell-ldd; \
        if grep -q 'not found' /tmp/php2shell-ldd; then cat /tmp/php2shell-ldd; exit 1; fi; \
    done; \
    rm /tmp/php2shell-ldd
LABEL org.opencontainers.image.source="https://github.com/Kirari04/nextcloud-php2shell-fix" \
      org.opencontainers.image.title="Nextcloud ${RELEASE_VERSION} with PHP ${PATCHED_PHP}" \
      org.opencontainers.image.version="${RELEASE_VERSION}-php${PATCHED_PHP}" \
      org.opencontainers.image.base.name="docker.io/library/nextcloud" \
      org.opencontainers.image.base.digest="${BASE_DIGEST}" \
      io.php2shell.fixed-cves="CVE-2026-109618,CVE-2026-109619"
# Entrypoint, command, user, stop signal, workdir, volumes and ports are inherited.
