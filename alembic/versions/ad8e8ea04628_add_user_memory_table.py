"""add_user_memory_table

Revision ID: ad8e8ea04628
Revises: 34f6b00e57a2
Create Date: 2026-01-11 16:19:01.525516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad8e8ea04628'
down_revision: Union[str, None] = '34f6b00e57a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицу для истории чатов пользователей
    op.create_table(
        'user_memory',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    # Создаем индексы для оптимизации запросов
    op.create_index('idx_user_memory_user_id', 'user_memory', ['user_id'], unique=False)
    op.create_index('idx_user_memory_created_at', 'user_memory', ['created_at'], unique=False)


def downgrade() -> None:
    # Удаляем индексы
    op.drop_index('idx_user_memory_created_at', table_name='user_memory')
    op.drop_index('idx_user_memory_user_id', table_name='user_memory')
    # Удаляем таблицу
    op.drop_table('user_memory')
