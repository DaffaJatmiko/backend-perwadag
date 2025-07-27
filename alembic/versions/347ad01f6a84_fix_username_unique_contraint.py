"""fix username unique contraint

Revision ID: 347ad01f6a84
Revises: d6be4a5887e9
Create Date: 2025-07-27 08:41:39.935593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '347ad01f6a84'
down_revision: Union[str, Sequence[str], None] = 'd6be4a5887e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Replace ix_users_username with partial unique index for soft delete support"""
    
    conn = op.get_bind()
    
    print("🔍 Checking current username constraint...")
    
    # Step 1: Verify current index exists
    result = conn.execute(text("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'users' 
        AND indexname = 'ix_users_username'
    """))
    
    current_index = result.fetchone()
    if not current_index:
        print("❌ ix_users_username not found. Migration may not be needed.")
        return
    
    print("✅ Found ix_users_username - proceeding with replacement")
    
    # Step 2: Drop existing unique index
    print("📝 Dropping existing unique index: ix_users_username")
    conn.execute(text("DROP INDEX ix_users_username"))
    
    # Step 3: Create new partial unique index
    print("📝 Creating new partial unique index: ix_users_username_active")
    conn.execute(text("""
        CREATE UNIQUE INDEX ix_users_username_active 
        ON users (username) 
        WHERE deleted_at IS NULL
    """))
    
    # Step 4: Verify new index was created
    verify_result = conn.execute(text("""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = 'users' 
        AND indexname = 'ix_users_username_active'
    """))
    
    new_index = verify_result.fetchone()
    if new_index:
        print("✅ New partial index created successfully!")
        print(f"   Index definition: {new_index[1]}")
    else:
        print("❌ Failed to create new index!")
        raise Exception("New index creation failed")
    
    print("🎉 Migration completed successfully!")
    print("   - Username uniqueness now only applies to active users")
    print("   - Soft deleted usernames can be reused")


def downgrade():
    """Restore original username unique constraint (WARNING: May fail if duplicates exist)"""
    
    conn = op.get_bind()
    
    print("⚠️  DOWNGRADE WARNING:")
    print("   This will restore the original constraint that prevents")
    print("   reusing usernames from soft-deleted users.")
    print("   Migration may fail if duplicate usernames exist.")
    
    # Step 1: Drop partial index
    print("📝 Dropping partial unique index: ix_users_username_active")
    conn.execute(text("DROP INDEX IF EXISTS ix_users_username_active"))
    
    # Step 2: Check for potential conflicts
    conflict_check = conn.execute(text("""
        SELECT username, COUNT(*) 
        FROM users 
        GROUP BY username 
        HAVING COUNT(*) > 1
    """))
    
    conflicts = conflict_check.fetchall()
    if conflicts:
        print("❌ CONFLICT DETECTED:")
        print("   The following usernames have duplicates:")
        for conflict in conflicts:
            print(f"   - '{conflict[0]}': {conflict[1]} users")
        print("   Cannot restore original constraint.")
        print("   Manual cleanup required before downgrade.")
        raise Exception("Username conflicts prevent downgrade")
    
    # Step 3: Restore original index
    print("📝 Restoring original unique index: ix_users_username")
    try:
        conn.execute(text("CREATE UNIQUE INDEX ix_users_username ON users (username)"))
        print("✅ Original index restored successfully")
    except Exception as e:
        print(f"❌ Failed to restore original index: {e}")
        raise
    
    print("🔄 Downgrade completed")
