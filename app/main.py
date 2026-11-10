import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import SessionLocal
from app.routers import builds, catalog, health

logger = logging.getLogger("app")

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.seed_on_start:
        from app.seed import load_default

        with SessionLocal() as session:
            added = load_default(session)
        logger.info("seed: добавлено комплектующих %s", added)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        summary="Каталог комплектующих ПК и проверка совместимости сборки",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(catalog.router, prefix="/catalog")
    app.include_router(builds.router, prefix="/builds")

    # Монтируется последним: маршруты API объявлены выше и матчатся первыми.
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
    return app


app = create_app()
