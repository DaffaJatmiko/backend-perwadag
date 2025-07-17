"""refactor_user_remove_fields

Revision ID: 8822222c91e6
Revises: 8cb7dc59dc77
Create Date: 2025-07-17 21:46:53.905312

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy import text



# revision identifiers, used by Alembic.
revision: str = '8822222c91e6'
down_revision: Union[str, Sequence[str], None] = '8cb7dc59dc77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Step 1: Create backup table
    op.execute("""
        CREATE TABLE user_backup AS 
        SELECT id, username, nama, tanggal_lahir, tempat_lahir, pangkat, inspektorat, role 
        FROM users;
    """)
    
    # Step 2: Update existing usernames for admin/inspektorat
    bind = op.get_bind()
    session = Session(bind=bind)
    
    # Function to clean and get first name
    session.execute(text("""
        CREATE OR REPLACE FUNCTION clean_first_name(input_name TEXT) 
        RETURNS TEXT AS $$
        BEGIN
            RETURN LOWER(TRIM(SPLIT_PART(input_name, ' ', 1)));
        END;
        $$ LANGUAGE plpgsql;
    """))
    
    # Update admin/inspektorat usernames
    session.execute(text("""
        UPDATE users 
        SET username = clean_first_name(nama) || '_ir' || 
            CASE 
                WHEN inspektorat LIKE '%1%' THEN '1'
                WHEN inspektorat LIKE '%2%' THEN '2'
                WHEN inspektorat LIKE '%3%' THEN '3'
                WHEN inspektorat LIKE '%4%' THEN '4'
                ELSE '1'
            END
        WHERE role IN ('ADMIN', 'INSPEKTORAT');
    """))
    
    # Handle username conflicts - add second name
    session.execute(text("""
        WITH conflict_users AS (
            SELECT id, nama, username, inspektorat, role,
                   ROW_NUMBER() OVER (PARTITION BY username ORDER BY id) as rn
            FROM users 
            WHERE role IN ('ADMIN', 'INSPEKTORAT')
        )
        UPDATE users 
        SET username = clean_first_name(conflict_users.nama) || '_' || 
                      LOWER(TRIM(SPLIT_PART(conflict_users.nama, ' ', 2))) || '_ir' || 
                      CASE 
                          WHEN conflict_users.inspektorat LIKE '%1%' THEN '1'
                          WHEN conflict_users.inspektorat LIKE '%2%' THEN '2'
                          WHEN conflict_users.inspektorat LIKE '%3%' THEN '3'
                          WHEN conflict_users.inspektorat LIKE '%4%' THEN '4'
                          ELSE '1'
                      END
        FROM conflict_users
        WHERE users.id = conflict_users.id 
        AND conflict_users.rn > 1
        AND SPLIT_PART(conflict_users.nama, ' ', 2) != '';
    """))
    
    # Clean up function
    session.execute(text("DROP FUNCTION clean_first_name(TEXT);"))
    
    # Step 3: Drop the columns
    op.drop_column('users', 'tanggal_lahir')
    op.drop_column('users', 'tempat_lahir')
    op.drop_column('users', 'pangkat')
    
    session.commit()

def downgrade():
    # Add columns back
    op.add_column('users', sa.Column('tanggal_lahir', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('tempat_lahir', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('pangkat', sa.String(100), nullable=True))
    
    # Restore data from backup
    op.execute("""
        UPDATE users 
        SET tanggal_lahir = ub.tanggal_lahir,
            tempat_lahir = ub.tempat_lahir,
            pangkat = ub.pangkat,
            username = ub.username
        FROM user_backup ub 
        WHERE users.id = ub.id;
    """)
    
    # Drop backup table
    op.drop_table('user_backup')