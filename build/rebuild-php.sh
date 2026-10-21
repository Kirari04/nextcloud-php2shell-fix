#!/usr/bin/env bash
set -euo pipefail

test "$(dpkg --print-architecture)" = amd64
test "$(php -r 'echo PHP_VERSION;')" = "$EXPECTED_ORIGINAL_PHP"
mkdir -p /build/downloads
dpkg-query -W -f='${binary:Package}\t${Version}\n' | sort > /build/original-packages.tsv
php-config --configure-options > /build/original-configure.txt
tar -cpf /build/php-config.tar -C /usr/local/etc/php .

# Headers are taken from the baseline's publication date. The assertion below
# rejects any upgrade of an existing runtime package in the builder.
sed -i \
    -e "s|http://deb.debian.org/debian-security|https://snapshot.debian.org/archive/debian-security/$DEBIAN_SNAPSHOT|" \
    -e "s|http://deb.debian.org/debian|https://snapshot.debian.org/archive/debian/$DEBIAN_SNAPSHOT|" \
    /etc/apt/sources.list.d/debian.sources
apt-get -o Acquire::Check-Valid-Until=false update
apt-get install -y --no-install-recommends \
    apache2-dev gnupg libargon2-dev libcurl4-openssl-dev libonig-dev \
    libreadline-dev libsodium-dev libsqlite3-dev libssl-dev libxml2-dev zlib1g-dev \
    libfreetype6-dev libgmp-dev libicu-dev libjpeg-dev libldap2-dev liblz4-dev \
    libmagickwand-dev libmemcached-dev libpng-dev libpq-dev libwebp-dev \
    libzip-dev libzstd-dev
while IFS=$'\t' read -r package version; do
    test "$(dpkg-query -W -f='${Version}' "$package")" = "$version" || {
        echo "Build headers would change runtime package: $package" >&2; exit 1;
    }
done < /build/original-packages.tsv

curl --fail --location --retry 5 "$PHP_URL" -o /usr/src/php.tar.xz
echo "$PHP_SHA256  /usr/src/php.tar.xz" | sha256sum -c -
curl --fail --location --retry 5 "$PHP_ASC_URL" -o /build/php.tar.xz.asc
export GNUPGHOME=/build/gnupg
mkdir -m 700 "$GNUPGHOME"
for key in $GPG_KEYS; do
    gpg --batch --keyserver hkps://keyserver.ubuntu.com --recv-keys "$key"
done
gpg --batch --verify /build/php.tar.xz.asc /usr/src/php.tar.xz
gpgconf --kill all
rm -rf "$GNUPGHOME"
unset GNUPGHOME

# Do not load pre-patch shared modules while rebuilding against new headers.
rm -f /usr/local/etc/php/conf.d/*.ini
docker-php-source delete
docker-php-source extract
cd /usr/src/php
export CFLAGS="$PHP_CFLAGS" CPPFLAGS="$PHP_CPPFLAGS" LDFLAGS="$PHP_LDFLAGS"
export PHP_BUILD_PROVIDER=https://github.com/Kirari04/nextcloud-php2shell-fix
export PHP_UNAME='Linux - Docker'
multiarch=$(dpkg-architecture --query DEB_BUILD_MULTIARCH)
./configure \
    --build="$(dpkg-architecture --query DEB_BUILD_GNU_TYPE)" \
    --sysconfdir=/usr/local/etc \
    --with-config-file-path=/usr/local/etc/php \
    --with-config-file-scan-dir=/usr/local/etc/php/conf.d \
    --enable-option-checking=fatal --with-mhash --with-pic --enable-mbstring \
    --enable-mysqlnd --with-password-argon2 --with-sodium=shared \
    --with-pdo-sqlite=/usr --with-sqlite3=/usr --with-curl --with-iconv \
    --with-openssl --with-readline --with-zlib --disable-phpdbg --with-pear \
    --with-libdir="lib/$multiarch" --disable-cgi --with-apxs2
make -j "$(nproc)"
make install

# Rebuild every bundled shared extension and every PECL extension in production.
docker-php-ext-configure ftp --with-ftp-ssl
docker-php-ext-configure gd --with-freetype --with-jpeg --with-webp
docker-php-ext-configure ldap --with-libdir="lib/$multiarch"
docker-php-ext-install -j "$(nproc)" \
    bcmath exif ftp gd gmp intl ldap pcntl pdo_mysql pdo_pgsql sysvsem zip
cd /build/downloads
while read -r checksum archive; do
    curl --fail --location --retry 5 "https://pecl.php.net/get/$archive" -o "$archive"
    echo "$checksum  $archive" | sha256sum -c -
done < /build/pecl.sha256
pecl install -f ./apcu-5.1.28.tgz
pecl install -f ./igbinary-3.2.17RC1.tgz
pecl install -f ./imagick-3.8.1.tgz
pecl install -f --configureoptions 'enable-memcached-igbinary="yes"' ./memcached-3.4.0.tgz
pecl install -f --configureoptions 'enable-redis-igbinary="yes" enable-redis-zstd="yes" enable-redis-lz4="yes"' ./redis-6.3.0.tgz

# Keep the deployed INI files byte for byte, including igbinary serialization.
rm -rf /usr/local/etc/php
mkdir /usr/local/etc/php
tar -xpf /build/php-config.tar -C /usr/local/etc/php
rm -rf /tmp/pear /root/.pearrc
strip --strip-unneeded /usr/local/bin/php /usr/lib/apache2/modules/libphp.so \
    /usr/local/lib/php/extensions/*/*.so
php -v
php -m
test "$(php -r 'echo PHP_VERSION;')" = "$PHP_VERSION"
