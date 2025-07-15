"""fix_inspektorat_format_to_numbers

Revision ID: 8cb7dc59dc77
Revises: 7711be8c3721
Create Date: 2025-07-15 08:32:22.944473

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8cb7dc59dc77'
down_revision: Union[str, Sequence[str], None] = '7711be8c3721'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update inspektorat format dari romawi ke angka."""
    connection = op.get_bind()
    
    # Update format inspektorat
    connection.execute(
        sa.text("UPDATE users SET inspektorat = 'Inspektorat 1' WHERE inspektorat = 'Inspektorat I'")
    )
    connection.execute(
        sa.text("UPDATE users SET inspektorat = 'Inspektorat 2' WHERE inspektorat = 'Inspektorat II'")
    )
    connection.execute(
        sa.text("UPDATE users SET inspektorat = 'Inspektorat 3' WHERE inspektorat = 'Inspektorat III'")
    )
    connection.execute(
        sa.text("UPDATE users SET inspektorat = 'Inspektorat 4' WHERE inspektorat = 'Inspektorat IV'")
    )

def downgrade() -> None:
    """Rollback ke format romawi."""
    connection = op.get_bind()
    
    connection.execute(
        sa.text("UPDATE users SET inspektorat = 'Inspektorat I' WHERE inspektorat = '1'")
    )
    connection.execute(
        sa.text("UPDATE users SET inspektorat = 'Inspektorat II' WHERE inspektorat = '2'")
    )
    connection.execute(
        sa.text("UPDATE users SET inspektorat = 'Inspektorat III' WHERE inspektorat = '3'")
    )
    connection.execute(
        sa.text("UPDATE users SET inspektorat = 'Inspektorat IV' WHERE inspektorat = '4'")
    )
