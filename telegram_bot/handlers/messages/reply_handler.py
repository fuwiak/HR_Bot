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
        # Обработка создания задачи в WEEEK
        if context.user_data.get("waiting_for_task_name"):
            project_id = context.user_data.get("selected_project_id")
            task_text = text.strip()
            
            if not project_id:
                await update.message.reply_text("❌ Ошибка: проект не выбран")
                context.user_data["waiting_for_task_name"] = False
                return
            
            if not task_text:
                await update.message.reply_text("❌ Название задачи не может быть пустым")
                return
            
            # Парсим дату из текста (форматы: "25.12", "25.12.2024", "завтра", "сегодня")
            task_date = context.user_data.get("task_date")
            task_name = task_text
            
            # Если дата не была выбрана кнопкой, пытаемся найти её в тексте
            if not task_date or task_date == "none":
                import re
                from datetime import datetime, timedelta
                
                # Паттерны для поиска даты
                date_patterns = [
                    (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', '%d.%m.%Y'),  # 25.12.2024
                    (r'(\d{1,2})\.(\d{1,2})', '%d.%m'),  # 25.12
                ]
                
                # Проверяем ключевые слова
                text_lower = task_text.lower()
                if "завтра" in text_lower:
                    task_date = (datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
                    task_name = re.sub(r'\bзавтра\b', '', task_text, flags=re.IGNORECASE).strip()
                elif "сегодня" in text_lower:
                    task_date = datetime.now().strftime('%d.%m.%Y')
                    task_name = re.sub(r'\bсегодня\b', '', task_text, flags=re.IGNORECASE).strip()
                else:
                    # Ищем дату в формате DD.MM или DD.MM.YYYY
                    for pattern, date_format in date_patterns:
                        match = re.search(pattern, task_text)
                        if match:
                            try:
                                if date_format == '%d.%m':
                                    # Добавляем текущий год
                                    date_str = match.group(0)
                                    parsed_date = datetime.strptime(date_str, '%d.%m')
                                    # Если дата уже прошла в этом году, берем следующий год
                                    if parsed_date.replace(year=datetime.now().year) < datetime.now():
                                        parsed_date = parsed_date.replace(year=datetime.now().year + 1)
                                    else:
                                        parsed_date = parsed_date.replace(year=datetime.now().year)
                                    task_date = parsed_date.strftime('%d.%m.%Y')
                                else:
                                    task_date = match.group(0)
                                
                                # Удаляем дату из названия задачи
                                task_name = re.sub(pattern, '', task_text).strip()
                                break
                            except ValueError:
                                continue
                
                if task_date == "none":
                    task_date = None
            
            # Если время было выбрано, добавляем его к дате
            if task_date and task_time and task_time != "none":
                # WEEEK API использует формат DD.MM.YYYY для даты
                # Время можно добавить в описание или использовать отдельное поле если API поддерживает
                # Пока добавляем время в описание
                task_description = f"Создано через Telegram бот\n⏰ Время: {task_time}"
            else:
                task_description = "Создано через Telegram бот"
            
            # Создаем задачу
            try:
                from services.helpers.weeek_helper import create_task, get_project
                
                await update.message.reply_text("⏳ Создаю задачу...")
                
                # Получаем название проекта для отображения
                project = await get_project(project_id)
                project_title = project.get("title", f"Проект {project_id}") if project else f"Проект {project_id}"
                
                # Создаем задачу
                task = await create_task(
                    project_id=project_id,
                    title=task_name,
                    description=task_description,
                    day=task_date
                )
                
                if task:
                    task_id = task.get("id", "")
                    response_text = f"✅ *Задача создана в WEEEK!*\n\n"
                    response_text += f"📁 *Проект:* {project_title}\n"
                    response_text += f"📝 *Задача:* {task_name}\n"
                    if task_date:
                        response_text += f"📅 *Дата:* {task_date}\n"
                    if task_time and task_time != "none":
                        response_text += f"⏰ *Время:* {task_time}\n"
                    response_text += f"🆔 *ID задачи:* `{task_id}`"
                    
                    await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)
                    log.info(f"✅ Задача создана: {task_name} в проекте {project_id}")
                else:
                    await update.message.reply_text("❌ Не удалось создать задачу в WEEEK")
                
                # Очищаем состояние
                context.user_data["waiting_for_task_name"] = False
                context.user_data["selected_project_id"] = None
                context.user_data["task_date"] = None
                context.user_data["task_time"] = None
                return
                
            except Exception as e:
                log.error(f"❌ Ошибка создания задачи: {e}")
                import traceback
                log.error(traceback.format_exc())
                await update.message.reply_text(f"❌ Ошибка создания задачи: {str(e)}")
                context.user_data["waiting_for_task_name"] = False
                context.user_data["selected_project_id"] = None
                context.user_data["task_date"] = None
                context.user_data["task_time"] = None
                return
        
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
                log.info(f"🔍 [RAG] Поиск в коллекции 'hr2137_bot_knowledge_base' для запроса: '{text[:100]}'")
                results = search_service(text, limit=3)
                if results:
                    log.info(f"✅ [RAG] Найдено {len(results)} результатов в коллекции 'hr2137_bot_knowledge_base'")
                    # Сортируем по score (уже отсортировано в search_service, но на всякий случай)
                    results_sorted = sorted(results, key=lambda x: x.get('score', 0), reverse=True)
                    rag_context = "\n\nРелевантная информация из базы знаний:\n"
                    for i, result in enumerate(results_sorted[:3], 1):
                        title = result.get('title', 'Без названия')
                        price_str = result.get('price_str', '')
                        score = result.get('score', 0)
                        # Используем price_str если есть, иначе пытаемся получить из content
                        content = result.get('content', '')
                        if price_str:
                            rag_context += f"{i}. {title} - {price_str} (релевантность: {score:.2f})\n"
                        elif content:
                            rag_context += f"{i}. {title}: {content[:200]}... (релевантность: {score:.2f})\n"
                        else:
                            rag_context += f"{i}. {title} (релевантность: {score:.2f})\n"
                else:
                    log.info(f"ℹ️ [RAG] Результаты не найдены в коллекции 'hr2137_bot_knowledge_base' для запроса: '{text[:100]}'")
            except Exception as e:
                log.warning(f"⚠️ Ошибка RAG поиска в коллекции 'hr2137_bot_knowledge_base': {e}")
        
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
