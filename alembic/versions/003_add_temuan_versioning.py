"""Add temuan version field for conflict detection

Revision ID: 003_add_temuan_versioning
Revises: 002_add_complete_inspektorat_users
Create Date: 2025-01-28 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '003_add_temuan_versioning'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add temuan_version field safely."""
    connection = op.get_bind()
    
    # Check if temuan_version column exists
    version_exists = connection.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'matriks' AND column_name = 'temuan_version'
    """)).fetchone()
    
    if not version_exists:
        print("Adding temuan_version column...")
        op.add_column('matriks', sa.Column('temuan_version', sa.Integer(), nullable=False, server_default='0'))
        print("✅ temuan_version column added successfully!")
    else:
        print("temuan_version column already exists, skipping...")


def downgrade() -> None:
    """Remove temuan_version field safely."""
    connection = op.get_bind()
    
    # Check existence before drop
    version_exists = connection.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'matriks' AND column_name = 'temuan_version'
    """)).fetchone()
    
    if version_exists:
        op.drop_column('matriks', 'temuan_version')
        print("✅ temuan_version column removed!")
    else:
        print("temuan_version column doesn't exist, skipping...")