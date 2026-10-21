#!/usr/bin/env bash
# Read-only inventory. Run on the Docker host with the existing Nextcloud container.
# Does not pull images, start/stop containers, run occ, or read config.php/secrets.
set -euo pipefail

if [[ $# != 1 || $1 == -* ]]; then
    printf 'Usage: bash %s NEXTCLOUD_CONTAINER\n' "$0" >&2
    exit 2
fi
container=$1

printf '\nContainer and image identity\n'
docker container inspect "$container" --format \
    'Name={{.Name}} Running={{.State.Running}} ConfiguredImage={{.Config.Image}} ImageID={{.Image}}'
image_id=$(docker container inspect "$container" --format '{{.Image}}')
docker image inspect "$image_id" --format \
    'RepoDigests={{json .RepoDigests}} OS={{.Os}} Architecture={{.Architecture}}'

printf '\nImage runtime contract\n'
docker image inspect "$image_id" --format \
    'Entrypoint={{json .Config.Entrypoint}} Cmd={{json .Config.Cmd}} User={{json .Config.User}} WorkDir={{json .Config.WorkingDir}} Volumes={{json .Config.Volumes}}'

printf '\nMount destinations (host paths omitted)\n'
docker container inspect "$container" --format \
    '{{range .Mounts}}{{printf "%s %s writable=%t\n" .Type .Destination .RW}}{{end}}'

printf '\nDeployed and image Nextcloud versions\n'
docker exec "$container" php -r \
    'require "/var/www/html/version.php"; echo "Deployed: ", $OC_VersionString, " (", implode(".", $OC_Version), ")\n";'
docker exec "$container" php -r \
    'require "/usr/src/nextcloud/version.php"; echo "Image: ", $OC_VersionString, " (", implode(".", $OC_Version), ")\n";'

printf '\nPHP runtime and modules\n'
docker exec "$container" php --version
docker exec "$container" php --modules
docker exec "$container" php-config --configure-options

printf '\nOperating system\n'
docker exec "$container" cat /etc/os-release

project=$(docker container inspect "$container" --format \
    '{{if .Config.Labels}}{{index .Config.Labels "com.docker.compose.project"}}{{end}}')
if [[ -n $project && $project != '<no value>' ]]; then
    printf '\nImages of services in the same Compose project\n'
    docker ps -a --filter "label=com.docker.compose.project=$project" \
        --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
fi
