"""
Telegram Channel Adapter
Адаптер для получения сообщений из Telegram канала @HRTime_bot
"""
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

log = logging.getLogger()

# Импорты для Telegram
try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    log.warning("⚠️ Telegram модуль недоступен")


# ===================== CONFIGURATION =====================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HRTIME_CHANNEL_USERNAME = os.getenv("HRTIME_CHANNEL_USERNAME", "@HRTime_bot")
HRTIME_CHANNEL_ID = os.getenv("HRTIME_CHANNEL_ID")  # Опционально, можно использовать username


# ===================== ADAPTER CLASS =====================

class TelegramChannelAdapter:
    """Адаптер для получения сообщений из Telegram канала"""
    
    def __init__(self):
        self.bot = None
        self.channel_username = HRTIME_CHANNEL_USERNAME
        self.channel_id = HRTIME_CHANNEL_ID
        
        if TELEGRAM_AVAILABLE and TELEGRAM_BOT_TOKEN:
            try:
                self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
            except Exception as e:
                log.error(f"❌ Ошибка инициализации Telegram Bot: {e}")
                self.bot = None
        else:
            log.warning("⚠️ Telegram Bot Token не установлен")
    
    async def get_channel_messages(
        self,
        limit: int = 10,
        since_message_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Получить последние сообщения из канала @HRTime_bot
        
        Args:
            limit: Максимальное количество сообщений
            since_message_id: ID сообщения, после которого получать (для получения только новых)
        
        Returns:
            Список сообщений с информацией
        """
        if not self.bot:
            log.warning("⚠️ Telegram Bot недоступен, используем placeholder")
            return []
        
        try:
            # Получаем информацию о канале
            if self.channel_id:
                chat_id = int(self.channel_id) if self.channel_id.lstrip('-').isdigit() else self.channel_id
            else:
                # Пытаемся получить ID канала по username
                try:
                    chat = await self.bot.get_chat(self.channel_username)
                    chat_id = chat.id
                except TelegramError as e:
                    log.error(f"❌ Не удалось получить информацию о канале {self.channel_username}: {e}")
                    return []
            
            log.info(f"📢 [Telegram Channel] Получение сообщений из канала {self.channel_username} (ID: {chat_id})")
            
            # Получаем последние сообщения
            # Примечание: Telegram Bot API не позволяет напрямую получать историю канала
            # Нужно использовать webhook или хранить последний обработанный message_id
            # Здесь используем упрощенный подход - получаем через getUpdates (если бот добавлен в канал)
            
            messages = []
            
            # Альтернативный подход: если бот добавлен в канал как администратор,
            # можно получать обновления через getUpdates
            # Но для этого нужен отдельный механизм отслеживания
            
            # Пока возвращаем пустой список (placeholder)
            # В будущем здесь будет реализация через webhook или polling канала
            
            log.info(f"✅ [Telegram Channel] Получено {len(messages)} сообщений из канала")
            return messages
            
        except Exception as e:
            log.error(f"❌ [Telegram Channel] Ошибка получения сообщений: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            return []
    
    async def get_channel_updates(
        self,
        offset: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Получить обновления из канала через getUpdates
        
        Args:
            offset: Offset для получения обновлений
            limit: Максимальное количество обновлений
        
        Returns:
            Список обновлений из канала
        """
        if not self.bot:
            return []
        
        try:
            updates = await self.bot.get_updates(offset=offset, limit=limit, timeout=10)
            
            channel_messages = []
            for update in updates:
                # Проверяем, что это сообщение из нужного канала
                if update.channel_post:
                    post = update.channel_post
                    # Проверяем, что это наш канал
                    if post.chat.username == self.channel_username.lstrip('@') or \
                       str(post.chat.id) == str(self.channel_id):
                        channel_messages.append({
                            "message_id": post.message_id,
                            "text": post.text or post.caption or "",
                            "date": post.date,
                            "chat_id": post.chat.id,
                            "chat_username": post.chat.username,
                            "raw": post.to_dict()
                        })
            
            log.info(f"✅ [Telegram Channel] Получено {len(channel_messages)} сообщений из канала через getUpdates")
            return channel_messages
            
        except Exception as e:
            log.error(f"❌ [Telegram Channel] Ошибка получения обновлений: {e}")
            return []
    
    def is_channel_message(self, message: Dict) -> bool:
        """
        Проверить, является ли сообщение сообщением из канала @HRTime_bot
        
        Args:
            message: Словарь с данными сообщения
        
        Returns:
            True если это сообщение из канала
        """
        if not message:
            return False
        
        chat_username = message.get("chat_username", "")
        chat_id = str(message.get("chat_id", ""))
        
        # Проверяем по username
        if chat_username and self.channel_username.lstrip('@') in chat_username:
            return True
        
        # Проверяем по ID
        if self.channel_id and chat_id == str(self.channel_id):
            return True
        
        return False
