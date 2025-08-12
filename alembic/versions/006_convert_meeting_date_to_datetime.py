"""Convert meeting tanggal_meeting from date to datetime with timezone

Revision ID: 006_meeting_datetime
Revises: 004_refactor_surat_tugas
Create Date: 2025-08-12 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers
revision: str = '006_meeting_datetime'
down_revision: Union[str, None] = '005_add_matrix_status_flow'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert tanggal_meeting from date to timestamptz."""
    connection = op.get_bind()
    
    # Check if meetings table exists
    table_exists = connection.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'meetings'"
    )).fetchone()
    
    if not table_exists:
        print("❌ meetings table tidak ditemukan, skipping migration...")
        return
    
    # Check current column type
    current_type = connection.execute(text("""
        SELECT data_type FROM information_schema.columns 
        WHERE table_name = 'meetings' AND column_name = 'tanggal_meeting'
    """)).fetchone()
    
    if not current_type:
        print("❌ tanggal_meeting column tidak ditemukan, skipping migration...")
        return
    
    current_data_type = current_type[0]
    
    # If already timestamptz, skip
    if current_data_type == 'timestamp with time zone':
        print("✅ tanggal_meeting sudah dalam format timestamptz, migration tidak diperlukan")
        return
    
    # If not date type, warn and skip
    if current_data_type != 'date':
        print(f"⚠️  tanggal_meeting type adalah {current_data_type}, bukan date. Skipping migration...")
        return
    
    print("🔄 Converting tanggal_meeting from date to timestamptz...")
    
    # Step 1: Add new column
    print("   → Adding temporary column...")
    op.add_column('meetings', 
        sa.Column('tanggal_meeting_new', 
                 postgresql.TIMESTAMP(timezone=True), 
                 nullable=True)
    )
    
    # Step 2: Migrate data - convert date to datetime at 09:00 AM Jakarta (UTC+7)
    print("   → Migrating existing data (09:00 AM Jakarta → 02:00 AM UTC)...")
    connection.execute(text("""
        UPDATE meetings 
        SET tanggal_meeting_new = (tanggal_meeting + TIME '02:00:00') AT TIME ZONE 'UTC'
        WHERE tanggal_meeting IS NOT NULL
    """))
    
    # Step 3: Drop old column
    print("   → Dropping old column...")
    op.drop_column('meetings', 'tanggal_meeting')
    
    # Step 4: Rename new column
    print("   → Renaming new column...")
    op.alter_column('meetings', 'tanggal_meeting_new', new_column_name='tanggal_meeting')
    
    print("✅ Successfully converted tanggal_meeting to timestamptz!")


def downgrade() -> None:
    """Revert back to date field (time info will be lost)."""
    connection = op.get_bind()
    
    # Check if meetings table exists
    table_exists = connection.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'meetings'"
    )).fetchone()
    
    if not table_exists:
        print("❌ meetings table tidak ditemukan, skipping downgrade...")
        return
    
    # Check current column type
    current_type = connection.execute(text("""
        SELECT data_type FROM information_schema.columns 
        WHERE table_name = 'meetings' AND column_name = 'tanggal_meeting'
    """)).fetchone()
    
    if not current_type:
        print("❌ tanggal_meeting column tidak ditemukan, skipping downgrade...")
        return
    
    current_data_type = current_type[0]
    
    # If already date, skip
    if current_data_type == 'date':
        print("✅ tanggal_meeting sudah dalam format date, downgrade tidak diperlukan")
        return
    
    print("🔄 Converting back to date (time info will be lost)...")
    
    # Step 1: Add temp date column
    print("   → Adding temporary date column...")
    op.add_column('meetings', 
        sa.Column('tanggal_meeting_temp', sa.Date, nullable=True)
    )
    
    # Step 2: Convert back to date - extract date part only
    print("   → Converting datetime to date...")
    connection.execute(text("""
        UPDATE meetings 
        SET tanggal_meeting_temp = (tanggal_meeting AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta')::date
        WHERE tanggal_meeting IS NOT NULL
    """))
    
    # Step 3: Drop datetime column
    print("   → Dropping datetime column...")
    op.drop_column('meetings', 'tanggal_meeting')
    
    # Step 4: Rename
    print("   → Renaming...")
    op.alter_column('meetings', 'tanggal_meeting_temp', new_column_name='tanggal_meeting')
    
    print("✅ Reverted to date field (time information lost)")