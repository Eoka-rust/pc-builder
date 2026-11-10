# RUNBOOK — эксплуатация PC Builder API

Аварийная инструкция: что проверить и что выполнить, когда сервис не отвечает.
Все команды — из корня репозитория. `COMPOSE="docker compose"` — локальный прод,
`.env` содержит `POSTGRES_PASSWORD` и `GHCR_OWNER`.

## 0. Диагностика за 30 секунд

```bash
docker compose ps                              # статус и health
curl -i http://localhost:8000/health            # 200 / 503
docker compose logs --tail=100 api              # приложение
docker compose logs --tail=50 db                # PostgreSQL
```

`/health` отдаёт версию образа — так проверяется, какая версия реально работает:

```bash
curl -s http://localhost:8000/health
# {"status":"ok","version":"0.2.0","database":"ok"}
```

| Симптом | Вероятная причина | Действие |
|---|---|---|
| `api` в статусе `health: starting` дольше 1 минуты | миграция или БД не готовы | п. 1 |
| `/health` → 503, `database: unavailable` | БД недоступна или пароль не совпал | п. 2 |
| `api` падает сразу после старта | ошибка миграции | п. 3 |
| `/health` ок, но версия не та | контейнер не пересоздан | п. 5 |
| 500 на запросах к сборкам | рассинхрон схемы и кода | п. 3 |

## 1. Сервис не поднимается

```bash
docker compose down
docker compose up -d
docker compose ps
docker compose logs --tail=200 api
```

Если в логах `dependency failed to start: container ... is unhealthy` — проблема в БД,
переходите к п. 2.

## 2. База недоступна

```bash
docker compose exec db pg_isready -U pcbuilder -d pcbuilder
docker compose exec db psql -U pcbuilder -d pcbuilder -c "select count(*) from components;"
```

- `pg_isready` не отвечает: `docker compose restart db`, затем `docker compose up -d api`.
- `password authentication failed`: в `.env` и в `DATABASE_URL` разный пароль.
  Исправьте `.env` и пересоздайте контейнеры: `docker compose up -d --force-recreate api`.
- Тома нет или он повреждён: `docker volume ls | findstr pcbuilder`. Если том потерян,
  данные сборок пропали; каталог восстановится сидом при `SEED_ON_START=true`.

Проверка, что данные на месте:

```bash
curl -s http://localhost:8000/catalog/categories
```

## 3. Миграция упала

```bash
docker compose exec api alembic current
docker compose exec api alembic history --verbose
docker compose logs api | findstr /i alembic
```

- `Can't locate revision identified by '0002_released_year'` — в образе нет файла этой
  миграции (старый тег на новой схеме). Это ошибка отката, см. п. 4, вариант Б.
- `Can't locate revision` на новом образе — в образ не попали файлы миграций: пересоберите
  образ или перевыкатите тег.
- Миграция применена частично: PostgreSQL DDL транзакционен, при падении откатывается сам;
  повторите `docker compose exec api alembic upgrade head`.
- Нужно вернуть схему на предыдущую ревизию: `docker compose exec api alembic downgrade -1`
  (осознанно: удаляются данные из откатываемых колонок).

## 4. Откат на предыдущую версию

Откат — это смена тега образа; сборка не выполняется. Порядок зависит от того,
пересекает ли откат границу миграции.

### Вариант А — в пределах одной ревизии схемы (0.2.2 → 0.2.1 → 0.2.0)

```bash
curl -s http://localhost:8000/health          # что сейчас
IMAGE_TAG=0.2.1 docker compose -f compose.yaml -f compose.prod.yaml up -d
curl -s http://localhost:8000/health          # {"status":"ok","version":"0.2.1",...}
docker compose -f compose.yaml -f compose.prod.yaml exec -T api alembic current
```

Схема не трогается: ревизия одна и та же.

### Вариант Б — через границу миграции (0.2.x → 0.1.0)

Образ `0.1.0` запускает `alembic upgrade head` и не знает ревизии `0002_released_year`,
поэтому падает с `Can't locate revision`. Сначала опускаем схему текущим образом:

```bash
# 1. откатить схему на ревизию, известную старому образу
IMAGE_TAG=0.2.2 docker compose -f compose.yaml -f compose.prod.yaml up -d
docker compose -f compose.yaml -f compose.prod.yaml exec -T api alembic downgrade 0001_initial

# 2. переключить образ
IMAGE_TAG=0.1.0 docker compose -f compose.yaml -f compose.prod.yaml up -d
curl -s http://localhost:8000/health          # version 0.1.0
curl -s http://localhost:8000/catalog/categories
```

Данные сборок сохраняются; теряются только значения `released_year` (их не существует в
схеме 0001). Для образов 0.2.2 и новее вместо downgrade можно отключить миграции при
старте: `RUN_MIGRATIONS=false` (если миграции выполняет отдельный шаг деплоя).

На версии `0.1.0` проверка сборки без видеокарты отвечает 500 — известный дефект,
исправлен в 0.2.3. Для smoke-теста старого образа используйте полную сборку
(с `component_id` видеокарты) или ограничьтесь `/health` и `/catalog/categories`.

### Проверка, что сервис жив после отката

```bash
curl -s http://localhost:8000/health
curl -s "http://localhost:8000/catalog/components?limit=1"
curl -s -X POST http://localhost:8000/builds/check -H "Content-Type: application/json" \
  -d '{"name":"smoke","items":[{"component_id":1,"quantity":1}]}'
```

Список доступных версий:

```bash
docker image ls ghcr.io/eoka-rust/pc-builder --format "{{.Tag}}"
```

## 5. Выкат новой версии

```bash
IMAGE_TAG=0.2.0 docker compose -f compose.yaml -f compose.prod.yaml up -d
docker compose ps
curl -s http://localhost:8000/health
```

Если версия в `/health` не изменилась — контейнер не пересоздан:

```bash
docker compose -f compose.yaml -f compose.prod.yaml pull api
docker compose -f compose.yaml -f compose.prod.yaml up -d --force-recreate api
```

## 6. Локальная пересборка (dev, без ghcr)

```bash
docker compose up -d --build
docker compose logs -f api
```

## 7. Полный сброс окружения (данные БД будут потеряны)

```bash
docker compose down -v          # удаляет том pgdata
docker compose up -d --build
```

## 8. Конвейер красный

- `check` упал на Ruff: `uv run ruff check . --fix && uv run ruff format .`, затем коммит.
- `check` упал на тестах: `uv run pytest -x -vv` локально, при необходимости
  `DATABASE_URL=postgresql+psycopg://... uv run pytest` на реальном PostgreSQL.
- `release` упал на `verify`: тег не semver, стоит не на коммите из `main` или не совпадает
  с `version` в `pyproject.toml`. Исправьте и переставьте тег:

```bash
git tag -d v0.2.0 && git push origin :refs/tags/v0.2.0
git tag v0.2.0 && git push origin v0.2.0
```

- Образ не пушится в ghcr: проверьте, что у репозитория включены Actions с правом
  `packages: write` (Settings → Actions → General → Workflow permissions) и что имя
  образа в нижнем регистре.

## 9. Контакты и границы

Сервис демонстрационный, без аутентификации и SLA. Критичные данные — только каталог
комплектующих (`app/seed.py`, восстанавливается сидом) и созданные пользователями сборки
(том `pcbuilder_pgdata`). Резервная копия сборок:

```bash
docker compose exec -T db pg_dump -U pcbuilder pcbuilder > backup.sql
```
