# PC Builder API

Подбор комплектующих ПК: каталог реальных комплектующих с характеристиками и проверка
совместимости сборки (сокет, тип памяти, форм-фактор, длина видеокарты, мощность БП).

Один небольшой сервис: FastAPI + PostgreSQL + Alembic, зависимости на uv, образ в ghcr.io,
релизы по git-тегам, откат на предыдущий тег.

- API-документация: `http://localhost:8000/docs`
- Аварийные действия: [RUNBOOK.md](RUNBOOK.md)
- История версий: [CHANGELOG.md](CHANGELOG.md)

## Быстрый старт (одна команда)

```bash
cp .env.example .env      # задайте POSTGRES_PASSWORD и GHCR_OWNER
docker compose up -d --build
curl http://localhost:8000/health
```

Ожидаемый ответ: `{"status":"ok","version":"0.0.0-dev","database":"ok"}`.
При первом старте контейнер применяет миграции Alembic и заливает каталог
(`SEED_ON_START=true`, повторно не дублируется).

Проверка сборки:

```bash
curl -X POST http://localhost:8000/builds/check -H "Content-Type: application/json" -d '{
  "name": "AM5 базовая",
  "items": [
    {"component_id": 1, "quantity": 1},
    {"component_id": 8, "quantity": 1},
    {"component_id": 14, "quantity": 2},
    {"component_id": 19, "quantity": 1},
    {"component_id": 24, "quantity": 1},
    {"component_id": 29, "quantity": 1},
    {"component_id": 34, "quantity": 1}
  ]}'
```

## Эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/health` | статус и версия образа (`APP_VERSION`), проверка БД |
| GET | `/version` | версия сервиса |
| GET | `/catalog/categories` | категории и количество позиций |
| GET | `/catalog/components?category=&search=&min_year=&limit=&offset=` | каталог с фильтрами |
| GET | `/catalog/components/{id}` | одна комплектующая |
| POST | `/builds/check` | проверить сборку без сохранения |
| POST | `/builds` | сохранить сборку (422 с причинами, если несовместима) |
| GET | `/builds`, `/builds/{id}` | список и карточка сборки |
| DELETE | `/builds/{id}` | удалить сборку |

Коды ошибок совместимости: `socket_mismatch`, `memory_type_mismatch`,
`form_factor_not_supported`, `cooler_socket_unsupported`, `gpu_too_long`,
`psu_too_weak`, `quantity_exceeded`, `missing_category`. Предупреждение
`psu_headroom_low` сохранение не блокирует.

## Разработка

```bash
uv sync                                        # зависимости строго по uv.lock
cp .env.example .env                           # DATABASE_URL берётся отсюда
uv run alembic upgrade head                    # схема
uv run uvicorn app.main:app --reload           # http://localhost:8000/docs
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

Python закреплён в `.python-version`, версии пакетов — в `uv.lock`; `uv sync --frozen`
в CI и в Dockerfile гарантирует одинаковое окружение.

## Данные каталога

Каталог — снимок реальных моделей комплектующих и их характеристик (сокет, TDP, длина
видеокарты, мощность БП, поддерживаемые форм-факторы). **Цены ориентировочные** на момент
релиза, а не live-прайс магазина. Никакого скрейпинга внешних сайтов в сервисе нет:
каталог — статический сид, поэтому сборка воспроизводима, CI не зависит от чужого сайта,
а демонстрация не ломается при изменении вёрстки магазина. Обновление цен — ручной импорт
своей выгрузки:

```bash
uv run python -m app.seed --csv prices.csv     # category,brand,model,price_rub
```

## Конфигурация

Все настройки — `pydantic-settings`, читаются из окружения и `.env` (см. `.env.example`):

| Переменная | По умолчанию | Смысл |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://pcbuilder:pcbuilder@localhost:5432/pcbuilder` | подключение к БД |
| `APP_VERSION` | `0.0.0-dev` | версия, подставляется в `/health` из тега при сборке образа |
| `SEED_ON_START` | `false` | залить каталог, если таблица пуста |
| `POSTGRES_PASSWORD` | — | пароль БД, в репозитории только `${...}` в compose |
| `GHCR_OWNER` | — | владелец образа в ghcr.io для прод-оверлея |

