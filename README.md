# nextcloud-php2shell-fix

Temporary drop-in replacement for **Nextcloud 34.0.4 (34.0.4.1), Apache, linux/amd64**, rebuilding PHP **8.5.10 → 8.5.12** to fix **CVE-2026-109618 and CVE-2026-109619**. Builds and publication run in [GitHub Actions](https://github.com/Kirari04/nextcloud-php2shell-fix/actions).

**Status: validation in progress; no published image is recommended yet.**

## What stays the same

The final image starts from the exact official image used by the deployment:

```text
nextcloud@sha256:a6281e8046ba1a15bfd4225c8027daee7fd2fff6c593b446f4cd4983a432eef1
Image ID: sha256:3de31768a5ed5bb14157679c1048465d3f5425347c37c1a9f6ff7207ad1f7e54
```

It preserves the Nextcloud payload, entrypoint, cron script, PHP/Apache configuration, OS packages, UID/GID, exposed port, stop signal and `/var/www/html` volume contract. `/tmp` mounts also remain usable. MySQL, Redis, HAProxy, phpMyAdmin and their configuration do not need changes.

The replacement changes PHP CLI, Apache's `libphp.so`, bundled shared extensions and the PHP development/source metadata. All PECL extensions are rebuilt against the patched headers at the original versions: APCu 5.1.28, igbinary 3.2.17RC1, imagick 3.8.1, memcached 3.4.0 and redis 6.3.0. Redis/memcached igbinary support, Redis lz4/zstd support and igbinary session serialization are preserved.

No application or database upgrade is intended or required. The PHP fixes add upstream memory-limit and request-state protections; configuration-only mitigations are not a complete fix.

## Switch to the replacement

After a successful publication, use the immutable `ghcr.io/kirari04/nextcloud-php2shell-fix@sha256:…` reference shown in the workflow summary and `published-image.txt` artifact. The readable release tag is `34.0.4-php8.5.12`; revision tags also include the source commit.

1. In the existing Compose/Portainer stack, change **only the `nextcloud` service's `image:`** to the published digest. Keep every existing environment variable, mount, dependency, network and healthcheck.
2. Recreate only that service. With Compose, from the directory containing the actual stack definition:

   ```bash
   docker compose pull nextcloud
   docker compose up -d --no-deps --force-recreate nextcloud
   ```

   With Portainer, edit the existing `nc` stack. Do not request a pull/redeployment of unrelated services or remove volumes.

3. Confirm the existing healthcheck becomes healthy:

   ```bash
   docker exec nextcloudcontainer php -v
   docker exec nextcloudcontainer curl -fsS http://127.0.0.1/status.php
   ```

   Expect PHP **8.5.12**, Nextcloud **34.0.4.1**, `installed:true`, `maintenance:false`, `needsDbUpgrade:false`.

Keep the existing values `PHP_MEMORY_LIMIT=1G`, `PHP_UPLOAD_LIMIT=50G`, `APACHE_BODY_LIMIT=53687091200`, `NEXTCLOUD_UPDATE=1` and `NEXTCLOUD_INIT_HTACCESS=true`. Do not run `occ upgrade`, replace config.php, migrate data, or recreate MySQL/Redis to make this image work. No production changes are made by this repository or workflow.

## Return to the official image

Use an official **Apache image with the same Nextcloud version, 34.0.4.1**, and patched PHP 8.5.12 or later in the 8.5 branch. Check the candidate on a test machine:

```bash
bash scripts/check-official.sh nextcloud:34.0.4-apache
```

The script pulls the candidate, checks its Nextcloud version without running the Nextcloud entrypoint, starts an isolated Apache probe, verifies the web PHP version, then prints its immutable official digest. It fails if the application version differs or PHP is unpatched. Use that digest in the same `image:` field and repeat the two Compose commands above. Reuse the same configuration, database and volumes.

**Do not blindly switch to `nextcloud:stable`.** At preparation time it already points to 34.0.5. Its entrypoint would upgrade a 34.0.4 installation. If upstream only publishes a patched image containing a newer Nextcloud version, returning to it is a separate Nextcloud upgrade; a migration-free return to that newer image cannot be promised. Keep this replacement until a matching official image exists, or plan that upgrade separately.

The isolated compatibility test switches back to the original 34.0.4 image solely to establish data/configuration compatibility. That old image still contains vulnerable PHP and is **not** a security-safe production rollback target.

## Build and verification

Run the **Build, verify and publish patched Nextcloud** workflow with `publish=false` for validation or `publish=true` to publish after all checks pass. The workflow needs only its scoped `GITHUB_TOKEN` (`contents:read`, `packages:write`); it has no production credentials.

The GHCR package must be **Public** in its [package settings](https://github.com/users/Kirari04/packages/container/nextcloud-php2shell-fix/settings), independently of this public repository. The first publication waits up to five minutes for that setting. A credential-free pull of the published digest must pass before the workflow reports a successful public release.

The Dockerfile pins the production manifest. Build headers come from the corresponding Debian snapshot; the build fails if installing them changes any existing runtime package. PHP source is checked against the pinned php.net SHA-256 and a detached signature using the original official image's pinned PHP signing keys. PECL archive checksums are pinned too. The final image inherits the original OS libraries; linker checks and runtime tests guard against missing dependencies.

Verification gates:

- Upstream OOM and session lifecycle regressions from the verified PHP source, with a separate test-only CGI binary and `zend_test`. Required parser and session cases must actually pass. Test-only binaries and source are excluded from the final image.
- Byte-for-byte checks of Nextcloud, PHP/Apache configuration, entrypoint and cron; identical OS package lists and image runtime settings; matching PHP modules, PECL versions and existing INI values.
- HTTP verification of Apache's PHP version/SAPI/modules and the deployed upload/memory limits; normal multipart uploads; repeated-worker fatal-error/INI-diagnostic sequences; large multipart-header input and nested-input OOM cases; Redis/igbinary session continuity.
- Official → patched → official with the same disposable MySQL 8.4, Redis and volumes: healthcheck, form login/session continuity, WebDAV upload/download/listing, cron, unchanged config hash, installed apps, DB schema and migration records, file hashes, custom-app/theme data and ownership. Files written while patched must remain readable after restoring official.
- Publication pushes the exact tested image; pulling its registry digest must return the same image ID. Failed image verification prevents publication, and failed anonymous access prevents a successful public release.

The tests pin dependency image digests in `tests/verify-image.py`; their exact runtime versions are recorded in `dependencies.txt`. The supplied production inventory specified `mysql:8.4` and `redis:latest`, not their immutable digests. These are compatibility tests of that dependency family, not a claim to have cloned all production app configuration or user data. The 50 GiB upload setting is checked; tests transfer small fixtures, not a 50 GiB file.

Each Actions run retains build logs and verification artifacts for 30 days. Upstream regression results are also included at `/usr/local/share/php2shell/upstream/` in the image. To run the integration suite locally against a built image:

```bash
docker build --target runtime -t nextcloud-php2shell:verified .
python3 tests/verify-image.py nextcloud-php2shell:verified --evidence-dir /tmp/nextcloud-php2shell-evidence
```

The integration suite creates uniquely named disposable containers/networks/volumes, publishes HTTP only on loopback, and removes only resources it created. It never connects to a production endpoint.

## Sources

- [PHP security release announcement](https://www.php.net/archive/2026.php#2026-10-21-1) and [PHP 8.5.12 release checksums](https://www.php.net/releases/index.php?json&version=8.5.12).
- [CVE-2026-109618: RCE via OOM corruption](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w).
- [CVE-2026-109619: RCE via stale global state](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp).
- [Historical official Nextcloud manifest and production image ID](https://github.com/docker-library/repo-info/blob/2c2d62fb4d0d9e4a063692f51768f8405fd0a260/repos/nextcloud/remote/34.0.4-apache.md).
