"""Answer synthesis fields on failed_questions.

Civic question attempts now carry the synthesized answer, the structured
findings behind it, evidence citations, and a confidence score — so answers
can be manually verified and partial information is preserved on failure.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-06
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("failed_questions", sa.Column("answer", sa.Text(), nullable=True))
    op.add_column("failed_questions", sa.Column("findings_json", sa.JSON(), nullable=True))
    op.add_column("failed_questions", sa.Column("evidence_json", sa.JSON(), nullable=True))
    op.add_column(
        "failed_questions",
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("failed_questions", "confidence")
    op.drop_column("failed_questions", "evidence_json")
    op.drop_column("failed_questions", "findings_json")
    op.drop_column("failed_questions", "answer")
