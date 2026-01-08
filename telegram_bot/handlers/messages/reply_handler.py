"""
Обработчик сообщений (основная функция reply)
"""
import sys
import re
import logging
from pathlib import Path
from typing import Dict
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction, ParseMode

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

log = logging.getLogger(__name__)

# Импорты из созданных модулей
from telegram_bot.storage.memory import add_memory, get_history, get_recent_history
from telegram_bot.integrations.openrouter import openrouter_chat
from telegram_bot.services.booking_service import create_real_booking, create_booking_from_parsed_data
from telegram_bot.nlp.intent_classifier import is_booking
from telegram_bot.nlp.booking_parser import parse_booking_message
from telegram_bot.integrations.google_sheets import (
    get_services, get_masters, get_api_data_for_ai, get_master_services_text,
    get_services_with_prices
)
from telegram_bot.integrations.qdrant import search_service
from telegram_bot.storage.email_subscribers import load_email_subscribers, add_email_subscriber
from telegram_bot.config import (
    CONSULTING_PROMPT,
    BOOKING_PROMPT,
    CHAT_PROMPT
)

# Импортируем сохранение сообщений
try:
    from backend.database.message_storage import save_telegram_message
except ImportError:
    log.warning("⚠️ message_storage не доступен, сообщения не будут сохраняться в БД")
    def save_telegram_message(*args, **kwargs):
        return None


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основной обработчик сообщений"""
    if not update.message or not update.message.text:
        return
    
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    message_id = update.message.message_id
    text = update.message.text.strip()
    username = update.message.from_user.username or "без username"
    first_name = update.message.from_user.first_name or "без имени"
    
    # Сохраняем входящее сообщение: Redis -> PostgreSQL -> Qdrant
    try:
        save_telegram_message(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            role="user",
            content=text,
            metadata={
                "username": username,
                "first_name": first_name,
                "last_name": update.message.from_user.last_name
            }
        )
    except Exception as e:
        log.warning(f"⚠️ Ошибка сохранения сообщения: {e}")
    
    # Показываем что печатаем
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    
    try:
        # Проверяем, является ли это запросом на запись
        if is_booking(text):
            log.info(f"🔍 Обнаружен запрос на запись: {text}")
            
            # Парсим данные из сообщения
            parsed_data = parse_booking_message(text)
            
            if parsed_data:
                # Создаем запись
                result = await create_real_booking(user_id, parsed_data, context)
                if result:
                    # Сохраняем ответ бота
                    try:
                        save_telegram_message(
                            user_id=user_id,
                            chat_id=chat_id,
                            message_id=None,
                            role="assistant",
                            content=result
                        )
                    except Exception:
                        pass
                    return
        
        # Получаем историю для контекста
        history = get_recent_history(user_id)
        
        # Используем RAG поиск если нужно
        rag_context = ""
        if len(text) > 10:  # Только для достаточно длинных запросов
            try:
                results = search_service(text, limit=3)
                if results:
                    rag_context = "\n\nРелевантная информация из базы знаний:\n"
                    for i, result in enumerate(results[:3], 1):
                        rag_context += f"{i}. {result.get('title', 'Без названия')}: {result.get('content', '')[:200]}...\n"
            except Exception as e:
                log.warning(f"⚠️ Ошибка RAG поиска: {e}")
        
        # Формируем промпт
        system_prompt = CHAT_PROMPT
        if rag_context:
            system_prompt += rag_context
        
        # Формируем сообщения для LLM
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Добавляем историю
        if history:
            messages.append({"role": "user", "content": history})
        
        # Добавляем текущее сообщение
        messages.append({"role": "user", "content": text})
        
        # Получаем ответ от LLM
        response = await openrouter_chat(messages, use_system_message=False)
        
        # Сохраняем ответ в память
        add_memory(user_id, "assistant", response)
        
        # Сохраняем ответ бота в БД
        try:
            save_telegram_message(
                user_id=user_id,
                chat_id=chat_id,
                message_id=None,
                role="assistant",
                content=response
            )
        except Exception:
            pass
        
        # Отправляем ответ
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        log.error(f"❌ Ошибка обработки сообщения: {e}")
        import traceback
        log.error(traceback.format_exc())
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке вашего сообщения. Попробуйте еще раз."
        )

__all__ = ['reply']
