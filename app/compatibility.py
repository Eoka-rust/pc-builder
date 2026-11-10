from dataclasses import dataclass, field
from enum import StrEnum
from math import ceil


class Category(StrEnum):
    cpu = "cpu"
    motherboard = "motherboard"
    ram = "ram"
    gpu = "gpu"
    psu = "psu"
    case = "case"
    cooler = "cooler"
    storage = "storage"


REQUIRED_CATEGORIES: tuple[Category, ...] = (
    Category.cpu,
    Category.motherboard,
    Category.ram,
    Category.psu,
    Category.case,
)

MAX_QUANTITY: dict[Category, int] = {
    Category.ram: 4,
    Category.storage: 4,
}

BASE_LOAD_W = 60
PSU_HEADROOM = 1.35


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    message: str


@dataclass(slots=True)
class Report:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    estimated_power_w: int = 0
    recommended_psu_w: int = 0
    total_price_rub: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _split(value: str | None) -> set[str]:
    if not value:
        return set()
    return {part.strip().upper() for part in value.split(",") if part.strip()}


def _one(rows: list[tuple], category: Category):
    for component, _quantity in rows:
        if component.category == category:
            return component
    return None


def _total(rows: list[tuple], category: Category) -> int:
    return sum(
        quantity * (component.capacity_gb or 0)
        for component, quantity in rows
        if component.category == category
    )


def evaluate(rows: list[tuple]) -> Report:
    """Проверяет совместимость набора (component, quantity).

    Ошибки блокируют сохранение сборки, предупреждения — только подсказки.
    """
    report = Report()

    counts: dict[str, int] = {}
    for component, quantity in rows:
        counts[component.category] = counts.get(component.category, 0) + quantity
        report.total_price_rub += component.price_rub * quantity
        limit = MAX_QUANTITY.get(component.category, 1)
        if quantity > limit:
            report.errors.append(
                Issue(
                    "quantity_exceeded",
                    f"{component.brand} {component.model}: максимум {limit} шт. "
                    f"для категории {component.category}",
                )
            )

    for category in REQUIRED_CATEGORIES:
        if category not in counts:
            report.errors.append(
                Issue("missing_category", f"В сборке нет комплектующей категории {category}")
            )

    cpu = _one(rows, Category.cpu)
    motherboard = _one(rows, Category.motherboard)
    case = _one(rows, Category.case)
    cooler = _one(rows, Category.cooler)
    psu = _one(rows, Category.psu)
    gpu = _one(rows, Category.gpu)
    rams = [component for component, _ in rows if component.category == Category.ram]

    if cpu and motherboard and (cpu.socket or "").upper() != (motherboard.socket or "").upper():
        report.errors.append(
            Issue(
                "socket_mismatch",
                f"Процессор {cpu.model} — сокет {cpu.socket}, "
                f"плата {motherboard.model} — сокет {motherboard.socket}",
            )
        )

    if motherboard:
        for ram in rams:
            if (ram.memory_type or "").upper() != (motherboard.memory_type or "").upper():
                report.errors.append(
                    Issue(
                        "memory_type_mismatch",
                        f"Память {ram.model} — {ram.memory_type}, "
                        f"плата поддерживает {motherboard.memory_type}",
                    )
                )

    if motherboard and case:
        supported = _split(case.supported_form_factors)
        if supported and (motherboard.form_factor or "").upper() not in supported:
            report.errors.append(
                Issue(
                    "form_factor_not_supported",
                    f"Корпус {case.model} не поддерживает платы {motherboard.form_factor}",
                )
            )

    if cpu and cooler:
        sockets = _split(cooler.supported_sockets)
        if sockets and (cpu.socket or "").upper() not in sockets:
            report.errors.append(
                Issue(
                    "cooler_socket_unsupported",
                    f"Кулер {cooler.model} не поддерживает сокет {cpu.socket}",
                )
            )

    if (
        gpu
        and case
        and gpu.length_mm
        and case.max_gpu_length_mm
        and gpu.length_mm > case.max_gpu_length_mm
    ):
        report.errors.append(
            Issue(
                "gpu_too_long",
                f"Видеокарта {gpu.model} ({gpu.length_mm} мм) не влезает в корпус "
                f"{case.model} (до {case.max_gpu_length_mm} мм)",
            )
        )

    storage_tb = _total(rows, Category.storage)
    ram_gb = _total(rows, Category.ram)
    report.estimated_power_w = (
        BASE_LOAD_W
        + (cpu.tdp_w or 0)
        + (gpu.tdp_w or 0)
        + (10 if ram_gb > 32 else 0)
        + (5 if storage_tb else 0)
    )
    report.recommended_psu_w = int(ceil(report.estimated_power_w * PSU_HEADROOM / 50) * 50)

    if psu and psu.wattage_w:
        if psu.wattage_w < report.estimated_power_w:
            report.errors.append(
                Issue(
                    "psu_too_weak",
                    f"Блок питания {psu.wattage_w} Вт слабее расчётного потребления "
                    f"{report.estimated_power_w} Вт",
                )
            )
        elif psu.wattage_w < report.recommended_psu_w:
            report.warnings.append(
                Issue(
                    "psu_headroom_low",
                    f"Блок питания {psu.wattage_w} Вт рабочий, но запас ниже рекомендуемых "
                    f"{report.recommended_psu_w} Вт",
                )
            )

    return report
