"""Add matriks status flow for evaluasi berjenjang

Revision ID: 005_add_matrix_status_flow
Revises: 004_refactor_surat_tugas
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision: str = '005_add_matrix_status_flow'
down_revision: Union[str, None] = '004_refactor_surat_tugas'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # 1. Check if matriks_status enum already exists
    enum_exists = connection.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'matriks_status'"
    )).fetchone()
    
    if not enum_exists:
        # Create matriks_status enum
        connection.execute(sa.text(
            "CREATE TYPE matriks_status AS ENUM ('DRAFTING', 'CHECKING', 'VALIDATING', 'FINISHED')"
        ))
    
    # 2. Check if matriks table exists and status column doesn't exist
    table_exists = connection.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'matriks'"
    )).fetchone()
    
    if table_exists:
        # Check if status column already exists
        status_column_exists = connection.execute(sa.text(
            """SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'matriks' AND column_name = 'status'"""
        )).fetchone()
        
        if not status_column_exists:
            # Add status column
            op.add_column('matriks', sa.Column(
                'status', 
                sa.Enum('DRAFTING', 'CHECKING', 'VALIDATING', 'FINISHED', name='matriks_status'), 
                nullable=False,
                server_default='DRAFTING'
            ))
            
            # Set default value untuk existing records
            connection.execute(sa.text("UPDATE matriks SET status = 'DRAFTING' WHERE status IS NULL"))
            
            # Create index for performance
            op.create_index('ix_matriks_status', 'matriks', ['status'])

def downgrade() -> None:
    connection = op.get_bind()
    
    # Check if column exists before dropping
    status_column_exists = connection.execute(sa.text(
        """SELECT 1 FROM information_schema.columns 
           WHERE table_name = 'matriks' AND column_name = 'status'"""
    )).fetchone()
    
    if status_column_exists:
        # Drop index
        op.drop_index('ix_matriks_status', 'matriks')
        
        # Drop column
        op.drop_column('matriks', 'status')
    
    # Check if enum exists before dropping
    enum_exists = connection.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'matriks_status'"
    )).fetchone()
    
    if enum_exists:
        # Drop enum type
        connection.execute(sa.text("DROP TYPE IF EXISTS matriks_status"))