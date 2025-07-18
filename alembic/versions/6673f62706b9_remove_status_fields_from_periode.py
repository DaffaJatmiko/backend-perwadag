"""remove status fields from periode

Revision ID: 6673f62706b9
Revises: a566a48a57bf
Create Date: 2025-07-18 17:07:16.557630

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '6673f62706b9'
down_revision: Union[str, Sequence[str], None] = 'a566a48a57bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove status field from periode_evaluasi table."""
    # Remove status column
    op.drop_column('periode_evaluasi', 'status')

    # Add comment for clarity
    op.execute("""
        COMMENT ON TABLE periode_evaluasi IS 
        'Periode evaluasi penilaian risiko - simplified without status field. 
        Editable control using is_locked field only.'
    """)

def downgrade() -> None:
    """Add back status field to periode_evaluasi table."""
    # Recreate status enum type
    status_enum = postgresql.ENUM('AKTIF', 'TUTUP', name='statusperiode')
    status_enum.create(op.get_bind())

    # Add status column back
    op.add_column('periode_evaluasi', 
        sa.Column('status', 
                status_enum,
                nullable=False, 
                server_default='AKTIF'
        )
    )

    # Remove comment
    op.execute("COMMENT ON TABLE periode_evaluasi IS NULL")