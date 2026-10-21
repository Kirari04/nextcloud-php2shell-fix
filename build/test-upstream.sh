#!/usr/bin/env bash
set -euo pipefail
mkdir -p /test-results /build/test-php
tar -xJf /usr/src/php.tar.xz -C /build/test-php --strip-components=1
cd /build/test-php

# Separate CGI build for request-parser regressions, with the same fixed source.
# The production CLI and Apache module remain the binaries installed above.
./configure --disable-all --enable-cgi --enable-session --enable-filter \
    --enable-zend-test=shared --without-pear
make -j "$(nproc)"
export TEST_PHP_EXECUTABLE=/usr/local/bin/php
export TEST_PHP_CGI_EXECUTABLE=/build/test-php/sapi/cgi/php-cgi
export TEST_PHP_ARGS='-n'
export NO_INTERACTION=1 REPORT_EXIT_STATUS=1 SKIP_ONLINE_TESTS=1

tests=(Zend/tests/oom_*.phpt sapi/cli/tests/oom_*_next_request.phpt
    ext/session/tests/rfc1867_no_user_code.phpt
    ext/session/tests/rfc1867_incomplete_class_reserved_props.phpt)
# Load zend_test from the test build where required, and the actual final shared
# extensions, so the harness can run enabled-extension OOM regressions too.
for ext in bcmath curl date dom exif fileinfo filter gd hash iconv intl json ldap \
    mbstring openssl pcre pdo pdo_mysql pdo_pgsql phar posix random readline session \
    simplexml sodium spl sqlite3 standard tokenizer xml xmlreader xmlwriter zip zlib; do
    for test in "ext/$ext"/tests/oom_*.phpt; do
        [[ ! -f $test ]] || tests+=("$test")
    done
done
args=(-n -d "extension_dir=$(php-config --extension-dir)")
if [[ -f modules/zend_test.so ]]; then
    args+=(-d "extension=$PWD/modules/zend_test.so")
fi
php -n run-tests.php "${args[@]}" -q -j2 \
    -w /test-results/failed.txt "${tests[@]}" \
    2>&1 | tee /test-results/upstream.txt
test ! -s /test-results/failed.txt
# Core request-parser and session lifecycle tests must run, not silently skip.
for name in oom_request_parsing.phpt oom_request_parsing_next_request.phpt \
    oom_shutdown_function_next_request.phpt rfc1867_no_user_code.phpt \
    rfc1867_incomplete_class_reserved_props.phpt oom_hard_limit_exceeded.phpt \
    oom_soft_limit_in_callback.phpt oom_filter_default_encoded.phpt \
    oom_filter_input.phpt oom_filter_input_array.phpt; do
    grep -E "PASS.*${name//./\\.}" /test-results/upstream.txt >/dev/null
done
printf 'PHP %s upstream OOM and session lifecycle regression suite passed.\n' "$PHP_VERSION" \
    > /test-results/passed.txt
