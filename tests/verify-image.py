#!/usr/bin/env python3
"""Isolated image, HTTP, MySQL/Redis and persistence tests. Never targets a host deployment."""
import argparse
import base64
import hashlib
import html
import http.cookiejar
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = 'nextcloud@sha256:a6281e8046ba1a15bfd4225c8027daee7fd2fff6c593b446f4cd4983a432eef1'
MYSQL = 'mysql@sha256:6f3a50835c54d61ffdcf78d71381ba268c27804cd96755231d2fd6f180f822f0'
REDIS = 'redis@sha256:13ad9044b4b2fd2abe4c5aad8c384b0504a71006fa33f023fc68998453a2eeca'
PECL = {'apcu': '5.1.28', 'igbinary': '3.2.17RC1', 'imagick': '3.8.1', 'memcached': '3.4.0', 'redis': '6.3.0'}
ROOT = Path(__file__).resolve().parent.parent


def command(*args, env=None):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if result.returncode:
        # No environment or command-line arguments (which can contain test passwords).
        raise RuntimeError(f'{args[0]} failed ({result.returncode}): {result.stderr[-6000:]}')
    return result.stdout.strip()


def docker(*args, **kwargs):
    return command('docker', *args, **kwargs)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def http(url, *, data=None, method=None, headers=None, opener=None):
    request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with (opener.open(request, timeout=45) if opener else urllib.request.urlopen(request, timeout=45)) as response:
            return response.status, response.read(), response.geturl()
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.geturl()


def wait_for(check, timeout=240):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except (Exception,) as error:
            last = error
        time.sleep(2)
    raise TimeoutError(f'Container readiness timed out; last error: {last}')


def image_php(image, code):
    return docker('run', '--rm', '--entrypoint', 'php', image, '-r', code)


def compare_contract(candidate, evidence):
    print('Comparing exact image contract, PHP extensions, configuration and Nextcloud payload', flush=True)
    original = json.loads(docker('image', 'inspect', BASE))[0]
    patched = json.loads(docker('image', 'inspect', candidate))[0]
    require(original['Id'] == 'sha256:3de31768a5ed5bb14157679c1048465d3f5425347c37c1a9f6ff7207ad1f7e54', 'Production image ID mismatch')
    require(original['Architecture'] == patched['Architecture'] == 'amd64', 'Architecture mismatch')
    for field in ('Entrypoint', 'Cmd', 'User', 'WorkingDir', 'Volumes', 'ExposedPorts', 'StopSignal'):
        require(original['Config'].get(field) == patched['Config'].get(field), f'Changed image contract: {field}')
    before_env = dict(item.split('=', 1) for item in original['Config']['Env'])
    after_env = dict(item.split('=', 1) for item in patched['Config']['Env'])
    for key in ('PHP_VERSION', 'PHP_URL', 'PHP_ASC_URL', 'PHP_SHA256'):
        before_env.pop(key)
        after_env.pop(key)
    require(before_env == after_env, 'Non-PHP environment changed')
    hash_command = ('find /usr/src/nextcloud /usr/local/etc/php /etc/apache2 '
                    '/entrypoint.sh /cron.sh /upgrade.exclude -type f -print0 '
                    '| sort -z | xargs -0 sha256sum')
    hashes = []
    inventories = []
    for label, image in [('original', BASE), ('patched', candidate)]:
        files = docker('run', '--rm', '--entrypoint', 'sh', image, '-c', hash_command)
        (evidence / f'{label}-files.sha256').write_text(files + '\n')
        hashes.append(files)
        inventory = json.loads(image_php(image, '''
            $modules = get_loaded_extensions(); sort($modules);
            $versions = []; foreach (["apcu","igbinary","imagick","memcached","redis"] as $m) $versions[$m] = phpversion($m);
            require "/usr/src/nextcloud/version.php";
            echo json_encode(["php"=>PHP_VERSION,"modules"=>$modules,"pecl"=>$versions,
                "nextcloud"=>implode(".",$OC_Version),"ini"=>ini_get_all(null,false)]);
        '''))
        (evidence / f'{label}-runtime.json').write_text(json.dumps(inventory, indent=2) + '\n')
        inventories.append(inventory)
        packages = docker('run', '--rm', '--entrypoint', 'dpkg-query', image, '-W', '-f=${binary:Package}\t${Version}\n')
        (evidence / f'{label}-packages.tsv').write_text(packages + '\n')
        if label == 'original':
            original_packages = packages
        else:
            require(packages == original_packages, 'OS packages changed')
    require(hashes[0] == hashes[1], 'Nextcloud payload or configuration changed')
    before, after = inventories
    require(before['php'] == '8.5.10' and after['php'] == '8.5.12', 'Wrong PHP versions')
    require(before['nextcloud'] == after['nextcloud'] == '34.0.4.1', 'Nextcloud changed')
    require(before['modules'] == after['modules'], 'PHP module set changed')
    require(before['pecl'] == after['pecl'] == PECL, 'PECL version mismatch')
    ini_changes = {key: [value, after['ini'].get(key)] for key, value in before['ini'].items() if after['ini'].get(key) != value}
    require(not ini_changes, f'Existing PHP INI defaults changed: {ini_changes}')
    docker('run', '--rm', '--entrypoint', 'apache2ctl', candidate, '-t')
    (evidence / 'apache-modules.txt').write_text(docker('run', '--rm', '--entrypoint', 'apache2ctl', candidate, '-M') + '\n')
    return after


