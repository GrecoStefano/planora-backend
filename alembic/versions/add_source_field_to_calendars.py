"""Add source field to calendars

Revision ID: add_source_calendars
Revises: 767ca726d6a2
Create Date: 2025-12-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_source_calendars'
down_revision = '767ca726d6a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create CalendarSource enum
    calendarsource_enum = sa.Enum('LOCAL', 'MICROSOFT365', 'GOOGLE', 'EXTERNAL', name='calendarsource')
    calendarsource_enum.create(op.get_bind(), checkfirst=True)
    
    # Add source column with default value 'LOCAL'
    op.add_column('calendars', sa.Column('source', calendarsource_enum, nullable=False, server_default='LOCAL'))


def downgrade() -> None:
    # Remove source column
    op.drop_column('calendars', 'source')
    
    # Drop enum
    calendarsource_enum = sa.Enum(name='calendarsource')
    calendarsource_enum.drop(op.get_bind(), checkfirst=True)
