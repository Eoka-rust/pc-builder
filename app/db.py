from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    return {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 5}


settings = get_settings()
engine = create_engine(
    settings.database_url, echo=settings.db_echo, **_engine_kwargs(settings.database_url)
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
