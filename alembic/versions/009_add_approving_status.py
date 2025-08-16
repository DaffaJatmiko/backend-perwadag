# File: alembic/versions/009_add_approving_status.py

"""Add APPROVING status to MatriksStatus enum

Revision ID: 009_add_approving_status
Revises: 007_add_status_tl
Create Date: 2025-08-15 XX:XX:XX.XXXXXX
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = '009_add_approving_status'
down_revision: Union[str, None] = '008_st_optional_file'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # ===== SKIP MECHANISM =====
    # Check if APPROVING value already exists in enum
    existing_values = connection.execute(sa.text(
        "SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'matriks_status')"
    )).fetchall()
    
    enum_values = [row[0] for row in existing_values]
    if 'APPROVING' in enum_values:
        print("⏭️ APPROVING status already exists in matriks_status enum, skipping")
        return
    
    # ===== ADD ENUM VALUE =====
    # Add APPROVING to matriks_status enum (before FINISHED)
    connection.execute(sa.text(
        "ALTER TYPE matriks_status ADD VALUE 'APPROVING' BEFORE 'FINISHED'"
    ))
    
    print("✅ Added APPROVING status to matriks_status enum")

def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values easily
    # This would require recreating the enum, which is risky for production
    # For now, we'll leave the enum value (it won't break anything)
    print("⚠️ Cannot remove enum value APPROVING (PostgreSQL limitation)")
    print("   Enum value will remain but won't be used")
    pass