"""Add global status_tindak_lanjut column

Revision ID: 007_add_status_tl
Revises: 005_add_matrix_status_flow
Create Date: 2025-08-12 XX:XX:XX.XXXXXX
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, Inspector

revision: str = '007_add_status_tl'
down_revision: Union[str, None] = '006_meeting_datetime'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # ===== SKIP MECHANISM =====
    inspector = Inspector.from_engine(connection)
    try:
        columns = [col['name'] for col in inspector.get_columns('matriks')]
        if 'status_tindak_lanjut' in columns:
            print("⏭️ Column 'status_tindak_lanjut' already exists, skipping")
            return
    except:
        pass  # Proceed if check fails
    
    # ===== CREATE ENUM (if not exists) =====
    enum_exists = connection.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'tindaklanjutstatus'"
    )).fetchone()
    
    if not enum_exists:
        connection.execute(sa.text(
            "CREATE TYPE tindaklanjutstatus AS ENUM ('DRAFTING', 'CHECKING', 'VALIDATING', 'FINISHED')"
        ))
    
    # ===== ADD COLUMN (SIMPLE!) =====
    op.add_column('matriks', sa.Column(
        'status_tindak_lanjut', 
        sa.Enum('DRAFTING', 'CHECKING', 'VALIDATING', 'FINISHED', name='tindaklanjutstatus'),
        nullable=True  # ✅ SIMPLE: Just nullable, no complex migration
    ))
    
    # ===== CREATE INDEX =====
    op.create_index('ix_matriks_status_tindak_lanjut', 'matriks', ['status_tindak_lanjut'])
    
    print("✅ Added status_tindak_lanjut column")

def downgrade() -> None:
    op.drop_index('ix_matriks_status_tindak_lanjut', 'matriks')
    op.drop_column('matriks', 'status_tindak_lanjut')
    # Note: Enum will remain, that's OK