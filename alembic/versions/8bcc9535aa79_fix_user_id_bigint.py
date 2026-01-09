"""fix_user_id_bigint

Revision ID: 8bcc9535aa79
Revises: 001_initial
Create Date: 2026-01-09 04:38:56.164249

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bcc9535aa79'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Изменяем тип user_id с Integer на BigInteger во всех таблицах
    # Это необходимо, так как Telegram user_id может быть больше чем максимальное значение Integer
    
    # 1. Изменяем telegram_users.user_id (PRIMARY KEY)
    op.alter_column('telegram_users', 'user_id',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)
    
    # 2. Изменяем telegram_messages.user_id (FOREIGN KEY)
    op.alter_column('telegram_messages', 'user_id',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)
    
    # 3. Изменяем conversation_contexts.user_id (FOREIGN KEY)
    op.alter_column('conversation_contexts', 'user_id',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)


def downgrade() -> None:
    # Откат изменений (меняем обратно на Integer)
    # ВНИМАНИЕ: Это может привести к ошибкам если есть user_id > 2147483647
    
    op.alter_column('conversation_contexts', 'user_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=False)
    
    op.alter_column('telegram_messages', 'user_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=False)
    
    op.alter_column('telegram_users', 'user_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=False)
