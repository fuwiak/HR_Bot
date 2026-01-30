"""
Вспомогательные функции для работы с сообщениями из канала HRAI_ANovoselova_Leads
"""
import os
import re
import logging
from typing import Optional, Dict

log = logging.getLogger(__name__)

TELEGRAM_LEADS_CHANNEL_ID = os.getenv("TELEGRAM_LEADS_CHANNEL_ID")
LEADS_CHANNEL_USERNAME = "@HRAI_ANovoselova_Leads"


async def get_channel_message_text(bot, message_identifier: str, user_chat_id: Optional[int] = None) -> Optional[str]:
    """
    Получает текст сообщения из канала по ID или ссылке
    
    Args:
        bot: Экземпляр Telegram бота
        message_identifier: ID сообщения, ссылка
        user_chat_id: ID чата пользователя для форварда сообщения (опционально)
    
    Returns:
        Текст сообщения или None если не удалось получить
    """
    if not bot:
        return None
    
    try:
        # Получаем ID канала
        if not TELEGRAM_LEADS_CHANNEL_ID:
            try:
                chat = await bot.get_chat(LEADS_CHANNEL_USERNAME)
                channel_id = int(chat.id)
            except Exception as e:
                log.error(f"❌ Не удалось получить ID канала: {e}")
                return None
        else:
            channel_id = int(TELEGRAM_LEADS_CHANNEL_ID)
        
        # Парсим ссылку на сообщение (например: https://t.me/HRAI_ANovoselova_Leads/123)
        link_pattern = r'(?:https?://)?(?:t\.me|telegram\.me)/(?:c/)?([^/]+)/(\d+)'
        link_match = re.search(link_pattern, message_identifier)
        if link_match:
            channel_username = link_match.group(1)
            message_id = int(link_match.group(2))
            
            # Проверяем, что это наш канал
            if channel_username.replace('_', '').lower() in LEADS_CHANNEL_USERNAME.replace('@', '').replace('_', '').lower():
                try:
                    # Пробуем форварднуть сообщение пользователю для получения текста
                    if user_chat_id:
                        try:
                            await bot.forward_message(
                                chat_id=user_chat_id,
                                from_chat_id=channel_id,
                                message_id=message_id
                            )
                            # После форварда пользователь может ответить на сообщение
                            # Но мы не можем получить текст напрямую
                            log.info(f"ℹ️ Сообщение {message_id} форварднуто пользователю для ответа")
                            return None  # Возвращаем None, пользователь должен ответить на сообщение
                        except Exception as e:
                            log.warning(f"⚠️ Не удалось форварднуть сообщение: {e}")
                    
                    # Альтернативный способ: пытаемся получить через copy_message (если доступно)
                    # Но это тоже не дает нам текст напрямую
                    log.warning(f"⚠️ Прямое получение текста сообщения по ссылке ограничено в Bot API")
                    return None
                except Exception as e:
                    log.error(f"❌ Ошибка получения сообщения по ссылке: {e}")
                    return None
        
        # Пробуем как числовой ID
        try:
            message_id = int(message_identifier)
            
            # Пробуем форварднуть сообщение пользователю
            if user_chat_id:
                try:
                    await bot.forward_message(
                        chat_id=user_chat_id,
                        from_chat_id=channel_id,
                        message_id=message_id
                    )
                    log.info(f"ℹ️ Сообщение {message_id} форварднуто пользователю")
                    return None  # Пользователь должен ответить на форварднутое сообщение
                except Exception as e:
                    log.warning(f"⚠️ Не удалось форварднуть сообщение {message_id}: {e}")
            
            log.warning(f"⚠️ Прямое получение сообщения по ID из канала ограничено в Bot API")
            return None
        except ValueError:
            # Не число, не ссылка - возвращаем None
            return None
    
    except Exception as e:
        log.error(f"❌ Ошибка в get_channel_message_text: {e}")
        return None


async def extract_message_from_reply(update) -> Optional[str]:
    """
    Извлекает текст сообщения из reply_to_message
    
    Args:
        update: Update объект от Telegram
    
    Returns:
        Текст сообщения или None
    """
    if not update.message or not update.message.reply_to_message:
        return None
    
    reply_msg = update.message.reply_to_message
    text = reply_msg.text or reply_msg.caption or ""
    
    # Если это форвард из канала, используем текст форварднутого сообщения
    if reply_msg.forward_from_chat:
        # Это форвард из канала - текст уже в reply_msg.text
        text = reply_msg.text or reply_msg.caption or ""
        log.info(f"📎 Извлечен текст из форварднутого сообщения из канала: {len(text)} символов")
    
    # Если текст есть, возвращаем его
    if text:
        return text
    
    # Если нет текста, но есть entities (например, форвард с медиа)
    if reply_msg.entities or reply_msg.caption_entities:
        # Пытаемся извлечь текст из entities
        if reply_msg.caption:
            return reply_msg.caption
    
    return None


def parse_message_reference(text: str) -> Optional[Dict]:
    """
    Парсит ссылку или ID сообщения из текста
    
    Args:
        text: Текст с возможной ссылкой или ID
    
    Returns:
        Словарь с типом и значением или None
    """
    if not text:
        return None
    
    # Проверяем ссылку
    link_pattern = r'(?:https?://)?(?:t\.me|telegram\.me)/(?:c/)?([^/]+)/(\d+)'
    link_match = re.search(link_pattern, text)
    if link_match:
        return {
            "type": "link",
            "channel": link_match.group(1),
            "message_id": int(link_match.group(2))
        }
    
    # Проверяем числовой ID
    try:
        message_id = int(text.strip())
        return {
            "type": "id",
            "message_id": message_id
        }
    except ValueError:
        pass
    
    return None
