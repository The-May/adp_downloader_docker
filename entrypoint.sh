#!/bin/sh
set -e

# Substitute environment variables into config.ini from the template
envsubst < /app/config.ini.template > /app/config.ini

echo "config.ini generated from environment."

exec python handler.py "$@"
