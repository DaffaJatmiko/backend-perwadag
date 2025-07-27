"""add is_active field to format_kuisioner

Revision ID: 1398d91af62b
Revises: 347ad01f6a84
Create Date: 2025-07-27 17:55:36.529794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1398d91af62b'
down_revision: Union[str, Sequence[str], None] = '347ad01f6a84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active column to format_kuisioner table."""
    # Add is_active column with default False
    op.add_column(
        'format_kuisioner',
        sa.Column('is_active', sa.Boolean(), nullable=False, default=False, server_default='false')
    )
    
    # Create index for better query performance
    op.create_index(
        'ix_format_kuisioner_is_active',
        'format_kuisioner',
        ['is_active']
    )
    
    # Optional: Set one template as active if none exists
    # Uncomment if you want to auto-activate the most recent template
    """
    # Get connection to execute raw SQL if needed
    connection = op.get_bind()
    
    # Check if there are any templates
    result = connection.execute(
        sa.text("SELECT COUNT(*) FROM format_kuisioner WHERE deleted_at IS NULL")
    ).scalar()
    
    if result > 0:
        # Activate the most recent template
        connection.execute(
            sa.text('''
                UPDATE format_kuisioner 
                SET is_active = true 
                WHERE id = (
                    SELECT id FROM format_kuisioner 
                    WHERE deleted_at IS NULL 
                    ORDER BY created_at DESC 
                    LIMIT 1
                )
            ''')
        )
    """


def downgrade() -> None:
    """Remove is_active column from format_kuisioner table."""
    # Drop index first
    op.drop_index('ix_format_kuisioner_is_active', table_name='format_kuisioner')
    
    # Drop column
    op.drop_column('format_kuisioner', 'is_active')