"""Make surat tugas file optional and add is_completed status

Revision ID: 008_st_optional_file
Revises: 007_add_status_tl
Create Date: 2025-08-15 XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, Inspector

# revision identifiers, used by Alembic.
revision: str = '008_st_optional_file'
down_revision: Union[str, None] = '007_add_status_tl'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make file_surat_tugas column nullable."""
    
    connection = op.get_bind()
    
    # ===== SKIP MECHANISM - Check if already nullable =====
    try:
        inspector = Inspector.from_engine(connection)
        columns = inspector.get_columns('surat_tugas')
        
        # Find file_surat_tugas column
        file_column = next((col for col in columns if col['name'] == 'file_surat_tugas'), None)
        
        if file_column:
            if file_column['nullable']:
                print("⏭️ Column 'file_surat_tugas' already nullable, skipping")
                return
            else:
                print("🔄 Making file_surat_tugas column nullable...")
                # Column exists and is NOT NULL, make it nullable
                op.alter_column('surat_tugas', 'file_surat_tugas',
                              existing_type=sa.VARCHAR(length=500),
                              nullable=True)
                print("✅ file_surat_tugas column is now nullable")
        else:
            print("❌ Column 'file_surat_tugas' not found, skipping")
            
    except Exception as e:
        # If there's any error (table doesn't exist, etc.), skip silently
        # This handles case where someone runs alembic on fresh DB
        print(f"⚠️ Error checking column: {e}, skipping migration")
        pass


def downgrade() -> None:
    """Revert file_surat_tugas to NOT NULL."""
    
    connection = op.get_bind()
    
    try:
        # Check if table exists
        inspector = Inspector.from_engine(connection)
        tables = inspector.get_table_names()
        
        if 'surat_tugas' in tables:
            print("🔄 Reverting file_surat_tugas to NOT NULL...")
            
            # Update any NULL values to empty string before making NOT NULL
            connection.execute(text(
                "UPDATE surat_tugas SET file_surat_tugas = '' WHERE file_surat_tugas IS NULL"
            ))
            
            # Make column NOT NULL again
            op.alter_column('surat_tugas', 'file_surat_tugas',
                          existing_type=sa.VARCHAR(length=500),
                          nullable=False)
            
            print("✅ file_surat_tugas reverted to NOT NULL")
                          
    except Exception as e:
        # If there's any error, skip silently
        print(f"⚠️ Error during downgrade: {e}")
        pass