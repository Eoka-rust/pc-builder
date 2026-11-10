from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.compatibility import Report, evaluate
from app.db import get_session
from app.models import Build, BuildItem, Component
from app.schemas import (
    BuildBriefOut,
    BuildIn,
    BuildItemOut,
    BuildOut,
    BuildPage,
    CompatibilityOut,
    ComponentOut,
    ItemIn,
)

router = APIRouter(tags=["builds"])


def _load_items(session: Session, items: list[ItemIn]) -> list[tuple[Component, int]]:
    ids = {item.component_id for item in items}
    found = {c.id: c for c in session.scalars(select(Component).where(Component.id.in_(ids)))}
    missing = ids - found.keys()
    if missing:
        raise HTTPException(
            status_code=404,
            detail={"code": "component_not_found", "ids": sorted(missing)},
        )
    merged: dict[int, int] = {}
    for item in items:
        merged[item.component_id] = merged.get(item.component_id, 0) + item.quantity
    return [(found[cid], quantity) for cid, quantity in merged.items()]


def _report_out(report: Report) -> CompatibilityOut:
    return CompatibilityOut(
        ok=report.ok,
        errors=[{"code": e.code, "message": e.message} for e in report.errors],
        warnings=[{"code": w.code, "message": w.message} for w in report.warnings],
        estimated_power_w=report.estimated_power_w,
        recommended_psu_w=report.recommended_psu_w,
        total_price_rub=report.total_price_rub,
    )


def _build_out(build: Build) -> BuildOut:
    report = evaluate([(item.component, item.quantity) for item in build.items])
    return BuildOut(
        id=build.id,
        name=build.name,
        created_at=build.created_at,
        items=[
            BuildItemOut(
                component=ComponentOut.model_validate(item.component), quantity=item.quantity
            )
            for item in build.items
        ],
        total_price_rub=report.total_price_rub,
        estimated_power_w=report.estimated_power_w,
    )


@router.post("/check", response_model=CompatibilityOut)
def check_build(payload: BuildIn, session: Session = Depends(get_session)) -> CompatibilityOut:
    rows = _load_items(session, payload.items)
    return _report_out(evaluate(rows))


@router.post("", response_model=BuildOut, status_code=201)
def create_build(payload: BuildIn, session: Session = Depends(get_session)) -> BuildOut:
    rows = _load_items(session, payload.items)
    report = evaluate(rows)
    if not report.ok:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "incompatible_build",
                "errors": [{"code": e.code, "message": e.message} for e in report.errors],
                "warnings": [{"code": w.code, "message": w.message} for w in report.warnings],
            },
        )

    build = Build(name=payload.name)
    for component, quantity in rows:
        build.items.append(BuildItem(component_id=component.id, quantity=quantity))
    session.add(build)
    session.commit()
    session.refresh(build)
    return _build_out(build)


@router.get("", response_model=BuildPage)
def list_builds(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> BuildPage:
    total = session.scalar(select(func.count()).select_from(Build)) or 0
    builds = session.scalars(
        select(Build).order_by(Build.id.desc()).limit(limit).offset(offset)
    ).all()
    return BuildPage(
        items=[
            BuildBriefOut(
                id=b.id,
                name=b.name,
                created_at=b.created_at,
                total_price_rub=evaluate(
                    [(i.component, i.quantity) for i in b.items]
                ).total_price_rub,
            )
            for b in builds
        ],
        total=total,
    )


@router.get("/{build_id}", response_model=BuildOut)
def get_build(build_id: int, session: Session = Depends(get_session)) -> BuildOut:
    build = session.get(Build, build_id)
    if build is None:
        raise HTTPException(status_code=404, detail="build_not_found")
    return _build_out(build)


@router.delete("/{build_id}", status_code=204)
def delete_build(build_id: int, session: Session = Depends(get_session)) -> None:
    build = session.get(Build, build_id)
    if build is None:
        raise HTTPException(status_code=404, detail="build_not_found")
    session.delete(build)
    session.commit()
