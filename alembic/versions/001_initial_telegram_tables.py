"""Initial migration: telegram users and messages

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицу telegram_users
    op.create_table(
        'telegram_users',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('language_code', sa.String(length=10), nullable=True),
        sa.Column('is_bot', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index('ix_telegram_users_user_id', 'telegram_users', ['user_id'], unique=False)
    op.create_index('ix_telegram_users_username', 'telegram_users', ['username'], unique=False)
    
    # Создаем таблицу telegram_messages
    op.create_table(
        'telegram_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(length=50), nullable=True, server_default='text'),
        sa.Column('platform', sa.String(length=50), nullable=True, server_default='telegram'),
        sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('processed_by_llm', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('indexed_in_qdrant', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['telegram_users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_telegram_messages_user_id', 'telegram_messages', ['user_id'], unique=False)
    op.create_index('ix_telegram_messages_message_id', 'telegram_messages', ['message_id'], unique=False)
    op.create_index('ix_telegram_messages_chat_id', 'telegram_messages', ['chat_id'], unique=False)
    op.create_index('ix_telegram_messages_role', 'telegram_messages', ['role'], unique=False)
    op.create_index('ix_telegram_messages_processed_by_llm', 'telegram_messages', ['processed_by_llm'], unique=False)
    op.create_index('ix_telegram_messages_indexed_in_qdrant', 'telegram_messages', ['indexed_in_qdrant'], unique=False)
    op.create_index('ix_telegram_messages_created_at', 'telegram_messages', ['created_at'], unique=False)
    op.create_index('idx_user_created', 'telegram_messages', ['user_id', 'created_at'], unique=False)
    op.create_index('idx_role_created', 'telegram_messages', ['role', 'created_at'], unique=False)
    op.create_index('idx_qdrant_indexed', 'telegram_messages', ['indexed_in_qdrant', 'created_at'], unique=False)
    
    # Создаем таблицу conversation_contexts
    op.create_table(
        'conversation_contexts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('context_json', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('context_size', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_message_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['telegram_users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversation_contexts_user_id', 'conversation_contexts', ['user_id'], unique=False)
    op.create_index('ix_conversation_contexts_chat_id', 'conversation_contexts', ['chat_id'], unique=False)


def downgrade() -> None:
    # Удаляем таблицы в обратном порядке
    op.drop_index('ix_conversation_contexts_chat_id', table_name='conversation_contexts')
    op.drop_index('ix_conversation_contexts_user_id', table_name='conversation_contexts')
    op.drop_table('conversation_contexts')
    
    op.drop_index('idx_qdrant_indexed', table_name='telegram_messages')
    op.drop_index('idx_role_created', table_name='telegram_messages')
    op.drop_index('idx_user_created', table_name='telegram_messages')
    op.drop_index('ix_telegram_messages_created_at', table_name='telegram_messages')
    op.drop_index('ix_telegram_messages_indexed_in_qdrant', table_name='telegram_messages')
    op.drop_index('ix_telegram_messages_processed_by_llm', table_name='telegram_messages')
    op.drop_index('ix_telegram_messages_role', table_name='telegram_messages')
    op.drop_index('ix_telegram_messages_chat_id', table_name='telegram_messages')
    op.drop_index('ix_telegram_messages_message_id', table_name='telegram_messages')
    op.drop_index('ix_telegram_messages_user_id', table_name='telegram_messages')
    op.drop_table('telegram_messages')
    
    op.drop_index('ix_telegram_users_username', table_name='telegram_users')
    op.drop_index('ix_telegram_users_user_id', table_name='telegram_users')
    op.drop_table('telegram_users')
