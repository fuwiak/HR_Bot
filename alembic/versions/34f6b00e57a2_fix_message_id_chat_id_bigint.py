"""fix_message_id_chat_id_bigint

Revision ID: 34f6b00e57a2
Revises: 1f792dd67dc4
Create Date: 2026-01-09 23:24:25.476338

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34f6b00e57a2'
down_revision: Union[str, None] = '1f792dd67dc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Изменяем тип message_id и chat_id с Integer на BigInteger
    # Это необходимо, так как Telegram message_id и chat_id могут быть очень большими числами
    
    # 1. Изменяем telegram_messages.message_id
    op.alter_column('telegram_messages', 'message_id',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=True)
    
    # 2. Изменяем telegram_messages.chat_id
    op.alter_column('telegram_messages', 'chat_id',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)
    
    # 3. Изменяем conversation_contexts.chat_id
    op.alter_column('conversation_contexts', 'chat_id',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)
    
    # 4. Изменяем conversation_contexts.last_message_id
    op.alter_column('conversation_contexts', 'last_message_id',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=True)


def downgrade() -> None:
    # Откат изменений (меняем обратно на Integer)
    # ВНИМАНИЕ: Это может привести к ошибкам если есть message_id или chat_id > 2147483647
    
    op.alter_column('conversation_contexts', 'last_message_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=True)
    
    op.alter_column('conversation_contexts', 'chat_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=False)
    
    op.alter_column('telegram_messages', 'chat_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=False)
    
    op.alter_column('telegram_messages', 'message_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=True)