class Lab:
    def __init__(self, evidence):
        self.prefix = 'nc-php2shell-test-' + uuid.uuid4().hex[:12]
        self.network = self.prefix + '-net'
        self.evidence = evidence
        self.containers = []
        self.volumes = []
        self.password = uuid.uuid4().hex
        # A private test bridge with HTTP published only on loopback. Docker's
        # internal networks do not publish host ports on all engine versions.
        docker('network', 'create', self.network)

    def volume(self, suffix):
        name = self.prefix + '-' + suffix
        docker('volume', 'create', name)
        self.volumes.append(name)
        return name

    def run(self, suffix, image, env=None, options=(), args=()):
        name = self.prefix + '-' + suffix
        self.containers.append(name)
        environment = os.environ.copy()
        env_args = []
        for key, value in (env or {}).items():
            environment[key] = value
            env_args += ['--env', key]
        docker('run', '-d', '--name', name, '--network', self.network,
               *env_args, *options, image, *args, env=environment)
        return name

    def url(self, container):
        address = docker('port', container, '80/tcp').splitlines()[0]
        require(address.startswith('127.0.0.1:'), 'Test endpoint must be loopback only')
        return 'http://' + address

    def remove(self, container):
        (self.evidence / f'{container}.log').write_text(docker('logs', container))
        docker('rm', '-f', '-v', container)
        self.containers.remove(container)

    def close(self):
        for container in reversed(self.containers):
            try:
                result = subprocess.run(['docker', 'logs', container], text=True, capture_output=True)
                (self.evidence / f'{container}.log').write_text(result.stdout + result.stderr)
            finally:
                subprocess.run(['docker', 'rm', '-f', '-v', container], capture_output=True)
        for volume in self.volumes:
            subprocess.run(['docker', 'volume', 'rm', volume], capture_output=True)
        subprocess.run(['docker', 'network', 'rm', self.network], capture_output=True)


def multipart(content, extra_headers=b''):
    boundary = 'php2shell-test-boundary'
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="PHP_SESSION_UPLOAD_PROGRESS"\r\n\r\nprobe\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="fixture.txt"\r\n').encode()
    body += extra_headers + b'Content-Type: application/octet-stream\r\n\r\n' + content
    body += f'\r\n--{boundary}--\r\n'.encode()
    return body, {'Content-Type': f'multipart/form-data; boundary={boundary}'}


