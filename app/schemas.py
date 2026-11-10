from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.compatibility import Category


class ComponentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: Category
    brand: str
    model: str
    price_rub: int
    socket: str | None = None
    memory_type: str | None = None
    form_factor: str | None = None
    supported_sockets: str | None = None
    supported_form_factors: str | None = None
    max_gpu_length_mm: int | None = None
    tdp_w: int | None = None
    length_mm: int | None = None
    wattage_w: int | None = None
    capacity_gb: int | None = None
    released_year: int | None = None


class ComponentPage(BaseModel):
    items: list[ComponentOut]
    total: int
    limit: int
    offset: int
    price_note: str = (
        "Цены — ориентировочный снимок каталога на момент релиза, не live-прайс магазина."
    )


class CategoryCount(BaseModel):
    category: Category
    count: int


class CategoryPage(BaseModel):
    items: list[CategoryCount]


class ItemIn(BaseModel):
    component_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=4)


class BuildIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    items: list[ItemIn] = Field(min_length=1, max_length=32)


class IssueOut(BaseModel):
    code: str
    message: str


class CompatibilityOut(BaseModel):
    ok: bool
    errors: list[IssueOut]
    warnings: list[IssueOut]
    estimated_power_w: int
    recommended_psu_w: int
    total_price_rub: int


class BuildItemOut(BaseModel):
    component: ComponentOut
    quantity: int


class BuildOut(BaseModel):
    id: int
    name: str
    created_at: datetime | None
    items: list[BuildItemOut]
    total_price_rub: int
    estimated_power_w: int


class BuildBriefOut(BaseModel):
    id: int
    name: str
    created_at: datetime | None
    total_price_rub: int


class BuildPage(BaseModel):
    items: list[BuildBriefOut]
    total: int


class HealthOut(BaseModel):
    status: str
    version: str
    database: str
