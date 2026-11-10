# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версии — [semver](https://semver.org/lang/ru/).

## [Unreleased]

## [0.1.0] - 2025-11-10

Первая версия сервиса.

### Добавлено

- Каталог комплектующих: CPU, материнские платы, память, видеокарты, БП, корпуса, кулеры,
  накопители — 44 реальные модели с характеристиками.
- Проверка совместимости сборки: сокет CPU и платы, тип памяти, форм-фактор платы и корпуса,
  длина видеокарты и корпуса, поддержка сокета кулером, мощность БП с расчётом потребления
  и рекомендуемого запаса 35%.
- API: `/health`, `/version`, `/catalog/*`, `/builds` (создание с проверкой, список, карточка,
  удаление), `/builds/check` для проверки без сохранения.
- Схема БД на Alembic (`0001_initial`): `components`, `builds`, `build_items`.
- Идемпотентный сид каталога и обновление цен из CSV-выгрузки.
- Dockerfile (multi-stage, non-root, миграции в entrypoint), `compose.yaml` с PostgreSQL,
  healthcheck, volume и паролем из `.env`.
- CI: Ruff, обратимость миграций на PostgreSQL, pytest. CD: публикация `:latest` и `:sha-*`
  в ghcr.io после зелёного CI. Release по тегу с проверкой semver, версии и принадлежности
  тега ветке `main`.
- README, RUNBOOK, CHANGELOG.
