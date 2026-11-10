from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.compatibility import Category
from app.db import get_session
from app.models import Component
from app.schemas import CategoryPage, ComponentOut, ComponentPage

router = APIRouter(tags=["catalog"])


@router.get("/categories", response_model=CategoryPage)
def list_categories(session: Session = Depends(get_session)) -> CategoryPage:
    rows = session.execute(
        select(Component.category, func.count(Component.id)).group_by(Component.category)
    ).all()
    items = [{"category": category, "count": count} for category, count in rows]
    items.sort(key=lambda item: item["category"])
    return CategoryPage(items=items)


@router.get("/components", response_model=ComponentPage)
def list_components(
    category: Category | None = None,
    search: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> ComponentPage:
    query = select(Component)
    if category is not None:
        query = query.where(Component.category == category.value)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(Component.brand.ilike(pattern), Component.model.ilike(pattern)))

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.scalars(
        query.order_by(Component.category, Component.brand, Component.model)
        .limit(limit)
        .offset(offset)
    ).all()

    return ComponentPage(
        items=[ComponentOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/components/{component_id}", response_model=ComponentOut)
def get_component(component_id: int, session: Session = Depends(get_session)) -> ComponentOut:
    component = session.get(Component, component_id)
    if component is None:
        raise HTTPException(status_code=404, detail="component_not_found")
    return ComponentOut.model_validate(component)
