#!/bin/sh
set -e

mkdir -p /usr/share/nginx/html/plugins/temp
cd /home/mosip

sh configure_start.sh "$@"

echo "starting nginx"
nginx
exec sleep infinity