def apache_security(candidate, lab, inventory):
    print('Testing actual Apache SAPI, multipart OOM, repeated-worker state and Redis/igbinary sessions', flush=True)
    fixtures = lab.evidence / 'http-fixtures'
    fixtures.mkdir(exist_ok=True)
    for path in ('index.php', 'early/index.php', 'oom/index.php'):
        target = fixtures / path
        target.parent.mkdir(exist_ok=True)
        target.write_bytes((ROOT / 'tests/runtime.php').read_bytes())
    config = lab.evidence / 'apache-test.conf'
    config.write_text('''ServerName localhost
StartServers 1
MinSpareServers 1
MaxSpareServers 1
MaxRequestWorkers 1
MaxConnectionsPerChild 0
php_admin_value error_log /proc/self/fd/2
php_admin_flag log_errors On
php_value session.save_handler redis
php_value session.save_path tcp://redis:6379
<Directory /var/www/html/early>
    php_value auto_detect_line_endings 1
</Directory>
<Directory /var/www/html/oom>
    php_value memory_limit 8M
</Directory>
''')
    for path in [fixtures, fixtures / 'early', fixtures / 'oom']:
        path.chmod(0o755)
    container = lab.run('http', candidate, env={'PHP_MEMORY_LIMIT': '1G', 'PHP_UPLOAD_LIMIT': '50G', 'APACHE_BODY_LIMIT': '53687091200'},
                        options=['--memory', '512m', '--pids-limit', '128', '-p', '127.0.0.1::80',
                                 '--entrypoint', 'apache2-foreground', '-v', f'{fixtures}:/var/www/html:ro',
                                 '-v', f'{config}:/etc/apache2/conf-enabled/zzz-test.conf:ro'])
    url = lab.url(container)
    wait_for(lambda: http(url)[0] == 200)
    details = json.loads(http(url)[1])
    require(details['php'] == '8.5.12' and details['sapi'] == 'apache2handler', 'Apache is not using patched PHP')
    # readline is CLI-only; Apache registers its own SAPI module.
    require(set(details['modules']) - {'apache2handler'} == set(inventory['modules']) - {'readline'}, 'Apache/CLI extension mismatch')
    require(details['memory_limit'] == '1G' and details['upload_max_filesize'] == details['post_max_size'] == '50G', 'Production PHP settings not honored')
    require(details['session_handler'] == 'redis' and details['session_serializer'] == 'igbinary', 'Wrong production session configuration')
    (lab.evidence / 'apache-runtime.json').write_text(json.dumps(details, indent=2) + '\n')
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    sentinel = json.loads(http(url + '/?action=session', opener=opener)[1])['sentinel']
    content = b'ordinary multipart upload\n' * 4096
    body, headers = multipart(content)
    status, response, _ = http(url + '/', data=body, headers=headers, opener=opener)
    require(status == 200 and json.loads(response)['file_sha256'] == hashlib.sha256(content).hexdigest(), 'Normal multipart upload failed')
    require(json.loads(http(url + '/?action=session', opener=opener)[1])['sentinel'] == sentinel, 'Upload progress broke session')
    initial_pid = details['pid']
    for _ in range(12):
        require(http(url + '/?action=fatal')[0] == 500, 'Fatal trigger did not execute')
        status, response, _ = http(url + '/early/index.php')
        require(status == 200 and json.loads(response)['pid'] == initial_pid, 'Stale-state sequence failed on same worker')
    malicious = [multipart(b'x', b'X-Padding: abcdefghijklmnopqrstuvwxyz\r\n' * 100000),
                 (('&'.join('a[]' + '[b]' * 63 + '=c' for _ in range(1000))).encode(),
                  {'Content-Type': 'application/x-www-form-urlencoded'})]
    for body, headers in malicious:
        status, _, _ = http(url + '/oom/index.php', data=body, headers=headers)
        require(status == 500, f'OOM trigger was not rejected: HTTP {status}')
        status, response, _ = http(url + '/')
        require(status == 200 and json.loads(response)['php'] == '8.5.12', 'Normal request failed after OOM')
    logs_result = subprocess.run(['docker', 'logs', container], capture_output=True, text=True)
    logs = logs_result.stdout + logs_result.stderr
    require('Allowed memory size' in logs, 'No evidence of OOM trigger')
    require(not re.search(r'Segmentation fault|signal 11|signal 7|corrupted|double free', logs, re.I), 'Apache memory corruption detected')
    (lab.evidence / 'apache-security.log').write_text(logs)
    lab.remove(container)


