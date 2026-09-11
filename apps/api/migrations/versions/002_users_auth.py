"""Users + auth allowlist + documents sha256 index.

Revision ID: 002_users_auth
Revises: 001_initial_schema
Create Date: 2026-09-10
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_users_auth"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("picture_url", sa.String(length=512), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="SENIOR_UNDERWRITER"),
        sa.Column("authorized", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("google_sub", sa.String(length=64), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('SENIOR_UNDERWRITER','RISK_ANALYST','COMPLIANCE_OFFICER')",
            name="ck_users_role",
        ),
        sa.PrimaryKeyConstraint("email"),
        sa.UniqueConstraint("google_sub"),
    )
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)
    # Hash lookup for dedup/audit (no UNIQUE: same file may legitimately repeat across dossiers).
    op.create_index("ix_documents_sha256", "documents", ["sha256"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_documents_sha256", table_name="documents")
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_table("users")
