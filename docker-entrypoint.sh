#!/bin/sh
set -eu

# Миграции в контейнере приложения — удобно для одного `docker compose up`,
# но при откате на старый образ его Alembic не знает новых ревизий и падает.
# Поэтому миграции можно отключить: RUN_MIGRATIONS=false.
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "applying migrations: ${DATABASE_URL%%\?*}"
    alembic upgrade head
else
    echo "migrations skipped: RUN_MIGRATIONS=${RUN_MIGRATIONS:-true}"
fi

exec "$@"
