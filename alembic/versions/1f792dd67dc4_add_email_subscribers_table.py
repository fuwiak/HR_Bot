"""add_email_subscribers_table

Revision ID: 1f792dd67dc4
Revises: 8bcc9535aa79
Create Date: 2026-01-09 01:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f792dd67dc4'
down_revision: Union[str, None] = '8bcc9535aa79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицу для подписчиков на email уведомления
    op.create_table(
        'email_subscribers',
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('subscribed_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index('ix_email_subscribers_user_id', 'email_subscribers', ['user_id'], unique=False)


def downgrade() -> None:
    # Удаляем таблицу email_subscribers
    op.drop_index('ix_email_subscribers_user_id', table_name='email_subscribers')
    op.drop_table('email_subscribers')
