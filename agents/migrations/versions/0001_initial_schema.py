"""Initial schema — all core tables.

Bootstraps from the ORM metadata so the schema has a single source of truth
(gov_oracle_agents.storage.orm). Subsequent migrations must use explicit
Alembic operations generated with `alembic revision --autogenerate`.

Revision ID: 0001
Revises:
Create Date: 2026-07-04
"""
from alembic import op

from gov_oracle_agents.storage.orm import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
