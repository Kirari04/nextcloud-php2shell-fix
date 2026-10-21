#!/usr/bin/env python3
"""Validated, immutable release selection for builds, tests and return checks."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def catalog():
    releases = json.loads((ROOT / 'releases.json').read_text())
    for version, config in releases.items():
        assert re.fullmatch(r'\d+\.\d+\.\d+', version), 'Invalid release version'
        assert re.fullmatch(r'nextcloud@sha256:[0-9a-f]{64}', config['base']), 'Unpinned base image'
        assert re.fullmatch(r'sha256:[0-9a-f]{64}', config['base_id']), 'Invalid baseline image ID'
        assert re.fullmatch(re.escape(version) + r'\.\d+', config['nextcloud_internal']), 'Wrong Nextcloud payload'
        for key in ('original_php', 'patched_php'):
            assert re.fullmatch(r'8\.[45]\.\d+', config[key]), 'Unsupported PHP version'
        assert config['original_php'].rsplit('.', 1)[0] == config['patched_php'].rsplit('.', 1)[0], 'PHP minor upgrade prohibited'
        assert config['patched_php'] in ('8.4.27', '8.5.12'), 'Unreviewed PHP security release'
        assert re.fullmatch(r'[0-9a-f]{64}', config['php_sha256']), 'Unpinned PHP source'
        assert re.fullmatch(r'\d{8}T\d{6}Z', config['debian_snapshot']), 'Invalid Debian snapshot'
        assert type(config['community']) is bool
    return releases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['matrix', 'env', 'get'])
    parser.add_argument('release')
    parser.add_argument('field', nargs='?')
    args = parser.parse_args()
    releases = catalog()
    if args.action == 'matrix':
        if args.release == 'community':
            selected = [v for v, c in releases.items() if c['community']]
        elif args.release == 'all':
            selected = list(releases)
        else:
            if args.release not in releases:
                parser.error('Unknown release')
            selected = [args.release]
        print('matrix=' + json.dumps({'include': [{'release': v} for v in selected]}))
        return
    if args.release not in releases:
        parser.error('Unknown release')
    config = releases[args.release]
    if args.action == 'get':
        if args.field not in config:
            parser.error('Unknown catalog field')
        print(config[args.field])
        return
    values = {'RELEASE_VERSION': args.release, 'BASE_IMAGE': config['base'],
              'BASE_DIGEST': config['base'].split('@')[1],
              'EXPECTED_ORIGINAL_PHP': config['original_php'], 'PATCHED_PHP': config['patched_php'],
              'PHP_SOURCE_SHA256': config['php_sha256'], 'DEBIAN_SNAPSHOT': config['debian_snapshot'],
              'EXPECTED_NEXTCLOUD_VERSION': config['nextcloud_internal']}
    for key, value in values.items():
        print(f'{key}={value}')


if __name__ == '__main__':
    main()
