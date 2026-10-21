# nextcloud-php2shell-fix

> [!IMPORTANT]
> **Retired on 21 October 2026: patched official Nextcloud images are available for 33.0.10, 34.0.5 and 35.0.2. Use the official images below.**
>
> This repository and its community images are no longer maintained. The source, image references and build evidence are retained as a historical record.

This project provided temporary community replacements for the official **Nextcloud Apache image on linux/amd64**, addressing **PHP2Shell: CVE-2026-109618 and CVE-2026-109619** while official images were being rebuilt.

Each temporary image preserved its baseline's exact Nextcloud version and rebuilt PHP CLI, Apache's PHP module and extensions in the same PHP minor branch. The original build, test and publication records remain visible in [GitHub Actions](https://github.com/Kirari04/nextcloud-php2shell-fix/actions/workflows/publish.yml).

## Patched official images

Checked on **21 October 2026 at 18:43 UTC**, using [`scripts/check-official.sh`](scripts/check-official.sh) on an isolated **linux/amd64** Docker host. The following images passed exact Nextcloud-version checks and reported patched PHP in **both CLI and Apache over HTTP**:

| Official tag | Nextcloud version | PHP | Verified official digest |
| --- | --- | --- | --- |
| `nextcloud:33.0.10-apache` | 33.0.10.1 | 8.4.27 | `nextcloud@sha256:ca04a99f5a081030dd6c494bdfbb1cbc2bf3e2e10c0f9fcdc3be031ac3803f77` |
| `nextcloud:34.0.5-apache` | 34.0.5.1 | 8.5.12 | `nextcloud@sha256:5cd0788a5c7e0374256939dd86fefa34160ae03730cb28246d16939eacfd4c08` |
| `nextcloud:35.0.2-apache` | 35.0.2.2 | 8.5.12 | `nextcloud@sha256:3f05f4d5eded9d3d029e617926500645cca6344710364737a374088f6811095a` |

At the same check, **`nextcloud:stable` resolved to the verified 34.0.5 image above**, with the same registry digest and amd64 image ID. It can be used for a 34.0.5 installation, but future pulls of a floating tag can select a newer Nextcloud version. Pin the exact version or digest when that matters.

**34.0.4 exception:** `nextcloud:34.0.4-apache` still reported PHP 8.5.11 and failed the return checker. A move from 34.0.4 to 34.0.5 is a separate Nextcloud application upgrade; it is not a same-version image replacement. The archived 34.0.4 workaround will not receive further security updates.

These official-image checks were run locally with the included checker. The Actions links below document the earlier community builds. See [Return to an official image](#return-to-an-official-image) for switching instructions. PHP's [security advisory](https://www.php.net/archive/2026.php#2026-10-21-5) identifies 8.4.27 and 8.5.12 as fixed releases.

## Published community images (historical)

Published and verified on **21 October 2026**. All listed images are publicly pullable without a registry login. Supported variant: **Apache, linux/amd64**. FPM, Alpine and other architectures are outside this release set.

Image namespace: `ghcr.io/kirari04/nextcloud-php2shell-fix`. Append `:<tag>` or `@<digest>` below. The four-component Nextcloud version is the value reported by `status.php`.

| Nextcloud version | Tag | Immutable digest | Build, test and publication job |
| --- | --- | --- | --- |
| 33.0.10.1 | `33.0.10-php8.4.27` | `sha256:3a7389af9bd76b147902c958c611dc9db5ab7de16b9597d59410883ad0ce2534` | [Passed; 176 upstream tests](https://github.com/Kirari04/nextcloud-php2shell-fix/actions/runs/39634559417/job/119341533408) |
| 34.0.4.1 | `34.0.4-php8.5.12` | `sha256:82e049f237314ac4d7b974e800059a729c9fb81d0ff3a8b315ce71518658c36c` | [Passed; 180 upstream tests](https://github.com/Kirari04/nextcloud-php2shell-fix/actions/runs/39629236163/job/119322607167) |
| 34.0.5.1 | `34.0.5-php8.5.12` | `sha256:d9a2f414ba48026c156bff8f605f8ea01918fd0b424760caa6924f2234206bbb` | [Passed; 180 upstream tests](https://github.com/Kirari04/nextcloud-php2shell-fix/actions/runs/39634559417/job/119341533507) |
| 35.0.2.2 | `35.0.2-php8.5.12` | `sha256:a41bcec44fe4eea23c7026e2b0af756c3894bb07429ae6d177c5e9fff89f44d9` | [Passed; 180 upstream tests](https://github.com/Kirari04/nextcloud-php2shell-fix/actions/runs/39634559417/job/119341533779) |

The `33.0.10-apache`, `34.0.5-apache` and `35.0.2-apache` aliases resolve to the same respective community images. Revision tags additionally include the first 12 characters of the source commit. These references are retained for existing users and audit purposes; use the patched official images above for ongoing operation.

## Build and publication evidence

Each release links directly to its successful job above. Those jobs cover compilation, security tests, application compatibility, publication and an anonymous pull. The published builds use these source revisions:

- **33.0.10, 34.0.5 and 35.0.2:** [source commit `3cb65203a158`](https://github.com/Kirari04/nextcloud-php2shell-fix/tree/3cb65203a1588f8753e2c24d5aa1fb063e95fdb8), [workflow at that commit](https://github.com/Kirari04/nextcloud-php2shell-fix/blob/3cb65203a1588f8753e2c24d5aa1fb063e95fdb8/.github/workflows/publish.yml), [successful run](https://github.com/Kirari04/nextcloud-php2shell-fix/actions/runs/39634559417).
- **34.0.4:** [source commit `06de0d98157f`](https://github.com/Kirari04/nextcloud-php2shell-fix/tree/06de0d98157f4118886f2b788802b8508fb2ce9f), [workflow at that commit](https://github.com/Kirari04/nextcloud-php2shell-fix/blob/06de0d98157f4118886f2b788802b8508fb2ce9f/.github/workflows/publish.yml), [successful run](https://github.com/Kirari04/nextcloud-php2shell-fix/actions/runs/39629236163).

Verification artifacts: [33.0.10](https://github.com/Kirari04/nextcloud-php2shell-fix/actions/runs/39634559417/artifacts/12360714868), [34.0.4](https://github.com/Kirari04/nextcloud-php2shell-fix/actions/runs/39629236163/artifacts/12359273370), [34.0.5](https://github.com/Kirari04/nextcloud-php2shell-fix/actions/runs/39634559417/artifacts/12363700228), [35.0.2](https://github.com/Kirari04/nextcloud-php2shell-fix/actions/runs/39634559417/artifacts/12362645757).

Artifacts are retained for **30 days**. [GitHub requires sign-in to download workflow artifacts](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts); pulling the container images requires no sign-in. Each artifact contains:

- `php-build.log`, `build.log` and `upstream/upstream.txt`: source verification, compilation and individual upstream test results. All published suites report **zero failures and zero skips**.
- `integration/passed.json`, runtime inventories, file/package comparisons and persistence reports: the tested baseline, PHP/Nextcloud versions and application results.
- `published-image.txt`: the exact published registry digest, matching the release table.
- `public-pull.txt`: the successful pull using an empty Docker credential configuration.

The **Publish the exact tested image and verify registry roundtrip** step pushes the tested local image, pulls its registry digest and checks that its image ID matches. The **Verify public pull without credentials** step then checks public access. The image's `org.opencontainers.image.revision` label records the source commit. Upstream test results are also included at `/usr/local/share/php2shell/upstream/` inside each image.

For example, inspect the published 34.0.5 image independently:

```bash
image_ref=ghcr.io/kirari04/nextcloud-php2shell-fix@sha256:d9a2f414ba48026c156bff8f605f8ea01918fd0b424760caa6924f2234206bbb
docker pull "$image_ref"
docker image inspect "$image_ref" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}'
docker run --rm --entrypoint php "$image_ref" -v
docker run --rm --entrypoint cat "$image_ref" /usr/local/share/php2shell/upstream/upstream.txt
```

The revision should be `3cb65203a1588f8753e2c24d5aa1fb063e95fdb8` and PHP should report `8.5.12`. The Actions job also verifies Apache's PHP version over HTTP.

## Compatibility and test coverage

Each release starts from its own pinned official image. [`releases.json`](releases.json) records the baseline manifest digest, image ID, exact Nextcloud/PHP versions, PHP source checksum and Debian package snapshot.

The final image preserves the Nextcloud payload, entrypoint, cron script, PHP/Apache configuration, OS packages, UID/GID, port, stop signal and volume contract. Existing `/var/www/html` and `/tmp` mounts remain usable. PHP CLI, Apache's `libphp.so`, bundled shared extensions and development/source metadata are rebuilt. PECL extensions retain their baseline versions and options, including Redis/memcached igbinary support and Redis lz4/zstd support.

PHP source archives are checked against pinned php.net SHA-256 values and detached signatures using the official baseline's PHP signing keys. PECL archive checksums are pinned. Installing build headers must leave every existing runtime package version unchanged; the final image uses the baseline's OS libraries and passes linker checks.

The linked jobs verify:

- Selected upstream OOM and session lifecycle regressions, including request parsing and repeated-request cases. A separate test-only CGI build and `zend_test` enable cases that would otherwise skip; those test binaries are excluded from the final image.
- Byte-for-byte application/configuration checks, identical OS package lists, matching image startup settings, PHP modules, PECL versions and existing INI values.
- Actual Apache PHP version/SAPI/modules, multipart uploads, bounded OOM inputs, same-worker fatal-error/early-INI-diagnostic sequences and Redis/igbinary session continuity.
- **Official → patched → same official** using the same disposable database, Redis and volumes: health, form login/session continuity, WebDAV, cron, unchanged config/schema/migration records, file hashes, custom-app/theme data and ownership. Files written while patched must survive the return.

Integration tests use pinned **MySQL 8.4.11** and **Redis 8.10.2** images; exact versions are recorded in `integration/dependencies.txt`. Coverage uses disposable fixtures rather than a copy of every installation's apps and data. The PHP tests are a focused suite. Upload tests check the 50 GiB configuration values while transferring small fixtures; they do not exercise a 50 GiB transfer or production concurrency.

## Historical community-image installation instructions

The following instructions describe installation of the retired workaround. For current use, follow [Return to an official image](#return-to-an-official-image).

**Choose the exact Nextcloud version already installed.** These images patch PHP without requiring an application/database upgrade. Check the Nextcloud administration page or run the following against the existing Compose service, replacing `nextcloud` if the service has another name:

```bash
docker compose exec -T --user www-data nextcloud php occ status --output=json
```

1. Change only the Nextcloud service's `image:` to the matching digest from the release table. Keep its existing environment, mounts, dependencies, networks and healthcheck. For an installation on **34.0.5.1**, the image field is:

   ```yaml
   image: ghcr.io/kirari04/nextcloud-php2shell-fix@sha256:d9a2f414ba48026c156bff8f605f8ea01918fd0b424760caa6924f2234206bbb
   ```

2. Recreate only that service from the directory containing the existing Compose definition:

   ```bash
   docker compose pull nextcloud
   docker compose up -d --no-deps --force-recreate nextcloud
   ```

   For Portainer, edit the image in the existing stack and redeploy the Nextcloud service while retaining its configuration and volumes.

3. Check the runtime and application status:

   ```bash
   docker compose exec -T nextcloud php -v
   docker compose exec -T nextcloud curl -fsS http://127.0.0.1/status.php
   ```

   Expect the PHP version in the release tag, the same Nextcloud version as before, `installed:true`, `maintenance:false` and `needsDbUpgrade:false`.

Keep existing upload limits, memory limits, database/Redis settings and other configuration. An `occ upgrade`, data migration, replacement `config.php` or database recreation is not part of this PHP-only switch.

If startup reports that the data version is higher than the image version, select an image matching the installed version. Do not edit stored version information or force a downgrade. If `needsDbUpgrade` is true, investigate the installation's application upgrade state separately.

## Return to an official image

Choose an official **Apache/linux-amd64** image with the **same exact Nextcloud version** and patched PHP in its original minor branch: **8.4.27+ for Nextcloud 33** or **8.5.12+ for Nextcloud 34/35**.

From a clone of this repository, check the candidate on a test machine with Docker, Python 3 and curl. For a 34.0.5 installation:

```bash
bash scripts/check-official.sh nextcloud:34.0.5-apache 34.0.5
```

Set both version arguments for the release being checked. The script checks architecture, exact Nextcloud version, CLI PHP and Apache PHP over HTTP using an isolated probe. The three official images in the table above have passed these checks.

For example, an installation using the community **34.0.5** image can change its existing image field to:

```yaml
image: nextcloud:34.0.5-apache
```

The exact verified reference is `nextcloud@sha256:5cd0788a5c7e0374256939dd86fefa34160ae03730cb28246d16939eacfd4c08`. `nextcloud:stable` also matched this image at the check above; it can advance on later pulls.

Keep the existing configuration, database, Redis, volumes, networks and healthcheck, then recreate only the Nextcloud service:

```bash
docker compose pull nextcloud
docker compose up -d --no-deps --force-recreate nextcloud
docker compose exec -T nextcloud php -v
docker compose exec -T nextcloud curl -fsS http://127.0.0.1/status.php
```

For the 34.0.5 example, expect PHP 8.5.12 and Nextcloud 34.0.5.1 with `installed:true`, `maintenance:false` and `needsDbUpgrade:false`. No data migration or configuration change is part of this same-version replacement. Recheck tags and the installed version before switching; a move to a newer application version is a separate Nextcloud upgrade.

The old official images used in compatibility roundtrips contain vulnerable PHP; those tests establish persistence compatibility rather than a safe production rollback target.

## Historical build and verification process

The [manual Actions workflow](https://github.com/Kirari04/nextcloud-php2shell-fix/actions/workflows/publish.yml) accepted an exact `release`, `community` for 33.0.10/34.0.5/35.0.2, or `all` for all four releases. Each release was published only after its tests passed, using scoped `GITHUB_TOKEN` permissions (`contents:read`, `packages:write`). A public pull was required before reporting a successful public release. The workflow had no deployment credentials or deployment step. No further builds or releases are planned for this archived project.

For local validation of the Dockerfile's default **34.0.4** variant:

```bash
docker build --target runtime -t nextcloud-php2shell:verified .
python3 tests/verify-image.py nextcloud-php2shell:verified \
  --release 34.0.4 --evidence-dir /tmp/nextcloud-php2shell-evidence
```

The suite creates uniquely named disposable containers, networks and volumes, publishes HTTP only on loopback and removes its own resources. See the pinned workflow revisions above for the build arguments used for each published variant.

## Upstream references

- [PHP security advisory and fixed releases](https://www.php.net/archive/2026.php#2026-10-21-5).
- [CVE-2026-109618: RCE via OOM corruption](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w).
- [CVE-2026-109619: RCE via stale global state](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp).
- [PHP 8.4.27 source checksums](https://www.php.net/releases/index.php?json&version=8.4.27) and [PHP 8.5.12 source checksums](https://www.php.net/releases/index.php?json&version=8.5.12).
- [Official Nextcloud image source](https://github.com/nextcloud/docker).
