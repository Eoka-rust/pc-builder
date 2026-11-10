import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db import SessionLocal
from app.routers import builds, catalog, health

logger = logging.getLogger("app")


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
    return app


app = create_app()
