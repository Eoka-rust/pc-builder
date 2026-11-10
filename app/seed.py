"""Каталог реальных комплектующих.

Цены — ориентировочный снимок розницы РФ на момент подготовки релиза
(осень 2025), а не live-прайс магазина. Источник моделей и характеристик —
открытые карточки товаров и спецификации производителей.
Скрипт идемпотентен: повторный запуск не дублирует записи.

Обновление цен из выгрузки: python -m app.seed --csv prices.csv
Формат CSV: category,brand,model,price_rub
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Component

COMPONENTS: list[dict] = [
    # --- CPU ---
    {
        "category": "cpu",
        "brand": "AMD",
        "model": "Ryzen 5 7600",
        "price_rub": 22990,
        "socket": "AM5",
        "tdp_w": 65,
    },
    {
        "category": "cpu",
        "brand": "AMD",
        "model": "Ryzen 7 7700",
        "price_rub": 32990,
        "socket": "AM5",
        "tdp_w": 65,
    },
    {
        "category": "cpu",
        "brand": "AMD",
        "model": "Ryzen 7 7800X3D",
        "price_rub": 49990,
        "socket": "AM5",
        "tdp_w": 120,
    },
    {
        "category": "cpu",
        "brand": "AMD",
        "model": "Ryzen 5 5600",
        "price_rub": 10990,
        "socket": "AM4",
        "tdp_w": 65,
    },
    {
        "category": "cpu",
        "brand": "Intel",
        "model": "Core i5-12400F",
        "price_rub": 12990,
        "socket": "LGA1700",
        "tdp_w": 65,
    },
    {
        "category": "cpu",
        "brand": "Intel",
        "model": "Core i5-14400F",
        "price_rub": 17990,
        "socket": "LGA1700",
        "tdp_w": 65,
    },
    {
        "category": "cpu",
        "brand": "Intel",
        "model": "Core i7-14700KF",
        "price_rub": 39990,
        "socket": "LGA1700",
        "tdp_w": 125,
    },
    # --- Motherboard ---
    {
        "category": "motherboard",
        "brand": "ASUS",
        "model": "PRIME B650M-A WIFI",
        "price_rub": 15990,
        "socket": "AM5",
        "memory_type": "DDR5",
        "form_factor": "mATX",
    },
    {
        "category": "motherboard",
        "brand": "MSI",
        "model": "B650 GAMING PLUS WIFI",
        "price_rub": 18990,
        "socket": "AM5",
        "memory_type": "DDR5",
        "form_factor": "ATX",
    },
    {
        "category": "motherboard",
        "brand": "Gigabyte",
        "model": "B550M DS3H",
        "price_rub": 8990,
        "socket": "AM4",
        "memory_type": "DDR4",
        "form_factor": "mATX",
    },
    {
        "category": "motherboard",
        "brand": "ASUS",
        "model": "PRIME H610M-K D4",
        "price_rub": 7490,
        "socket": "LGA1700",
        "memory_type": "DDR4",
        "form_factor": "mATX",
    },
    {
        "category": "motherboard",
        "brand": "MSI",
        "model": "PRO B760M-A WIFI DDR4",
        "price_rub": 13990,
        "socket": "LGA1700",
        "memory_type": "DDR4",
        "form_factor": "mATX",
    },
    {
        "category": "motherboard",
        "brand": "ASUS",
        "model": "TUF GAMING B760-PLUS WIFI D4",
        "price_rub": 19990,
        "socket": "LGA1700",
        "memory_type": "DDR4",
        "form_factor": "ATX",
    },
    # --- RAM ---
    {
        "category": "ram",
        "brand": "Kingston",
        "model": "FURY Beast DDR5 16GB 5600",
        "price_rub": 5490,
        "memory_type": "DDR5",
        "capacity_gb": 16,
    },
    {
        "category": "ram",
        "brand": "G.Skill",
        "model": "Trident Z5 Neo DDR5 32GB (2x16) 6000",
        "price_rub": 12990,
        "memory_type": "DDR5",
        "capacity_gb": 32,
    },
    {
        "category": "ram",
        "brand": "ADATA",
        "model": "XPG Lancer DDR5 32GB (2x16) 6000",
        "price_rub": 11990,
        "memory_type": "DDR5",
        "capacity_gb": 32,
    },
    {
        "category": "ram",
        "brand": "Patriot",
        "model": "Viper Steel DDR4 16GB 3200",
        "price_rub": 3790,
        "memory_type": "DDR4",
        "capacity_gb": 16,
    },
    {
        "category": "ram",
        "brand": "Kingston",
        "model": "FURY Beast DDR4 16GB 3200",
        "price_rub": 4190,
        "memory_type": "DDR4",
        "capacity_gb": 16,
    },
    # --- GPU ---
    {
        "category": "gpu",
        "brand": "Palit",
        "model": "GeForce RTX 4060 Dual 8GB",
        "price_rub": 34990,
        "tdp_w": 115,
        "length_mm": 260,
    },
    {
        "category": "gpu",
        "brand": "Palit",
        "model": "GeForce RTX 4070 Super JetStream 12GB",
        "price_rub": 69990,
        "tdp_w": 220,
        "length_mm": 328,
    },
    {
        "category": "gpu",
        "brand": "GIGABYTE",
        "model": "GeForce RTX 3060 Gaming OC 12GB",
        "price_rub": 32990,
        "tdp_w": 170,
        "length_mm": 282,
    },
    {
        "category": "gpu",
        "brand": "Sapphire",
        "model": "PULSE Radeon RX 7600 8GB",
        "price_rub": 28990,
        "tdp_w": 165,
        "length_mm": 240,
    },
    {
        "category": "gpu",
        "brand": "Sapphire",
        "model": "PULSE Radeon RX 7800 XT 16GB",
        "price_rub": 59990,
        "tdp_w": 263,
        "length_mm": 313,
    },
    # --- PSU ---
    {
        "category": "psu",
        "brand": "be quiet!",
        "model": "System Power 10 650W",
        "price_rub": 6990,
        "wattage_w": 650,
    },
    {
        "category": "psu",
        "brand": "DeepCool",
        "model": "PF700 700W",
        "price_rub": 4990,
        "wattage_w": 700,
    },
    {
        "category": "psu",
        "brand": "Corsair",
        "model": "RM750e 750W",
        "price_rub": 12990,
        "wattage_w": 750,
    },
    {
        "category": "psu",
        "brand": "Chieftec",
        "model": "GPC-500S 500W",
        "price_rub": 3490,
        "wattage_w": 500,
    },
    {
        "category": "psu",
        "brand": "MSI",
        "model": "MAG A650BN 650W",
        "price_rub": 5490,
        "wattage_w": 650,
    },
    # --- Case ---
    {
        "category": "case",
        "brand": "Zalman",
        "model": "i3 Neo",
        "price_rub": 4290,
        "supported_form_factors": "ATX,mATX,Mini-ITX",
        "max_gpu_length_mm": 330,
    },
    {
        "category": "case",
        "brand": "DeepCool",
        "model": "CH510",
        "price_rub": 6490,
        "supported_form_factors": "ATX,mATX,Mini-ITX",
        "max_gpu_length_mm": 380,
    },
    {
        "category": "case",
        "brand": "Cooler Master",
        "model": "MasterBox Q300L",
        "price_rub": 4990,
        "supported_form_factors": "MATX,MINI-ITX",
        "max_gpu_length_mm": 360,
    },
    {
        "category": "case",
        "brand": "Zalman",
        "model": "T8",
        "price_rub": 2990,
        "supported_form_factors": "ATX,mATX,Mini-ITX",
        "max_gpu_length_mm": 300,
    },
    {
        "category": "case",
        "brand": "Lian Li",
        "model": "Lancool 216",
        "price_rub": 11990,
        "supported_form_factors": "ATX,mATX,Mini-ITX",
        "max_gpu_length_mm": 392,
    },
    # --- Cooler ---
    {
        "category": "cooler",
        "brand": "DeepCool",
        "model": "AK400",
        "price_rub": 2890,
        "supported_sockets": "AM4,AM5,LGA1700,LGA1200",
    },
    {
        "category": "cooler",
        "brand": "ID-COOLING",
        "model": "SE-224-XT",
        "price_rub": 1990,
        "supported_sockets": "AM4,AM5,LGA1700",
    },
    {
        "category": "cooler",
        "brand": "Arctic",
        "model": "Freezer A35",
        "price_rub": 2490,
        "supported_sockets": "AM4,AM5",
    },
    {
        "category": "cooler",
        "brand": "be quiet!",
        "model": "Pure Rock 2",
        "price_rub": 3990,
        "supported_sockets": "AM4,AM5,LGA1700,LGA1200",
    },
    {
        "category": "cooler",
        "brand": "Noctua",
        "model": "NH-U12S redux",
        "price_rub": 5990,
        "supported_sockets": "AM4,AM5,LGA1700,LGA1200",
    },
    # --- Storage ---
    {
        "category": "storage",
        "brand": "Samsung",
        "model": "980 1TB M.2",
        "price_rub": 7490,
        "capacity_gb": 1000,
    },
    {
        "category": "storage",
        "brand": "Kingston",
        "model": "NV2 1TB M.2",
        "price_rub": 5490,
        "capacity_gb": 1000,
    },
    {
        "category": "storage",
        "brand": "WD",
        "model": "Blue SN580 1TB M.2",
        "price_rub": 6990,
        "capacity_gb": 1000,
    },
    {
        "category": "storage",
        "brand": "Seagate",
        "model": "Barracuda 2TB HDD",
        "price_rub": 5990,
        "capacity_gb": 2000,
    },
    {
        "category": "storage",
        "brand": "Crucial",
        "model": "P3 Plus 2TB M.2",
        "price_rub": 12990,
        "capacity_gb": 2000,
    },
]


def load_default(session: Session, reset: bool = False) -> int:
    """Заливает каталог, если таблица пуста. Возвращает число добавленных записей."""
    if reset:
        session.query(Component).delete()
        session.commit()

    existing = session.scalar(select(func.count()).select_from(Component)) or 0
    if existing:
        return 0

    session.add_all([Component(**row) for row in COMPONENTS])
    session.commit()
    return len(COMPONENTS)


def update_prices(session: Session, csv_path: Path) -> int:
    """Обновляет цены по выгрузке category,brand,model,price_rub."""
    updated = 0
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            component = session.scalar(
                select(Component).where(
                    Component.category == row["category"].strip(),
                    Component.brand == row["brand"].strip(),
                    Component.model == row["model"].strip(),
                )
            )
            if component is None:
                print(f"нет в каталоге: {row}", file=sys.stderr)
                continue
            component.price_rub = int(row["price_rub"])
            updated += 1
    session.commit()
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Каталог комплектующих")
    parser.add_argument("--reset", action="store_true", help="удалить текущий каталог")
    parser.add_argument("--csv", type=Path, help="выгрузка цен для обновления")
    args = parser.parse_args()

    with SessionLocal() as session:
        if args.csv:
            print(f"обновлено цен: {update_prices(session, args.csv)}")
        else:
            print(f"добавлено комплектующих: {load_default(session, reset=args.reset)}")


if __name__ == "__main__":
    main()