Секретов в репозитории нет: `.env` в `.gitignore`, в git лежит `.env.example`.

## Конвейер

1. `ci.yml` — на каждый `push` и `pull_request`: Ruff (lint + format check), обратимость
   миграций (`upgrade → downgrade → upgrade`) на реальном PostgreSQL, pytest.
2. `cd.yml` — только для `push` в `main`: job `image` стартует после `needs: check`
   и публикует `ghcr.io/<owner>/pc-builder:latest` и `:sha-<short>`.
3. `release.yml` — по тегу `vX.Y.Z`: проверяет, что тег semver, стоит на коммите из `main`
   и совпадает с `version` в `pyproject.toml`, прогоняет CI, публикует образ с тегом
   версии (`0.2.0`, `v0.2.0`, `latest`) и создаёт GitHub Release из раздела `CHANGELOG.md`.

Порядок выпуска версии:

```bash
# 1. версия в pyproject.toml + раздел в CHANGELOG.md
git commit -am "feat: ..."
git tag v0.2.0
git push origin main --tags
```

## Выкат и откат

Прод запускается из готового образа, без сборки на сервере:

```bash
# выкат версии 0.2.0
IMAGE_TAG=0.2.0 docker compose -f compose.yaml -f compose.prod.yaml up -d
curl http://localhost:8000/health          # version: 0.2.0

# откат на 0.1.0
IMAGE_TAG=0.1.0 docker compose -f compose.yaml -f compose.prod.yaml up -d
curl http://localhost:8000/health          # version: 0.1.0
```

Откат образа — отдельная операция, порядок зависит от того, пересекается ли граница
миграции; обе схемы описаны в разделе «Совместимость миграций» и в RUNBOOK.

## Совместимость миграций

Версия 0.2.0 добавляет в `components` колонку `released_year` — `NULL`-колонку без
значения по умолчанию и без изменений существующих столбцов:

- старый код (`0.1.0`) на новой схеме продолжает работать: он не выбирает и не пишет эту
  колонку, `INSERT` вставляет `NULL`, `NOT NULL`-ограничений нет;
- новый код на старой схеме не запускается, поэтому порядок выката — сначала миграция,
  затем новый код (это делает entrypoint контейнера);
- удаление и переименования не делаются в том же релизе: сначала добавление (expand),
  удаление — отдельным релизом, когда старый код выведен (contract).

Отсюда два разных случая отката, и их важно не путать:

| Откат | Что делать |
|---|---|
| в пределах одной ревизии схемы (`0.2.2 → 0.2.1 → 0.2.0`) | просто сменить тег образа, схема не трогается |
| через границу миграции (`0.2.x → 0.1.0`) | сначала `alembic downgrade 0001_initial` текущим образом, потом тег `0.1.0` |

Причина второго пункта: entrypoint запускает `alembic upgrade head`, а Alembic старого
образа не знает ревизии `0002_released_year` и падает с `Can't locate revision`. Сама схема
для старого кода совместима — несовместим запуск миграций из старого образа. Начиная с
0.2.2 миграции можно отключить (`RUN_MIGRATIONS=false`) и выполнять их отдельным шагом
деплоя; подробности — в [RUNBOOK.md](RUNBOOK.md), раздел 4.

## Структура

```
app/
  main.py           # приложение, lifespan, seed
  config.py         # pydantic-settings
  db.py             # engine, сессии
  models.py         # components, builds, build_items
  schemas.py        # pydantic-схемы API
  compatibility.py  # правила совместимости
  seed.py           # каталог + импорт цен из CSV
  routers/          # health, catalog, builds
migrations/         # Alembic
tests/              # pytest (юнит + API)
compose.yaml        # dev: сборка локально
compose.prod.yaml   # прод: образ из ghcr.io по IMAGE_TAG
```

## Ограничения

- Нет аутентификации: сервис демонстрационный, писать сборки может любой, у кого есть доступ.
- Расчёт мощности БП оценочный (TDP + 60 Вт базы + запас 35%), а не измерение.
- Каталог не обновляется автоматически; цены — статический снимок.
