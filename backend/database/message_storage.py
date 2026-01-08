"""
Сервис для сохранения сообщений Telegram: Redis -> PostgreSQL -> Qdrant
"""
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.database.models_sqlalchemy import TelegramUser, TelegramMessage, get_session, get_engine
from services.helpers.redis_helper import get_redis_client, add_memory_redis
try:
    from services.rag.qdrant_helper import index_message_to_qdrant
except ImportError:
    log.warning("⚠️ qdrant_helper не доступен, индексация в Qdrant отключена")
    def index_message_to_qdrant(*args, **kwargs):
        return False

log = logging.getLogger(__name__)


def save_telegram_message(
    user_id: int,
    chat_id: int,
    message_id: Optional[int],
    role: str,  # "user" или "assistant"
    content: str,
    message_type: str = "text",
    metadata: Optional[Dict[str, Any]] = None,
    save_to_redis: bool = True,
    save_to_postgres: bool = True,
    save_to_qdrant: bool = True
) -> Optional[int]:
    """
    Сохранить сообщение Telegram: Redis -> PostgreSQL -> Qdrant
    
    Args:
        user_id: ID пользователя Telegram
        chat_id: ID чата
        message_id: ID сообщения в Telegram (опционально)
        role: Роль сообщения ("user" или "assistant")
        content: Текст сообщения
        message_type: Тип сообщения (text, photo, document, etc.)
        metadata: Дополнительные метаданные
        save_to_redis: Сохранить в Redis (быстрый доступ)
        save_to_postgres: Сохранить в PostgreSQL (постоянное хранилище)
        save_to_qdrant: Индексировать в Qdrant (для RAG)
    
    Returns:
        ID сохраненного сообщения в PostgreSQL или None при ошибке
    """
    message_db_id = None
    
    # 1. Сохраняем в Redis (быстрый доступ для LLM)
    if save_to_redis:
        try:
            add_memory_redis(user_id, role, content)
            log.debug(f"✅ Сообщение сохранено в Redis (user_id={user_id}, role={role})")
        except Exception as e:
            log.warning(f"⚠️ Ошибка сохранения в Redis: {e}")
    
    # 2. Сохраняем в PostgreSQL (постоянное хранилище)
    if save_to_postgres:
        try:
            session = get_session()
            try:
                # Создаем или обновляем пользователя
                user = session.query(TelegramUser).filter_by(user_id=user_id).first()
                if not user:
                    user = TelegramUser(
                        user_id=user_id,
                        username=metadata.get("username") if metadata else None,
                        first_name=metadata.get("first_name") if metadata else None,
                        last_name=metadata.get("last_name") if metadata else None,
                        language_code=metadata.get("language_code") if metadata else None,
                        is_bot=metadata.get("is_bot", False) if metadata else False
                    )
                    session.add(user)
                    log.info(f"✅ Создан новый пользователь: user_id={user_id}")
                else:
                    # Обновляем данные пользователя если нужно
                    if metadata:
                        if "username" in metadata:
                            user.username = metadata.get("username")
                        if "first_name" in metadata:
                            user.first_name = metadata.get("first_name")
                        if "last_name" in metadata:
                            user.last_name = metadata.get("last_name")
                        user.updated_at = datetime.utcnow()
                
                # Создаем сообщение
                message = TelegramMessage(
                    user_id=user_id,
                    message_id=message_id,
                    chat_id=chat_id,
                    role=role,
                    content=content,
                    message_type=message_type,
                    platform="telegram",
                    metadata_json=metadata,
                    processed_by_llm=False,
                    indexed_in_qdrant=False
                )
                session.add(message)
                session.commit()
                message_db_id = message.id
                log.debug(f"✅ Сообщение сохранено в PostgreSQL (id={message_db_id}, user_id={user_id})")
            except SQLAlchemyError as e:
                session.rollback()
                log.error(f"❌ Ошибка SQLAlchemy при сохранении сообщения: {e}")
            finally:
                session.close()
        except Exception as e:
            log.error(f"❌ Ошибка сохранения в PostgreSQL: {e}")
    
    # 3. Индексируем в Qdrant (для RAG) - асинхронно в фоне
    if save_to_qdrant and message_db_id and content:
        try:
            # Индексируем только текстовые сообщения пользователя (не ответы бота)
            if role == "user" and message_type == "text":
                # Помечаем как индексированное после успешной индексации
                # Это делается асинхронно, чтобы не блокировать ответ бота
                index_message_to_qdrant_async(message_db_id, user_id, content)
                log.debug(f"✅ Сообщение отправлено на индексацию в Qdrant (id={message_db_id})")
        except Exception as e:
            log.warning(f"⚠️ Ошибка индексации в Qdrant: {e}")
    
    return message_db_id


def index_message_to_qdrant_async(message_id: int, user_id: int, content: str):
    """Асинхронно индексировать сообщение в Qdrant"""
    import threading
    
    def index_task():
        try:
            # Индексируем сообщение
            success = index_message_to_qdrant(
                text=content,
                metadata={
                    "message_id": message_id,
                    "user_id": user_id,
                    "source": "telegram_message",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            if success:
                # Помечаем сообщение как индексированное
                session = get_session()
                try:
                    message = session.query(TelegramMessage).filter_by(id=message_id).first()
                    if message:
                        message.indexed_in_qdrant = True
                        message.updated_at = datetime.utcnow()
                        session.commit()
                        log.info(f"✅ Сообщение {message_id} индексировано в Qdrant")
                except Exception as e:
                    log.error(f"❌ Ошибка обновления флага индексации: {e}")
                finally:
                    session.close()
        except Exception as e:
            log.error(f"❌ Ошибка индексации сообщения {message_id} в Qdrant: {e}")
    
    # Запускаем в отдельном потоке
    thread = threading.Thread(target=index_task, daemon=True)
    thread.start()


def get_user_messages(
    user_id: int,
    limit: int = 10,
    role: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Получить сообщения пользователя из PostgreSQL
    
    Args:
        user_id: ID пользователя
        limit: Количество сообщений
        role: Фильтр по роли (опционально)
    
    Returns:
        Список сообщений
    """
    try:
        session = get_session()
        try:
            query = session.query(TelegramMessage).filter_by(user_id=user_id)
            if role:
                query = query.filter_by(role=role)
            messages = query.order_by(TelegramMessage.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    "indexed_in_qdrant": msg.indexed_in_qdrant
                }
                for msg in reversed(messages)  # Возвращаем в хронологическом порядке
            ]
        finally:
            session.close()
    except Exception as e:
        log.error(f"❌ Ошибка получения сообщений: {e}")
        return []


def mark_message_processed_by_llm(message_id: int):
    """Пометить сообщение как обработанное LLM"""
    try:
        session = get_session()
        try:
            message = session.query(TelegramMessage).filter_by(id=message_id).first()
            if message:
                message.processed_by_llm = True
                message.updated_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()
    except Exception as e:
        log.error(f"❌ Ошибка пометки сообщения как обработанного: {e}")