def persistence(candidate, lab, mysql):
    print('Testing official -> patched -> official with the SAME MySQL, Redis and volumes', flush=True)
    html_volume = lab.volume('html')
    tmp_volume = lab.volume('tmp')
    env = {'MYSQL_HOST': 'mysql', 'MYSQL_DATABASE': 'nextcloud', 'MYSQL_USER': 'nextcloud',
           'MYSQL_PASSWORD': lab.password, 'REDIS_HOST': 'redis', 'PHP_MEMORY_LIMIT': '1G',
           'NEXTCLOUD_UPDATE': '1', 'APACHE_BODY_LIMIT': '53687091200', 'PHP_UPLOAD_LIMIT': '50G',
           'NEXTCLOUD_INIT_HTACCESS': 'true', 'NEXTCLOUD_ADMIN_USER': 'testadmin',
           'NEXTCLOUD_ADMIN_PASSWORD': lab.password, 'NEXTCLOUD_TRUSTED_DOMAINS': '127.0.0.1 localhost'}
    files = {}
    reference = None
    session_opener = None
    auth = 'Basic ' + base64.b64encode(('testadmin:' + lab.password).encode()).decode()
    for phase, image in [('original', BASE), ('patched', candidate), ('restored-official', BASE)]:
        container = lab.run(phase, image, env=env, options=[
            '--memory', '2g', '-p', '127.0.0.1::80', '-v', f'{html_volume}:/var/www/html', '-v', f'{tmp_volume}:/tmp'])
        url = lab.url(container)

        def healthy():
            status, body, _ = http(url + '/status.php')
            if status != 200:
                return False
            data = json.loads(body)
            return data if data.get('installed') and not data.get('maintenance') and not data.get('needsDbUpgrade') else False

        state = wait_for(healthy, timeout=360)
        require(state['version'] == '34.0.4.1', 'Application version changed')
        php_version = docker('exec', container, 'php', '-r', 'echo PHP_VERSION;')
        require(php_version == ('8.5.12' if phase == 'patched' else '8.5.10'), 'Unexpected runtime in persistence phase')
        # The real production healthcheck is unchanged.
        docker('exec', container, 'sh', '-c', '''curl -sSf http://127.0.0.1/status.php | grep '"installed":true' | grep '"maintenance":false' | grep '"needsDbUpgrade":false' ''')
        docker('exec', '-u', 'www-data', container, 'php', '-f', '/var/www/html/cron.php')
        config_hash = docker('exec', container, 'sha256sum', '/var/www/html/config/config.php')
        apps = json.loads(docker('exec', '-u', 'www-data', container, 'php', 'occ', 'app:list', '--output=json'))
        sql = '''SELECT app,version FROM oc_migrations ORDER BY app,version;
                 SELECT TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_DEFAULT,EXTRA
                 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='nextcloud' ORDER BY TABLE_NAME,ORDINAL_POSITION;
                 SELECT TABLE_NAME,INDEX_NAME,NON_UNIQUE,SEQ_IN_INDEX,COLUMN_NAME
                 FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='nextcloud' ORDER BY TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX;'''
        schema = docker('exec', '-e', 'MYSQL_PWD=' + lab.password, mysql, 'mysql', '-u', 'nextcloud', '-N', '-B', 'nextcloud', '-e', sql)
        if reference is None:
            reference = (config_hash, apps, schema)
            docker('exec', '-u', 'www-data', container, 'sh', '-c',
                   'printf custom-app-data > custom_apps/persistence-marker; printf theme-data > themes/persistence-marker')
        else:
            require((config_hash, apps, schema) == reference, 'Config, installed apps, DB schema or migrations changed')
        require(docker('exec', container, 'cat', '/var/www/html/custom_apps/persistence-marker') == 'custom-app-data', 'Custom apps volume not preserved')
        require(docker('exec', container, 'stat', '-c', '%u:%g', '/var/www/html/custom_apps/persistence-marker') == '33:33', 'Volume ownership changed')
        require(docker('exec', container, 'cat', '/var/www/html/themes/persistence-marker') == 'theme-data', 'Theme volume not preserved')
        if session_opener is not None:
            status, response, _ = http(url + '/ocs/v2.php/cloud/user?format=json', opener=session_opener, headers={'OCS-APIRequest': 'true'})
            require(status == 200 and json.loads(response)['ocs']['data']['id'] == 'testadmin', 'Login session did not survive image switch')
        # Test actual form login and Redis session, retaining the cookie jar across replacements.
        jar = http.cookiejar.CookieJar()
        session_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        status, page, _ = http(url + '/login', opener=session_opener)
        token = re.search(r'data-requesttoken="([^"]+)"', page.decode())
        require(status == 200 and token is not None, 'Login page/token unavailable')
        data = urllib.parse.urlencode({'user': 'testadmin', 'password': lab.password, 'requesttoken': html.unescape(token.group(1))}).encode()
        http(url + '/login', data=data, opener=session_opener)
        status, response, _ = http(url + '/ocs/v2.php/cloud/user?format=json', opener=session_opener, headers={'OCS-APIRequest': 'true'})
        require(status == 200 and json.loads(response)['ocs']['data']['id'] == 'testadmin', 'Form login failed')
        dav = url + '/remote.php/dav/files/testadmin/'
        for filename, content in files.items():
            status, response, _ = http(dav + filename, headers={'Authorization': auth})
            require(status == 200 and response == content, 'File changed during image switch: ' + filename)
        content = (phase + '\n').encode() * 8192
        filename = phase + '.txt'
        status, _, _ = http(dav + filename, method='PUT', data=content, headers={'Authorization': auth, 'Content-Type': 'text/plain'})
        require(status == 201, 'WebDAV upload failed')
        files[filename] = content
        status, response, _ = http(dav + filename, headers={'Authorization': auth})
        require(status == 200 and response == content, 'WebDAV download failed')
        status, _, _ = http(dav, method='PROPFIND', headers={'Authorization': auth, 'Depth': '1'})
        require(status == 207, 'WebDAV listing failed')
        logs = docker('logs', container)
        require('Upgrading nextcloud' not in logs, 'Nextcloud upgrade was triggered')
        report = {'status': state, 'php': php_version, 'config_sha256': config_hash.split()[0],
                  'schema_sha256': hashlib.sha256(schema.encode()).hexdigest(), 'apps': apps,
                  'file_sha256': {name: hashlib.sha256(value).hexdigest() for name, value in files.items()},
                  'login': True, 'webdav': True, 'cron': True}
        (lab.evidence / f'{phase}-persistence.json').write_text(json.dumps(report, indent=2) + '\n')
        lab.remove(container)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('image')
    parser.add_argument('--evidence-dir', type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    for image in (BASE, MYSQL, REDIS):
        docker('pull', image)
    inventory = compare_contract(args.image, evidence)
    lab = Lab(evidence)
    try:
        mysql = lab.run('mysql', MYSQL, env={'MYSQL_ROOT_PASSWORD': lab.password, 'MYSQL_DATABASE': 'nextcloud',
                       'MYSQL_USER': 'nextcloud', 'MYSQL_PASSWORD': lab.password}, options=['--network-alias', 'mysql', '--memory', '1g'])
        redis = lab.run('redis', REDIS, options=['--network-alias', 'redis', '--memory', '256m'])
        wait_for(lambda: docker('exec', '-e', 'MYSQL_PWD=' + lab.password, mysql, 'mysql', '-u', 'nextcloud', '-N', '-e', 'SELECT 1') == '1')
        wait_for(lambda: docker('exec', redis, 'redis-cli', 'ping') == 'PONG')
        (evidence / 'dependencies.txt').write_text(docker('exec', mysql, 'mysqld', '--version') + '\n' + docker('exec', redis, 'redis-server', '--version') + '\n')
        apache_security(args.image, lab, inventory)
        persistence(args.image, lab, mysql)
        (evidence / 'passed.json').write_text(json.dumps({'image': args.image, 'baseline': BASE, 'mysql': MYSQL,
            'redis': REDIS, 'php': '8.5.12', 'nextcloud': '34.0.4.1', 'architecture': 'amd64', 'passed': True}, indent=2) + '\n')
        print('PASS: patched Apache/CLI, unchanged image contract, security regressions, MySQL/Redis and official roundtrip', flush=True)
    finally:
        lab.close()


if __name__ == '__main__':
    main()
