"""
Telegram адаптер для HR Bot
"""
import os
import logging
from typing import Dict, Any, Optional

from .base_adapter import BaseAdapter

log = logging.getLogger(__name__)

try:
    from telegram import Update, Bot
    from telegram.constants import ChatAction, ParseMode
    from telegram.ext import Application, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    log.warning("python-telegram-bot не установлен")


class TelegramAdapter(BaseAdapter):
    """Адаптер для Telegram"""
    
    def __init__(self, token: str = None):
        super().__init__(platform="telegram")
        # Проверяем оба варианта имени переменной окружения
        self.token = token or os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
    
    async def initialize(self) -> bool:
        """Инициализация Telegram бота"""
        if not TELEGRAM_AVAILABLE:
            log.error("python-telegram-bot не установлен")
            return False
        
        if not self.token:
            log.error("TELEGRAM_TOKEN или TELEGRAM_BOT_TOKEN не установлен")
            return False
        
        try:
            self.bot = Bot(token=self.token)
            self._initialized = True
            log.info("✅ Telegram адаптер инициализирован")
            return True
        except Exception as e:
            log.error(f"❌ Ошибка инициализации Telegram: {e}")
            return False
    
    async def send_message(self, user_id: str, text: str, **kwargs) -> bool:
        """Отправить сообщение в Telegram"""
        if not self._initialized or not self.bot:
            log.error("Telegram адаптер не инициализирован")
            return False
        
        try:
            parse_mode = kwargs.get("parse_mode", ParseMode.MARKDOWN)
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            log.error(f"❌ Ошибка отправки сообщения: {e}")
            return False
    
    async def send_typing_action(self, user_id: str) -> bool:
        """Показать индикатор набора текста"""
        if not self._initialized or not self.bot:
            return False
        
        try:
            await self.bot.send_chat_action(
                chat_id=user_id,
                action=ChatAction.TYPING
            )
            return True
        except Exception as e:
            log.error(f"❌ Ошибка отправки typing action: {e}")
            return False
    
    async def handle_message(self, message: Dict[str, Any]) -> Optional[str]:
        """Обработать входящее сообщение"""
        try:
            user_id = message.get("user_id")
            text = message.get("text", "")
            
            if not user_id or not text:
                return None
            
            # Показываем typing indicator
            await self.send_typing_action(user_id)
            
            # Импортируем LangGraph workflow
            from backend.api.services import query_with_conversation_workflow
            
            result = await query_with_conversation_workflow(
                message=text,
                user_id=str(user_id),
                platform=self.platform
            )
            
            return result.get("response")
        except Exception as e:
            log.error(f"❌ Ошибка обработки сообщения: {e}")
            return None


# Глобальный экземпляр
_telegram_adapter: Optional[TelegramAdapter] = None


def get_telegram_adapter() -> TelegramAdapter:
    """Получить глобальный экземпляр Telegram адаптера"""
    global _telegram_adapter
    if _telegram_adapter is None:
        _telegram_adapter = TelegramAdapter()
    return _telegram_adapter
