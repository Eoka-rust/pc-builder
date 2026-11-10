"""add released_year

Обратно совместимое расширение схемы (expand):
- новая колонка NULL-able, без значения по умолчанию и без изменения старых;
- старый код 0.1.0 её не читает и не пишет, INSERT подставляет NULL;
- данные для существующих строк дозаполняются отдельным UPDATE.

Revision ID: 0002_released_year
Revises: 0001_initial
Create Date: 2025-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_released_year"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RELEASED: list[tuple[str, str, int]] = [
    ("AMD", "Ryzen 5 7600", 2023),
    ("AMD", "Ryzen 7 7700", 2023),
    ("AMD", "Ryzen 7 7800X3D", 2023),
    ("AMD", "Ryzen 5 5600", 2022),
    ("Intel", "Core i5-12400F", 2022),
    ("Intel", "Core i5-14400F", 2024),
    ("Intel", "Core i7-14700KF", 2023),
    ("ASUS", "PRIME B650M-A WIFI", 2022),
    ("MSI", "B650 GAMING PLUS WIFI", 2023),
    ("Gigabyte", "B550M DS3H", 2021),
    ("ASUS", "PRIME H610M-K D4", 2022),
    ("MSI", "PRO B760M-A WIFI DDR4", 2023),
    ("ASUS", "TUF GAMING B760-PLUS WIFI D4", 2023),
    ("Kingston", "FURY Beast DDR5 16GB 5600", 2022),
    ("G.Skill", "Trident Z5 Neo DDR5 32GB (2x16) 6000", 2022),
    ("ADATA", "XPG Lancer DDR5 32GB (2x16) 6000", 2022),
    ("Patriot", "Viper Steel DDR4 16GB 3200", 2020),
    ("Kingston", "FURY Beast DDR4 16GB 3200", 2021),
    ("Palit", "GeForce RTX 4060 Dual 8GB", 2023),
    ("Palit", "GeForce RTX 4070 Super JetStream 12GB", 2024),
    ("GIGABYTE", "GeForce RTX 3060 Gaming OC 12GB", 2021),
    ("Sapphire", "PULSE Radeon RX 7600 8GB", 2023),
    ("Sapphire", "PULSE Radeon RX 7800 XT 16GB", 2023),
    ("be quiet!", "System Power 10 650W", 2021),
    ("DeepCool", "PF700 700W", 2022),
    ("Corsair", "RM750e 750W", 2023),
    ("Chieftec", "GPC-500S 500W", 2020),
    ("MSI", "MAG A650BN 650W", 2022),
    ("Zalman", "i3 Neo", 2021),
    ("DeepCool", "CH510", 2022),
    ("Cooler Master", "MasterBox Q300L", 2018),
    ("Zalman", "T8", 2020),
    ("Lian Li", "Lancool 216", 2022),
    ("DeepCool", "AK400", 2021),
    ("ID-COOLING", "SE-224-XT", 2019),
    ("Arctic", "Freezer A35", 2021),
    ("be quiet!", "Pure Rock 2", 2019),
    ("Noctua", "NH-U12S redux", 2021),
    ("Samsung", "980 1TB M.2", 2020),
    ("Kingston", "NV2 1TB M.2", 2022),
    ("WD", "Blue SN580 1TB M.2", 2023),
    ("Seagate", "Barracuda 2TB HDD", 2021),
    ("Crucial", "P3 Plus 2TB M.2", 2022),
]


def upgrade() -> None:
    op.add_column("components", sa.Column("released_year", sa.Integer(), nullable=True))

    components = sa.table(
        "components",
        sa.column("brand", sa.String),
        sa.column("model", sa.String),
        sa.column("released_year", sa.Integer),
    )
    for brand, model, year in RELEASED:
        op.execute(
            components.update()
            .where(sa.and_(components.c.brand == brand, components.c.model == model))
            .values(released_year=year)
        )


def downgrade() -> None:
    op.drop_column("components", "released_year")
