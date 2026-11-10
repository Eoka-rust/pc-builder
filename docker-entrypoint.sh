#!/bin/sh
set -eu

echo "applying migrations: ${DATABASE_URL%%\?*}"
alembic upgrade head

exec "$@"
