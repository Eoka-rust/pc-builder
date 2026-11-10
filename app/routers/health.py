from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.schemas import HealthOut

router = APIRouter(tags=["service"])


@router.get("/health", response_model=HealthOut)
def health(response: Response, session: Session = Depends(get_session)) -> HealthOut:
    settings = get_settings()
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = 503
        return HealthOut(status="degraded", version=settings.app_version, database="unavailable")
    return HealthOut(status="ok", version=settings.app_version, database="ok")


@router.get("/version")
def version() -> dict[str, str]:
    return {"version": get_settings().app_version}
