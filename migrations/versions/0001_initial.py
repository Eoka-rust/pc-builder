"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "components",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("brand", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("price_rub", sa.Integer(), nullable=False),
        sa.Column("socket", sa.String(length=32), nullable=True),
        sa.Column("memory_type", sa.String(length=16), nullable=True),
        sa.Column("form_factor", sa.String(length=16), nullable=True),
        sa.Column("supported_sockets", sa.String(length=128), nullable=True),
        sa.Column("supported_form_factors", sa.String(length=64), nullable=True),
        sa.Column("max_gpu_length_mm", sa.Integer(), nullable=True),
        sa.Column("tdp_w", sa.Integer(), nullable=True),
        sa.Column("length_mm", sa.Integer(), nullable=True),
        sa.Column("wattage_w", sa.Integer(), nullable=True),
        sa.Column("capacity_gb", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_components_category", "components", ["category"])

    op.create_table(
        "builds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "build_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("build_id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["build_id"], ["builds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["component_id"], ["components.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("build_id", "component_id", name="uq_build_component"),
    )
    op.create_index("ix_build_items_build_id", "build_items", ["build_id"])
    op.create_index("ix_build_items_component_id", "build_items", ["component_id"])


def downgrade() -> None:
    op.drop_index("ix_build_items_component_id", table_name="build_items")
    op.drop_index("ix_build_items_build_id", table_name="build_items")
    op.drop_table("build_items")
    op.drop_table("builds")
    op.drop_index("ix_components_category", table_name="components")
    op.drop_table("components")
