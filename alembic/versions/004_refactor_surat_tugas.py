"""Refactor surat tugas - add PIMPINAN role and update assignment fields

Revision ID: 004_refactor_surat_tugas
Revises: 003_add_temuan_versioning
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers
revision: str = '004_refactor_surat_tugas'
down_revision: Union[str, None] = '003_add_temuan_versioning'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # 1. Update UserRole enum (add PIMPINAN)
    # Check if PIMPINAN already exists
    result = connection.execute(sa.text(
        "SELECT 1 FROM pg_enum WHERE enumlabel = 'PIMPINAN' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole')"
    ))
    if not result.fetchone():
        connection.execute(sa.text("ALTER TYPE userrole ADD VALUE 'PIMPINAN'"))
    
    # 2. Check if surat_tugas table exists and has old structure
    table_exists = connection.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'surat_tugas'"
    )).fetchone()
    
    if table_exists:
        # Check if we need to update columns (check if old string columns exist)
        old_columns_exist = connection.execute(sa.text(
            """SELECT column_name FROM information_schema.columns 
               WHERE table_name = 'surat_tugas' 
               AND column_name IN ('nama_pengedali_mutu', 'nama_pengendali_teknis', 'nama_ketua_tim')"""
        )).fetchall()
        
        if old_columns_exist:
            # Drop old string columns
            op.drop_column('surat_tugas', 'nama_pengedali_mutu')
            op.drop_column('surat_tugas', 'nama_pengendali_teknis') 
            op.drop_column('surat_tugas', 'nama_ketua_tim')
            
            # Add new FK columns
            op.add_column('surat_tugas', sa.Column('pengedali_mutu_id', sa.String(36), nullable=True))
            op.add_column('surat_tugas', sa.Column('pengendali_teknis_id', sa.String(36), nullable=True))
            op.add_column('surat_tugas', sa.Column('ketua_tim_id', sa.String(36), nullable=True))
            op.add_column('surat_tugas', sa.Column('anggota_tim_ids', sa.Text(), nullable=True))
            op.add_column('surat_tugas', sa.Column('pimpinan_inspektorat_id', sa.String(36), nullable=True))
            
            # Add foreign key constraints
            op.create_foreign_key('fk_surat_tugas_pengedali_mutu', 'surat_tugas', 'users', ['pengedali_mutu_id'], ['id'])
            op.create_foreign_key('fk_surat_tugas_pengendali_teknis', 'surat_tugas', 'users', ['pengendali_teknis_id'], ['id'])
            op.create_foreign_key('fk_surat_tugas_ketua_tim', 'surat_tugas', 'users', ['ketua_tim_id'], ['id'])
            op.create_foreign_key('fk_surat_tugas_pimpinan_inspektorat', 'surat_tugas', 'users', ['pimpinan_inspektorat_id'], ['id'])
            
            # Add indexes for performance
            op.create_index('ix_surat_tugas_pengedali_mutu_id', 'surat_tugas', ['pengedali_mutu_id'])
            op.create_index('ix_surat_tugas_pengendali_teknis_id', 'surat_tugas', ['pengendali_teknis_id'])
            op.create_index('ix_surat_tugas_ketua_tim_id', 'surat_tugas', ['ketua_tim_id'])
            op.create_index('ix_surat_tugas_pimpinan_inspektorat_id', 'surat_tugas', ['pimpinan_inspektorat_id'])

def downgrade() -> None:
    connection = op.get_bind()
    
    # Drop new columns and constraints
    op.drop_constraint('fk_surat_tugas_pimpinan_inspektorat', 'surat_tugas', type_='foreignkey')
    op.drop_constraint('fk_surat_tugas_ketua_tim', 'surat_tugas', type_='foreignkey')
    op.drop_constraint('fk_surat_tugas_pengendali_teknis', 'surat_tugas', type_='foreignkey')
    op.drop_constraint('fk_surat_tugas_pengedali_mutu', 'surat_tugas', type_='foreignkey')
    
    op.drop_index('ix_surat_tugas_pimpinan_inspektorat_id', 'surat_tugas')
    op.drop_index('ix_surat_tugas_ketua_tim_id', 'surat_tugas')
    op.drop_index('ix_surat_tugas_pengendali_teknis_id', 'surat_tugas')
    op.drop_index('ix_surat_tugas_pengedali_mutu_id', 'surat_tugas')
    
    op.drop_column('surat_tugas', 'pimpinan_inspektorat_id')
    op.drop_column('surat_tugas', 'anggota_tim_ids')
    op.drop_column('surat_tugas', 'ketua_tim_id')
    op.drop_column('surat_tugas', 'pengendali_teknis_id')
    op.drop_column('surat_tugas', 'pengedali_mutu_id')
    
    # Add back old string columns
    op.add_column('surat_tugas', sa.Column('nama_pengedali_mutu', sa.String(200), nullable=False))
    op.add_column('surat_tugas', sa.Column('nama_pengendali_teknis', sa.String(200), nullable=False))
    op.add_column('surat_tugas', sa.Column('nama_ketua_tim', sa.String(200), nullable=False))