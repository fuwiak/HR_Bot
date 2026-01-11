"""
Обработчик сообщений (основная функция reply)
"""
import sys
import re
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction, ParseMode

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

log = logging.getLogger(__name__)


async def should_use_rag_async(text: str, context: Optional[Dict] = None) -> Dict[str, any]:
    """
    Определяет, нужно ли использовать RAG поиск для данного сообщения.
    Использует сервис классификации намерений.
    
    Returns:
        Dict с полями:
        - use_rag: bool - нужно ли использовать RAG
        - confidence: float - уверенность (0.0-1.0)
        - reason: str - причина решения
        - intent: str - тип намерения
    """
    try:
        from services.services.rag_intent_classifier import get_rag_intent_classifier
        
        classifier = get_rag_intent_classifier()
        result = await classifier.should_use_rag(text, context)
        return result
    except Exception as e:
        log.warning(f"⚠️ [RAG Intent] Ошибка классификации: {e}")
        # Fallback на простую логику
        return {
            "use_rag": len(text.split()) >= 5,
            "confidence": 0.5,
            "reason": "Fallback из-за ошибки классификации",
            "intent": "fallback"
        }


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
    # Обрабатываем channel_post если есть
    if update.channel_post:
        try:
            from telegram_bot.handlers.channel.hrtime_channel_handler import handle_channel_post
            await handle_channel_post(update, context)
        except Exception as e:
            log.warning(f"⚠️ Ошибка обработки channel_post: {e}")
        return
    
    if not update.message or not update.message.text:
        return
    
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    message_id = update.message.message_id
    text = update.message.text.strip()
    username = update.message.from_user.username or "без username"
    first_name = update.message.from_user.first_name or "без имени"
    
    log.info(f"💬 Получено сообщение от {user_id} (@{username}): {text[:100]}")
    
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
        # Обработка редактирования задачи
        if context.user_data.get("waiting_for_task_edit"):
            task_id = context.user_data.get("editing_task_id")
            field = context.user_data.get("editing_task_field")
            
            if not task_id or not field:
                await update.message.reply_text("❌ Ошибка: данные редактирования не найдены")
                context.user_data["waiting_for_task_edit"] = False
                context.user_data["editing_task_id"] = None
                context.user_data["editing_task_field"] = None
                return
            
            try:
                from services.helpers.weeek_helper import update_task, get_task
                from datetime import datetime
                
                if field == "title":
                    # Редактирование названия
                    new_title = text.strip()
                    if not new_title:
                        await update.message.reply_text("❌ Название задачи не может быть пустым")
                        return
                    
                    result = await update_task(task_id, title=new_title)
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    if result:
                        await update.message.reply_text(
                            f"✅ *Название задачи обновлено!*\n\n"
                            f"📝 Новое название: *{new_title}*",
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=reply_markup
                        )
                    else:
                        await update.message.reply_text("❌ Ошибка обновления названия задачи", reply_markup=reply_markup)
                
                elif field == "date":
                    # Редактирование даты
                    date_input = text.strip().lower()
                    
                    if date_input == "нет" or date_input == "no":
                        # Удаляем дату
                        result = await update_task(task_id, due_date="")
                        if result:
                            await update.message.reply_text("✅ Дата удалена из задачи")
                        else:
                            await update.message.reply_text("❌ Ошибка удаления даты")
                    else:
                        # Парсим дату
                        import re
                        from datetime import timedelta
                        
                        date_str = None
                        text_lower = date_input
                        
                        if "завтра" in text_lower:
                            date_str = (datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
                        elif "сегодня" in text_lower:
                            date_str = datetime.now().strftime('%d.%m.%Y')
                        else:
                            # Ищем дату в формате DD.MM или DD.MM.YYYY
                            date_patterns = [
                                (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', '%d.%m.%Y'),
                                (r'(\d{1,2})\.(\d{1,2})', '%d.%m'),
                            ]
                            
                            for pattern, date_format in date_patterns:
                                match = re.search(pattern, date_input)
                                if match:
                                    try:
                                        if date_format == '%d.%m':
                                            date_str = match.group(0)
                                            parsed_date = datetime.strptime(date_str, '%d.%m')
                                            if parsed_date.replace(year=datetime.now().year) < datetime.now():
                                                parsed_date = parsed_date.replace(year=datetime.now().year + 1)
                                            else:
                                                parsed_date = parsed_date.replace(year=datetime.now().year)
                                            date_str = parsed_date.strftime('%d.%m.%Y')
                                        else:
                                            date_str = match.group(0)
                                        break
                                    except ValueError:
                                        continue
                        
                        if date_str:
                            # Конвертируем в формат API
                            try:
                                date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                                api_date = date_obj.strftime('%Y-%m-%d')
                                result = await update_task(task_id, due_date=api_date)
                                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                                keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
                                reply_markup = InlineKeyboardMarkup(keyboard)
                                if result:
                                    await update.message.reply_text(
                                        f"✅ *Дата задачи обновлена!*\n\n"
                                        f"📅 Новая дата: *{date_str}*",
                                        parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=reply_markup
                                    )
                                else:
                                    await update.message.reply_text("❌ Ошибка обновления даты", reply_markup=reply_markup)
                            except ValueError:
                                await update.message.reply_text("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ или ДД.ММ")
                        else:
                            await update.message.reply_text(
                                "❌ Неверный формат даты.\n\n"
                                "Используйте:\n"
                                "• `25.12.2024` или `25.12`\n"
                                "• `сегодня` / `завтра`\n"
                                "• `нет` - удалить дату"
                            )
                
                # Очищаем состояние
                context.user_data["waiting_for_task_edit"] = False
                context.user_data["editing_task_id"] = None
                context.user_data["editing_task_field"] = None
                return
                
            except Exception as e:
                log.error(f"❌ Ошибка редактирования задачи: {e}")
                import traceback
                log.error(traceback.format_exc())
                await update.message.reply_text(f"❌ Ошибка редактирования: {str(e)}")
                context.user_data["waiting_for_task_edit"] = False
                context.user_data["editing_task_id"] = None
                context.user_data["editing_task_field"] = None
                return
        
        # Обработка ввода произвольного времени для задачи
        if context.user_data.get("waiting_for_task_time"):
            time_input = text.strip().lower()
            
            # Проверяем формат времени (ЧЧ:ММ)
            import re
            time_pattern = r'^(\d{1,2}):(\d{2})$'
            match = re.match(time_pattern, text.strip())
            
            if time_input == "нет" or time_input == "no":
                context.user_data["task_time"] = None
                context.user_data["waiting_for_task_time"] = False
                
                date_str = context.user_data.get("task_date", "не указана")
                keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="menu_projects")]]
                await update.message.reply_text(
                    f"✅ Дата: *{date_str}*\n"
                    f"✅ Время: *не указано*\n\n"
                    "📝 Теперь отправьте название задачи текстовым сообщением.\n\n"
                    "💡 *Пример:*\n"
                    "`Согласовать КП с клиентом`",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            elif match:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                
                # Проверяем валидность времени
                if 0 <= hours <= 23 and 0 <= minutes <= 59:
                    time_str = f"{hours:02d}:{minutes:02d}"
                    context.user_data["task_time"] = time_str
                    context.user_data["waiting_for_task_time"] = False
                    
                    date_str = context.user_data.get("task_date", "не указана")
                    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="menu_projects")]]
                    await update.message.reply_text(
                        f"✅ Дата: *{date_str}*\n"
                        f"✅ Время: *{time_str}*\n\n"
                        "📝 Теперь отправьте название задачи текстовым сообщением.\n\n"
                        "💡 *Пример:*\n"
                        "`Согласовать КП с клиентом`",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return
                else:
                    await update.message.reply_text(
                        "❌ Неверный формат времени.\n\n"
                        "Используйте формат ЧЧ:ММ (например: 14:30)\n"
                        "Часы: 0-23, минуты: 0-59"
                    )
                    return
            else:
                await update.message.reply_text(
                    "❌ Неверный формат времени.\n\n"
                    "Используйте формат ЧЧ:ММ (например: 14:30)\n"
                    "Или отправьте `нет` чтобы пропустить время."
                )
                return
        
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
            task_time = context.user_data.get("task_time")
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
                    
                    # Добавляем кнопки для редактирования задачи
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    keyboard = [
                        [InlineKeyboardButton("✏️ Редактировать задачу", callback_data=f"weeek_edit_task_{task_id}")],
                        [InlineKeyboardButton("📅 Изменить дату", callback_data=f"weeek_edit_date_{task_id}")],
                        [InlineKeyboardButton("➕ Создать еще задачу", callback_data="weeek_create_task_menu")],
                        [InlineKeyboardButton("🔙 В меню проектов", callback_data="menu_projects")],
                        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
                    ]
                    
                    await update.message.reply_text(
                        response_text, 
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
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
        
        # Обновляем индикатор перед RAG поиском
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        
        # Определяем, нужно ли использовать RAG поиск через сервис классификации
        rag_decision = await should_use_rag_async(text, context={"user_id": user_id})
        use_rag = rag_decision.get("use_rag", False)
        rag_context = ""
        rag_documents = []  # Сохраняем информацию о найденных документах для логирования и RAGAS
        
        log.info(f"🔍 [RAG Decision] use_rag={use_rag}, intent={rag_decision.get('intent')}, confidence={rag_decision.get('confidence', 0):.2f}, reason={rag_decision.get('reason')}")
        
        if use_rag:
            log.info(f"🔍 [RAG] Запрос требует поиска в базе знаний: '{text[:100]}'")
        try:
            from services.rag.qdrant_helper import get_qdrant_client, generate_embedding_async
            
            log.info(f"🔍 [RAG] Поиск в базе знаний для запроса: '{text[:100]}'")
            
            client = get_qdrant_client()
            if client:
                # Генерируем эмбеддинг для запроса
                query_embedding = await generate_embedding_async(text)
                
                if query_embedding:
                    collection_name = "hr2137_bot_knowledge_base"
                    
                    try:
                        # Ищем в Qdrant
                        search_results = client.query_points(
                            collection_name=collection_name,
                            query=query_embedding,
                            limit=5
                        )
                        
                        if search_results.points:
                            log.info(f"✅ [RAG] Найдено {len(search_results.points)} результатов в базе знаний")
                            
                            # Собираем результаты
                            results = []
                            for point in search_results.points:
                                payload = point.payload if hasattr(point, 'payload') else {}
                                score = point.score if hasattr(point, 'score') else 0.0
                                
                                # Извлекаем информацию о документе
                                file_name = payload.get("file_name") or payload.get("title") or payload.get("source", "Документ")
                                text_content = payload.get("text") or payload.get("content", "")
                                
                                if text_content and score > 0.3:  # Минимальный порог релевантности
                                    results.append({
                                        "file_name": file_name,
                                        "text": text_content,
                                        "score": score
                                    })
                            
                            # Сортируем по score и берем топ-3
                            results_sorted = sorted(results, key=lambda x: x.get('score', 0), reverse=True)[:3]
                            
                            if results_sorted:
                                rag_context = "\n\n📚 Релевантная информация из базы знаний:\n\n"
                                for i, result in enumerate(results_sorted, 1):
                                    file_name = result.get('file_name', 'Документ')
                                    text_snippet = result.get('text', '')[:300]  # Первые 300 символов
                                    score = result.get('score', 0)
                                    rag_context += f"{i}. {file_name} (релевантность: {score:.2f}):\n{text_snippet}...\n\n"
                                    
                                    # Сохраняем полные тексты документов для RAGAS оценки
                                    rag_documents = [r.get('text', '') for r in results_sorted]
                                    
                                    # Детальное логирование найденных документов
                                    log.info(f"✅ [RAG] Сформирован контекст из {len(results_sorted)} документов:")
                                    for i, result in enumerate(results_sorted, 1):
                                        file_name = result.get('file_name', 'Документ')
                                        score = result.get('score', 0)
                                        text_length = len(result.get('text', ''))
                                        log.info(f"  📄 Документ {i}: {file_name} | Релевантность: {score:.3f} | Длина: {text_length} символов")
                            else:
                                log.info(f"ℹ️ [RAG] Результаты найдены, но не прошли порог релевантности")
                        else:
                            log.info(f"ℹ️ [RAG] Результаты не найдены в базе знаний для запроса: '{text[:100]}'")
                    except Exception as search_error:
                        error_str = str(search_error).lower()
                        if "timeout" in error_str or "timed out" in error_str:
                            log.warning(f"⚠️ [RAG] Таймаут при поиске в базе знаний: {search_error}")
                        else:
                            log.warning(f"⚠️ [RAG] Ошибка поиска в базе знаний: {search_error}")
                else:
                    log.warning(f"⚠️ [RAG] Не удалось создать эмбеддинг для запроса")
            else:
                log.warning(f"⚠️ [RAG] Qdrant клиент недоступен")
        except Exception as e:
            log.warning(f"⚠️ Ошибка RAG поиска: {e}")
            import traceback
            log.debug(traceback.format_exc())
        else:
            log.info(f"ℹ️ [RAG] Запрос не требует поиска в базе знаний (приветствие/простой вопрос): '{text[:100]}'")
        
        # Формируем промпт с подстановкой переменных
        system_prompt = CHAT_PROMPT
        
        # Подставляем RAG контекст (если есть)
        if rag_context:
            system_prompt = system_prompt.replace("{{rag_context}}", rag_context)
        else:
            system_prompt = system_prompt.replace("{{rag_context}}", "")
        
        # Подставляем историю
        history_text = history if history else "Истории разговора нет."
        system_prompt = system_prompt.replace("{{history}}", history_text)
        
        # Подставляем текущее сообщение
        system_prompt = system_prompt.replace("{{message}}", text)
        
        # Формируем сообщения для LLM
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Добавляем текущее сообщение как user сообщение (для совместимости)
        messages.append({"role": "user", "content": text})
        
        # Обновляем индикатор перед генерацией ответа (может занять время)
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        
        # Создаем задачу для периодического обновления typing индикатора во время долгой генерации
        import asyncio
        typing_task = None
        
        async def keep_typing():
            """Периодически обновляет typing индикатор каждые 3 секунды"""
            while True:
                await asyncio.sleep(3)
                try:
                    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                except Exception:
                    break
        
        # Запускаем задачу обновления typing
        typing_task = asyncio.create_task(keep_typing())
        
        try:
        # Получаем ответ от LLM
            log.info(f"🤖 Генерация ответа для пользователя {user_id}...")
            if rag_context and rag_documents:
                log.info(f"📝 [RAG Response] Используется RAG контекст из {len(rag_documents)} документов")
                log.info(f"📝 [RAG Response] Размер контекста: {len(rag_context)} символов")
            response = await openrouter_chat(messages, use_system_message=False)
            log.info(f"✅ Ответ сгенерирован: {response[:100] if response else 'None'}...")
        finally:
            # Останавливаем задачу обновления typing
            if typing_task:
                typing_task.cancel()
                try:
                    await typing_task
                except asyncio.CancelledError:
                    pass
        
        # Обновляем индикатор перед отправкой ответа
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        
        # Детальное логирование RAG ответа - почему так отвечает
        if rag_context and rag_documents:
            log.info(f"📊 [RAG Response Analysis] Анализ ответа на основе RAG:")
            log.info(f"  ❓ Вопрос: {text[:200]}")
            log.info(f"  📚 Использовано документов: {len(rag_documents)}")
            log.info(f"  💬 Длина ответа: {len(response)} символов")
            
            # Логируем влияние каждого документа на ответ
            for i, doc_text in enumerate(rag_documents, 1):
                # Простая проверка: есть ли ключевые слова из документа в ответе
                doc_words = set(doc_text.lower().split()[:50])  # Первые 50 слов документа
                response_words = set(response.lower().split())
                common_words = doc_words.intersection(response_words)
                influence_score = len(common_words) / max(len(doc_words), 1) if doc_words else 0
                log.info(f"  📄 Документ {i}: Влияние на ответ ~{influence_score:.1%} (общих слов: {len(common_words)})")
        
        # Оценка ответа с помощью RAGAS (если использовался RAG)
        if use_rag and rag_documents and response:
            try:
                from services.rag.rag_evaluator import evaluate_rag_response, format_evaluation_log
                
                log.info(f"🔍 [RAGAS] Запуск оценки качества RAG ответа...")
                evaluation = await evaluate_rag_response(
                    question=text,
                    answer=response,
                    contexts=rag_documents
                )
                
                if evaluation:
                    log.info(format_evaluation_log(evaluation))
                    
                    # Дополнительный анализ оценок
                    if evaluation.faithfulness < 0.5:
                        log.warning(f"⚠️ [RAGAS] Низкая верность ответа ({evaluation.faithfulness:.3f}) - ответ может содержать информацию не из контекста")
                    if evaluation.answer_relevancy < 0.5:
                        log.warning(f"⚠️ [RAGAS] Низкая релевантность ответа ({evaluation.answer_relevancy:.3f}) - ответ может не соответствовать вопросу")
                    if evaluation.context_precision < 0.5:
                        log.warning(f"⚠️ [RAGAS] Низкая точность контекста ({evaluation.context_precision:.3f}) - возможно, использованы нерелевантные документы")
                    
                    if evaluation.average_score >= 0.7:
                        log.info(f"✅ [RAGAS] Высокое качество ответа (средняя оценка: {evaluation.average_score:.3f})")
                    elif evaluation.average_score >= 0.5:
                        log.info(f"ℹ️ [RAGAS] Среднее качество ответа (средняя оценка: {evaluation.average_score:.3f})")
                    else:
                        log.warning(f"⚠️ [RAGAS] Низкое качество ответа (средняя оценка: {evaluation.average_score:.3f})")
                else:
                    log.warning(f"⚠️ [RAGAS] Не удалось выполнить оценку (возможно, библиотека не установлена)")
            except Exception as e:
                log.warning(f"⚠️ [RAGAS] Ошибка при оценке ответа: {e}")
                import traceback
                log.debug(traceback.format_exc())
        
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
