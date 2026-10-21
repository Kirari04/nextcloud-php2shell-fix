#!/usr/bin/env bash
# Run on a test Docker host. Only an isolated probe container is started.
set -euo pipefail
if [[ $# != 1 ]]; then
    echo "Usage: bash $0 nextcloud:34.0.4-apache[@sha256:...]" >&2
    exit 2
fi
case "$1" in
    nextcloud:*|nextcloud@sha256:*|docker.io/library/nextcloud:*|docker.io/library/nextcloud@sha256:*) ;;
    *) echo 'Expected an official docker.io/library/nextcloud reference' >&2; exit 2 ;;
esac
docker pull "$1"
image_id=$(docker image inspect "$1" --format '{{.Id}}')
digest=$(docker image inspect "$1" --format '{{index .RepoDigests 0}}')
docker run --rm --entrypoint php "$image_id" -r '
    require "/usr/src/nextcloud/version.php";
    if (implode(".", $OC_Version) !== "34.0.4.1") {
        fwrite(STDERR, "Nextcloud version differs; this would be an application upgrade.\n"); exit(1);
    }
    if (PHP_MAJOR_VERSION !== 8 || PHP_MINOR_VERSION !== 5 || version_compare(PHP_VERSION, "8.5.12", "<")) {
        fwrite(STDERR, "Expected patched PHP in the deployed 8.5 branch.\n"); exit(1);
    }
'
container=''
cleanup() { if [[ -n $container ]]; then docker rm -f -v "$container" >/dev/null; fi; }
trap cleanup EXIT
container=$(docker create --entrypoint apache2-foreground -p 127.0.0.1::80 "$image_id")
docker cp "$(dirname "$0")/../tests/runtime.php" "$container:/var/www/html/index.php"
docker start "$container" >/dev/null
address=$(docker port "$container" 80/tcp)
for _ in {1..30}; do
    if result=$(curl --silent --fail --max-time 5 "http://$address/"); then
        break
    fi
    sleep 1
done
printf '%s' "${result:-}" | docker run --rm -i --entrypoint php "$image_id" -r '
    $r = json_decode(stream_get_contents(STDIN), true, flags: JSON_THROW_ON_ERROR);
    if ($r["sapi"] !== "apache2handler" || !str_starts_with($r["php"], "8.5.") || version_compare($r["php"], "8.5.12", "<")) exit(1);
    echo "Apache PHP ", $r["php"], " verified.\n";
'
printf 'Matching official Nextcloud version and patched web runtime: %s\n' "$digest"
