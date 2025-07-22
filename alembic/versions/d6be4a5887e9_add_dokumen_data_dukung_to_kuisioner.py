"""add dokumen data dukung to kuisioner

Revision ID: d6be4a5887e9
Revises: 524bfc8a8f1d
Create Date: 2025-07-22 16:53:11.776323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6be4a5887e9'
down_revision: Union[str, Sequence[str], None] = '524bfc8a8f1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new column to kuisioner table
    op.add_column('kuisioner', 
        sa.Column('link_dokumen_data_dukung', 
                 sa.String(length=1000), 
                 nullable=True,
                 comment='Link Google Drive untuk dokumen data dukung')
    )

def downgrade() -> None:
    # Remove the column if we need to rollback
    op.drop_column('kuisioner', 'link_dokumen_data_dukung')
