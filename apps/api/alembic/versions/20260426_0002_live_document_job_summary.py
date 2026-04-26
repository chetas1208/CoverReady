"""live document job summary

Revision ID: 20260426_0002
Revises: 20260425_0001
Create Date: 2026-04-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260426_0002"
down_revision = "20260425_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("latest_job_stage", sa.String(length=32), nullable=True))
    op.add_column("documents", sa.Column("latest_job_attempt", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("latest_error", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE documents SET updated_at = created_at WHERE updated_at IS NULL")


def downgrade() -> None:
    op.drop_column("documents", "updated_at")
    op.drop_column("documents", "latest_error")
    op.drop_column("documents", "latest_job_attempt")
    op.drop_column("documents", "latest_job_stage")
