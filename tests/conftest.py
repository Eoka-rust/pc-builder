import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite://")
os.environ.setdefault("APP_VERSION", "0.0.0-test")
os.environ.setdefault("SEED_ON_START", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Build, BuildItem
from app.seed import load_default


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        load_default(session)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_builds():
    yield
    with SessionLocal() as session:
        session.execute(delete(BuildItem))
        session.execute(delete(Build))
        session.commit()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def catalog(client) -> dict[str, dict]:
    response = client.get("/catalog/components", params={"limit": 200})
    assert response.status_code == 200
    return {item["model"]: item for item in response.json()["items"]}
