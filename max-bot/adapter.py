"""
Max адаптер для HR Bot
"""
import os
import logging
from typing import Dict, Any, Optional

log = logging.getLogger(__name__)

try:
    from maxapi import Bot
    from maxapi.exceptions import MaxApiError
    MAXAPI_AVAILABLE = True
except ImportError:
    MAXAPI_AVAILABLE = False
    log.warning("maxapi не установлен")


def get_chat_id_from_session(user_id: str) -> Optional[str]:
    """
    Получить chat_id из сессии/базы данных
    
    Args:
        user_id: ID пользователя
        
    Returns:
        chat_id или None
    """
    try:
        # Пытаемся получить из Redis
        try:
            from services.helpers.redis_helper import get_redis_client
            redis_client = get_redis_client()
            if redis_client:
                chat_id = redis_client.get(f"max:chat_id:{user_id}")
                if chat_id:
                    return chat_id.decode() if isinstance(chat_id, bytes) else chat_id
        except Exception as e:
            log.debug(f"Не удалось получить chat_id из Redis: {e}")
        
        # Пытаемся получить из PostgreSQL
        try:
            from backend.database.models_sqlalchemy import ConversationContext, get_session
            session = get_session()
            try:
                context = session.query(ConversationContext).filter_by(
                    user_id=int(user_id) if user_id.isdigit() else None
                ).first()
                if context and context.chat_id:
                    return str(context.chat_id)
            finally:
                session.close()
        except Exception as e:
            log.debug(f"Не удалось получить chat_id из PostgreSQL: {e}")
        
        # Пытаемся получить из последнего сообщения
        try:
            from backend.database.models_sqlalchemy import TelegramMessage, get_session
            user_id_int = int(user_id) if user_id.isdigit() else None
            if user_id_int:
                session = get_session()
                try:
                    message = session.query(TelegramMessage).filter_by(
                        user_id=user_id_int
                    ).order_by(TelegramMessage.created_at.desc()).first()
                    if message and message.chat_id:
                        return str(message.chat_id)
                finally:
                    session.close()
        except Exception as e:
            log.debug(f"Не удалось получить chat_id из сообщений: {e}")
        
        return None
    except Exception as e:
        log.error(f"Ошибка получения chat_id: {e}")
        return None


class MaxAdapter:
    """Адаптер для Max"""
    
    def __init__(self, token: str = None):
        self.token = token or os.getenv("MAX_BOT_TOKEN") or os.getenv("MAX_TOKEN")
        self.bot: Optional[Bot] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Инициализация Max бота"""
        if not MAXAPI_AVAILABLE:
            log.error("maxapi не установлен")
            return False
        
        if not self.token:
            log.error("MAX_BOT_TOKEN или MAX_TOKEN не установлен")
            return False
        
        try:
            self.bot = Bot(token=self.token)
            self._initialized = True
            log.info("✅ Max адаптер инициализирован")
            return True
        except Exception as e:
            log.error(f"❌ Ошибка инициализации Max: {e}")
            return False
    
    async def send_message(self, user_id: str, text: str, **kwargs) -> bool:
        """Отправить сообщение в Max"""
        if not self._initialized or not self.bot:
            log.error("Max адаптер не инициализирован")
            return False
        
        try:
            # Пытаемся получить chat_id из сессии
            chat_id = kwargs.get("chat_id")
            if not chat_id:
                chat_id = get_chat_id_from_session(user_id)
            
            # Если chat_id не найден, используем user_id как fallback
            if not chat_id:
                log.warning(f"⚠️ chat_id не найден в сессии, используем user_id={user_id} как fallback")
                chat_id = user_id
            
            # Отправляем сообщение
            sent_message = await self.bot.send_message(
                chat_id=chat_id,
                text=text
            )
            
            log.info(f"📨 MaxAdapter.send_message: user_id={user_id}, message_length={len(text)}, message_preview='{text[:50]}...'")
            return True
        except MaxApiError as e:
            # Если ошибка 404 (chat not found), пытаемся использовать другой подход
            if e.code == 404 and ("chat.not.found" in str(e.raw) or "Chat" in str(e.raw)):
                log.warning(f"⚠️ Chat {chat_id} не найден, пытаемся использовать user_id напрямую")
                # Если chat_id был равен user_id, значит проблема в другом
                if chat_id == user_id:
                    log.error(f"❌ Ошибка от API: {e}")
                    return False
                try:
                    # Пытаемся отправить с user_id
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=text
                    )
                    # Сохраняем chat_id = user_id в сессию для будущих запросов
                    try:
                        from services.helpers.redis_helper import get_redis_client
                        redis_client = get_redis_client()
                        if redis_client:
                            redis_client.set(f"max:chat_id:{user_id}", user_id, ex=3600)
                    except Exception:
                        pass
                    log.info(f"✅ Сообщение отправлено с user_id={user_id}")
                    return True
                except Exception as e2:
                    log.error(f"❌ Ошибка отправки сообщения в Max: {e2}")
                    return False
            else:
                log.error(f"❌ Ошибка отправки сообщения в Max: {e}")
                return False
        except Exception as e:
            log.error(f"❌ Ошибка отправки сообщения в Max: {e}")
            return False
