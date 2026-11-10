from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Component(Base):
    """Комплектующая. Одна таблица на все категории: поля специфичны,
    но их немного, а фильтры и совместимость работают одинаково."""

    __tablename__ = "components"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    brand: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    price_rub: Mapped[int] = mapped_column(Integer)

    # cpu / motherboard
    socket: Mapped[str | None] = mapped_column(String(32))
    # motherboard / ram
    memory_type: Mapped[str | None] = mapped_column(String(16))
    # motherboard
    form_factor: Mapped[str | None] = mapped_column(String(16))
    # cooler: список поддерживаемых сокетов через запятую
    supported_sockets: Mapped[str | None] = mapped_column(String(128))
    # case: список поддерживаемых форм-факторов плат
    supported_form_factors: Mapped[str | None] = mapped_column(String(64))
    # case
    max_gpu_length_mm: Mapped[int | None] = mapped_column(Integer)

    # cpu / gpu
    tdp_w: Mapped[int | None] = mapped_column(Integer)
    # gpu
    length_mm: Mapped[int | None] = mapped_column(Integer)
    # psu
    wattage_w: Mapped[int | None] = mapped_column(Integer)
    # ram / storage
    capacity_gb: Mapped[int | None] = mapped_column(Integer)
    # год выхода модели на рынок (появился в 0.2.0, допускает NULL)
    released_year: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - отладочное
        return f"<Component {self.category} {self.brand} {self.model}>"


class Build(Base):
    __tablename__ = "builds"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    items: Mapped[list["BuildItem"]] = relationship(
        back_populates="build",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="BuildItem.id",
    )


class BuildItem(Base):
    __tablename__ = "build_items"
    __table_args__ = (UniqueConstraint("build_id", "component_id", name="uq_build_component"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    build_id: Mapped[int] = mapped_column(ForeignKey("builds.id", ondelete="CASCADE"), index=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    build: Mapped[Build] = relationship(back_populates="items")
    component: Mapped[Component] = relationship(lazy="joined")
