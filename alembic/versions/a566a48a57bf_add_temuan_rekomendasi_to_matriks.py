"""add temuan_rekomendasi to matriks

Revision ID: a566a48a57bf
Revises: 8822222c91e6
Create Date: 2025-07-18 14:46:12.311153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a566a48a57bf'
down_revision: Union[str, Sequence[str], None] = '8822222c91e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add temuan_rekomendasi column to matriks table."""
    
    # Add the new column
    op.add_column(
        'matriks',
        sa.Column(
            'temuan_rekomendasi',
            sa.Text(),
            nullable=True,
            comment='JSON data untuk pasangan temuan dan rekomendasi'
        )
    )
    
    # Optional: Add index for better performance on JSON queries
    # Uncomment if you want index for null checks
    # op.create_index(
    #     'idx_matriks_has_temuan_rekomendasi',
    #     'matriks',
    #     [sa.text('(temuan_rekomendasi IS NOT NULL)')],
    #     postgresql_where=sa.text('deleted_at IS NULL')
    # )


def downgrade() -> None:
    """Remove temuan_rekomendasi column from matriks table."""
    
    # Drop index if created
    # op.drop_index('idx_matriks_has_temuan_rekomendasi', table_name='matriks')
    
    # Drop the column
    op.drop_column('matriks', 'temuan_rekomendasi')
