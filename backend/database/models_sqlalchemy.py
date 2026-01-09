"""
SQLAlchemy модели для базы данных
"""
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Text, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
import logging

log = logging.getLogger(__name__)

Base = declarative_base()


class TelegramUser(Base):
    """Модель пользователя Telegram"""
    __tablename__ = "telegram_users"
    
    user_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(255), nullable=True, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    language_code = Column(String(10), nullable=True)
    is_bot = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Связь с сообщениями
    messages = relationship("TelegramMessage", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TelegramUser(user_id={self.user_id}, username={self.username})>"


class TelegramMessage(Base):
    """Модель сообщения Telegram (входящие и исходящие)"""
    __tablename__ = "telegram_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("telegram_users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(Integer, nullable=True, index=True)  # ID сообщения в Telegram
    chat_id = Column(Integer, nullable=False, index=True)
    
    # Тип сообщения
    role = Column(String(50), nullable=False, index=True)  # "user" или "assistant"
    content = Column(Text, nullable=False)  # Текст сообщения
    
    # Метаданные
    message_type = Column(String(50), default="text")  # text, photo, document, etc.
    platform = Column(String(50), default="telegram")
    
    # Дополнительные данные (JSON)
    metadata_json = Column(JSON, nullable=True)  # Дополнительные данные (callback_data, entities, etc.)
    
    # Флаги обработки
    processed_by_llm = Column(Boolean, default=False, index=True)  # Обработано ли LLM
    indexed_in_qdrant = Column(Boolean, default=False, index=True)  # Индексировано ли в Qdrant
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Связь с пользователем
    user = relationship("TelegramUser", back_populates="messages")
    
    # Индексы для быстрого поиска
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_role_created', 'role', 'created_at'),
        Index('idx_qdrant_indexed', 'indexed_in_qdrant', 'created_at'),
    )
    
    def __repr__(self):
        return f"<TelegramMessage(id={self.id}, user_id={self.user_id}, role={self.role})>"


class ConversationContext(Base):
    """Модель контекста разговора (для Redis и быстрого доступа)"""
    __tablename__ = "conversation_contexts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("telegram_users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    chat_id = Column(Integer, nullable=False, index=True)
    
    # Контекст разговора (последние N сообщений)
    context_json = Column(JSON, nullable=False)  # Массив сообщений для LLM
    
    # Метаданные контекста
    context_size = Column(Integer, default=0)  # Количество сообщений в контексте
    last_message_id = Column(Integer, nullable=True)  # ID последнего сообщения
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<ConversationContext(user_id={self.user_id}, context_size={self.context_size})>"


# Функция для получения engine
def get_engine():
    """Получить SQLAlchemy engine"""
    from config import load_config
    
    db_config = load_config("database")
    db_settings = db_config.get("database", {}).get("postgresql", {})
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pg_host = db_settings.get("host") or os.getenv("PGHOST")
        pg_port = db_settings.get("port") or os.getenv("PGPORT", "5432")
        pg_database = db_settings.get("database") or os.getenv("PGDATABASE", "railway")
        pg_user = db_settings.get("user") or os.getenv("PGUSER", "postgres")
        pg_password = db_settings.get("password") or os.getenv("PGPASSWORD")
        
        if pg_host and pg_password:
            database_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
        else:
            database_url = "postgresql://postgres:postgres@localhost:5432/railway"
    
    return create_engine(database_url, pool_pre_ping=True)


# Функция для получения сессии
def get_session():
    """Получить SQLAlchemy session"""
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()
