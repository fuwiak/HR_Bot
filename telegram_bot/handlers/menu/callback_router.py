"""
Роутер для callback кнопок
"""
import sys
import asyncio
from pathlib import Path
from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
import logging

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

log = logging.getLogger(__name__)

# Импортируем функции из правильных модулей
try:
    from telegram_bot.handlers.commands.weeek import (
        show_weeek_projects,
        show_weeek_create_task_menu,
        show_weeek_project_details,
        show_weeek_tasks_for_update,
        show_weeek_task_edit_menu,
        handle_weeek_edit_field,
        handle_weeek_complete_task,
        handle_weeek_delete_task,
        handle_weeek_set_priority,
        handle_weeek_set_type
    )
except ImportError:
    log.warning("⚠️ WEEEK handlers не доступны")
    # Заглушки
    async def show_weeek_projects(*args, **kwargs): pass
    async def show_weeek_create_task_menu(*args, **kwargs): pass
    async def show_weeek_project_details(*args, **kwargs): pass
    async def show_weeek_tasks_for_update(*args, **kwargs): pass
    async def show_weeek_task_edit_menu(*args, **kwargs): pass
    async def handle_weeek_edit_field(*args, **kwargs): pass
    async def handle_weeek_complete_task(*args, **kwargs): pass
    async def handle_weeek_delete_task(*args, **kwargs): pass
    async def handle_weeek_set_priority(*args, **kwargs): pass
    async def handle_weeek_set_type(*args, **kwargs): pass

try:
    from telegram_bot.handlers.commands.basic import show_main_menu
except ImportError:
    log.warning("⚠️ Basic handlers не доступны")
    async def show_main_menu(*args, **kwargs): pass

try:
    from telegram_bot.handlers.commands.email import (
        handle_email_reply_last,
        handle_email_reply,
        handle_email_reply_primary,
        handle_email_reply_followup,
        handle_email_reply_report,
        handle_email_proposal,
        handle_email_task,
        handle_email_done,
        handle_email_full,
        handle_email_send_reply,
        handle_email_create_task,
        handle_email_cancel
    )
except ImportError:
    log.warning("⚠️ Email handlers не доступны")
    async def handle_email_reply_last(*args, **kwargs): pass
    async def handle_email_reply(*args, **kwargs): pass
    async def handle_email_reply_primary(*args, **kwargs): pass
    async def handle_email_reply_followup(*args, **kwargs): pass
    async def handle_email_reply_report(*args, **kwargs): pass
    async def handle_email_proposal(*args, **kwargs): pass
    async def handle_email_task(*args, **kwargs): pass
    async def handle_email_done(*args, **kwargs): pass
    async def handle_email_full(*args, **kwargs): pass
    async def handle_email_send_reply(*args, **kwargs): pass
    async def handle_email_create_task(*args, **kwargs): pass
    async def handle_email_cancel(*args, **kwargs): pass

# Временные заглушки для функций, которые нужно будет перенести
async def show_services(query, *args, **kwargs):
    await query.edit_message_text("⚠️ Функция временно недоступна")
    
async def show_services_page(query, *args, **kwargs):
    await query.edit_message_text("⚠️ Функция временно недоступна")

async def delete_user_record(query, record_id, *args, **kwargs):
    await query.edit_message_text(f"⚠️ Удаление записи {record_id} временно недоступно")

async def reset_user_session(query, *args, **kwargs):
    await query.edit_message_text("✅ Сессия сброшена")

async def start_booking_process(query, *args, **kwargs):
    await query.edit_message_text("📅 Для записи отправьте сообщение с указанием услуги и времени")

async def show_masters(query, *args, **kwargs):
    await query.edit_message_text("👥 Список мастеров временно недоступен")

async def show_user_records(query, *args, **kwargs):
    await query.edit_message_text("📋 Список записей временно недоступен")

async def save_response_rating(user_id: int, bot_message_id: int, rating: int, user_message: str, bot_response: str):
    """Сохранить оценку ответа бота"""
    try:
        import json
        import os
        from datetime import datetime
        
        # Создаем директорию для оценок, если её нет
        ratings_dir = "data/ratings"
        os.makedirs(ratings_dir, exist_ok=True)
        
        # Сохраняем в JSON файл
        rating_data = {
            "user_id": user_id,
            "bot_message_id": bot_message_id,
            "rating": rating,
            "user_message": user_message,
            "bot_response": bot_response,
            "timestamp": datetime.now().isoformat()
        }
        
        ratings_file = os.path.join(ratings_dir, "ratings.json")
        
        # Читаем существующие оценки
        ratings = []
        if os.path.exists(ratings_file):
            try:
                with open(ratings_file, 'r', encoding='utf-8') as f:
                    ratings = json.load(f)
            except:
                ratings = []
        except Exception as e:
            log.warning(f"⚠️ Ошибка чтения файла оценок: {e}")
            ratings = []
        
        # Добавляем новую оценку
        ratings.append(rating_data)
        
        # Сохраняем обратно
        with open(ratings_file, 'w', encoding='utf-8') as f:
            json.dump(ratings, f, ensure_ascii=False, indent=2)
        
        log.info(f"✅ Оценка сохранена: пользователь {user_id}, сообщение {bot_message_id}, оценка {rating}")
        
        # Также пробуем сохранить в БД, если доступна
        try:
            from backend.database import get_connection, return_connection
            conn = get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS response_ratings (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        bot_message_id BIGINT NOT NULL,
                        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                        user_message TEXT,
                        bot_response TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    INSERT INTO response_ratings (user_id, bot_message_id, rating, user_message, bot_response)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, bot_message_id, rating, user_message, bot_response))
                conn.commit()
                return_connection(conn)
                log.info(f"✅ Оценка сохранена в БД")
        except Exception as e:
            log.warning(f"⚠️ Не удалось сохранить оценку в БД: {e}")
        
        return True
    except Exception as e:
        log.error(f"❌ Ошибка сохранения оценки: {e}")
        return False


async def handle_response_rating(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Обработка оценки ответа бота"""
    try:
        # Парсим callback_data: rate_response_{bot_message_id}_{rating} или rate_response_temp_{user_message_id}_{rating}
        parts = query.data.split("_")
        if len(parts) < 4:
            await query.answer("❌ Ошибка формата оценки", show_alert=True)
            return
        
        is_temp = parts[2] == "temp"
        
        if is_temp:
            # Временный формат - используем user_message_id для поиска bot_message_id
            user_message_id = int(parts[3])
            rating = int(parts[4])
            
            # Используем message_id текущего сообщения как bot_message_id
            bot_message_id = query.message.message_id
            
            # Сохраняем связь для будущих оценок
            if f"bot_response_{bot_message_id}" not in context.user_data:
                lead_data = context.user_data.get(f"lead_message_{user_message_id}")
                if lead_data:
                    context.user_data[f"bot_response_{bot_message_id}"] = {
                        "user_message": lead_data.get("user_message", ""),
                        "bot_response": lead_data.get("bot_response", ""),
                        "user_message_id": user_message_id,
                        "timestamp": datetime.now().isoformat()
                    }
        else:
            bot_message_id = int(parts[2])
            rating = int(parts[3])
        
        if rating < 1 or rating > 5:
            await query.answer("❌ Неверная оценка", show_alert=True)
            return
        
        user_id = query.from_user.id
        
        # Получаем данные о сообщении из context
        response_data = context.user_data.get(f"bot_response_{bot_message_id}")
        if not response_data:
            # Пробуем найти через все bot_response_ ключи
            found_data = None
            for key, value in context.user_data.items():
                if key.startswith("bot_response_") and isinstance(value, dict):
                    if value.get("user_message_id"):
                        found_data = value
                        break
            
            if found_data:
                user_message = found_data.get("user_message", "")
                bot_response = found_data.get("bot_response", "")
            else:
                # Пробуем получить из lead_message через user_message_id (если был temp формат)
                if is_temp:
                    lead_data = context.user_data.get(f"lead_message_{user_message_id}")
                    if lead_data:
                        user_message = lead_data.get("user_message", "")
                        bot_response = lead_data.get("bot_response", "")
                    else:
                        user_message = ""
                        bot_response = query.message.text if query.message else ""
                else:
                    user_message = ""
                    bot_response = query.message.text if query.message else ""
        else:
            user_message = response_data.get("user_message", "")
            bot_response = response_data.get("bot_response", "")
        
        # Сохраняем оценку
        saved = await save_response_rating(user_id, bot_message_id, rating, user_message, bot_response)
        
        if saved:
            # Показываем подтверждение
            stars = "⭐" * rating
            await query.answer(f"✅ Спасибо! Оценка {rating} {stars} сохранена", show_alert=False)
            
            # Обновляем кнопки - убираем оценку, показываем что оценено
            try:
                # Получаем текущую клавиатуру
                current_markup = query.message.reply_markup
                if current_markup:
                    # Создаем новую клавиатуру без кнопок оценки
                    keyboard = []
                    for row in current_markup.inline_keyboard:
                        # Пропускаем строку с оценками
                        if not any(btn.callback_data and btn.callback_data.startswith("rate_response_") for btn in row):
                            keyboard.append(row)
                    
                    # Добавляем строку с подтверждением оценки
                    keyboard.insert(0, [
                        InlineKeyboardButton(f"✅ Оценено: {stars}", callback_data="rating_saved")
                    ])
                    
                    new_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.edit_reply_markup(reply_markup=new_markup)
            except Exception as e:
                log.warning(f"⚠️ Не удалось обновить кнопки после оценки: {e}")
        else:
            await query.answer("❌ Не удалось сохранить оценку", show_alert=True)
            
    except Exception as e:
        log.error(f"❌ Ошибка обработки оценки: {e}")
        import traceback
        log.error(traceback.format_exc())
        await query.answer("❌ Произошла ошибка при сохранении оценки", show_alert=True)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Обработка оценки ответа (поддерживаем оба формата: с bot_message_id и временный)
    if query.data.startswith("rate_response_"):
        await handle_response_rating(query, context)
        return
    
    # Обработка уже сохраненной оценки (просто подтверждаем)
    if query.data == "rating_saved":
        await query.answer("Оценка уже сохранена", show_alert=False)
        return
    
    # Главное меню и подменю
    if query.data == "back_to_menu" or query.data == "menu_main":
        await show_main_menu(query)
        return
    
    # Подменю "База знаний"
    elif query.data == "menu_knowledge_base":
        keyboard = [
            [
                InlineKeyboardButton("🔍 Поиск", callback_data="rag_search_menu"),
                InlineKeyboardButton("📚 Документы", callback_data="rag_docs")
            ],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="rag_stats"),
                InlineKeyboardButton("📤 Загрузить", callback_data="rag_upload_menu")
            ],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        message_text = (
            "📚 *База знаний*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔍 *Поиск* — семантический поиск\n"
            "   по методикам, кейсам, шаблонам\n\n"
            "📚 *Документы* — список всех\n"
            "   документов в базе\n\n"
            "📊 *Статистика* — информация\n"
            "   о базе знаний\n\n"
            "📤 *Загрузить* — инструкция\n"
            "   по загрузке документов"
        )
        await query.edit_message_text(
            message_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Подменю "Проекты"
    elif query.data == "menu_projects":
        keyboard = [
            [
                InlineKeyboardButton("📋 Мои проекты", callback_data="weeek_list_projects"),
                InlineKeyboardButton("➕ Создать задачу", callback_data="weeek_create_task_menu")
            ],
            [
                InlineKeyboardButton("📊 Статус", callback_data="status"),
                InlineKeyboardButton("📝 Суммаризация", callback_data="summary_menu")
            ],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "📋 *Управление проектами*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 *Мои проекты* — список проектов\n"
            "➕ *Создать задачу* — новая задача\n"
            "📊 *Статус* — ближайшие дедлайны\n"
            "📝 *Суммаризация* — сводка по проекту",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Подменю "Инструменты"
    elif query.data == "menu_tools":
        keyboard = [
            [
                InlineKeyboardButton("📝 Генерация КП", callback_data="generate_proposal"),
                InlineKeyboardButton("📄 Суммаризация", callback_data="quick_summary_menu")
            ],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "🛠 *Инструменты*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📝 *Генерация КП* — создать\n"
            "   коммерческое предложение\n\n"
            "📄 *Суммаризация* — краткая\n"
            "   сводка текста",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Подменю "Помощь"
    elif query.data == "menu_help":
        keyboard = [
            [
                InlineKeyboardButton("📖 Команды", callback_data="help_commands"),
                InlineKeyboardButton("💡 Примеры", callback_data="help_examples")
            ],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "❓ *Помощь*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📖 *Команды* — список всех команд\n"
            "💡 *Примеры* — примеры использования",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Обработчики WEEEK
    elif query.data == "weeek_list_projects":
        await show_weeek_projects(query)
        return
    
    elif query.data == "weeek_create_task_menu":
        await show_weeek_create_task_menu(query)
        return
    
    elif query.data.startswith("weeek_select_project_"):
        project_id = query.data.replace("weeek_select_project_", "")
        context.user_data["selected_project_id"] = project_id
        context.user_data["waiting_for_task_name"] = True
        
        # Показываем кнопки для быстрого выбора даты
        from datetime import datetime, timedelta
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        
        keyboard = [
            [InlineKeyboardButton("📅 Сегодня", callback_data=f"weeek_date_{today.strftime('%d.%m.%Y')}")],
            [InlineKeyboardButton("📅 Завтра", callback_data=f"weeek_date_{tomorrow.strftime('%d.%m.%Y')}")],
            [InlineKeyboardButton("📅 Через неделю", callback_data=f"weeek_date_{next_week.strftime('%d.%m.%Y')}")],
            [InlineKeyboardButton("📝 Без даты", callback_data="weeek_date_none")],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]
        ]
        
        await query.edit_message_text(
            "✅ *Проект выбран!*\n\n"
            "📝 *Шаг 1: Название задачи*\n"
            "Отправьте название задачи текстовым сообщением.\n\n"
            "📅 *Шаг 2: Дата (опционально)*\n"
            "Выберите дату кнопкой ниже или отправьте свою дату после названия.\n\n"
            "💡 *Пример:*\n"
            "`Согласовать КП с клиентом`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif query.data.startswith("weeek_date_"):
        # Обработка выбора даты
        date_str = query.data.replace("weeek_date_", "")
        
        if date_str == "none":
            context.user_data["task_date"] = None
            context.user_data["task_time"] = None
            await query.answer("✅ Задача будет создана без даты")
        else:
            context.user_data["task_date"] = date_str
            # Показываем кнопки для выбора времени
            keyboard = [
                [InlineKeyboardButton("🕐 09:00", callback_data=f"weeek_time_{date_str}_09:00")],
                [InlineKeyboardButton("🕐 12:00", callback_data=f"weeek_time_{date_str}_12:00")],
                [InlineKeyboardButton("🕐 15:00", callback_data=f"weeek_time_{date_str}_15:00")],
                [InlineKeyboardButton("🕐 18:00", callback_data=f"weeek_time_{date_str}_18:00")],
                [InlineKeyboardButton("✏️ Ввести своё время", callback_data=f"weeek_time_custom_{date_str}")],
                [InlineKeyboardButton("⏰ Без времени", callback_data=f"weeek_time_{date_str}_none")],
                [InlineKeyboardButton("🔙 Назад", callback_data=f"weeek_select_project_{context.user_data.get('selected_project_id')}")]
            ]
            
            await query.edit_message_text(
                f"✅ Дата выбрана: *{date_str}*\n\n"
                "⏰ *Выберите время (опционально):*",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Если дата не выбрана, показываем сообщение о вводе названия
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="menu_projects")]]
        await query.edit_message_text(
            "✅ Дата: не указана\n\n"
            "📝 Теперь отправьте название задачи текстовым сообщением.\n\n"
            "💡 *Пример:*\n"
            "`Согласовать КП с клиентом`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif query.data.startswith("weeek_time_custom_"):
        # Обработка запроса на ввод произвольного времени
        date_str = query.data.replace("weeek_time_custom_", "")
        context.user_data["task_date"] = date_str
        context.user_data["waiting_for_task_time"] = True
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"weeek_date_{date_str}")]]
        await query.edit_message_text(
            f"✅ Дата: *{date_str}*\n\n"
            "⏰ *Введите время в формате ЧЧ:ММ*\n\n"
            "💡 *Примеры:*\n"
            "• `14:30`\n"
            "• `09:15`\n"
            "• `18:45`\n\n"
            "Или отправьте `нет` чтобы пропустить время.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif query.data.startswith("weeek_time_"):
        # Обработка выбора времени
        # Формат: weeek_time_DD.MM.YYYY_HH:MM или weeek_time_DD.MM.YYYY_none
        parts = query.data.replace("weeek_time_", "").split("_", 1)
        if len(parts) == 2:
            date_str = parts[0]
            time_str = parts[1]
            
            context.user_data["task_date"] = date_str
            if time_str == "none":
                context.user_data["task_time"] = None
                await query.answer("✅ Время не указано")
            else:
                context.user_data["task_time"] = time_str
                await query.answer(f"✅ Время выбрано: {time_str}")
            
            # Показываем сообщение о вводе названия
            keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="menu_projects")]]
            time_display = f"{time_str}" if time_str != "none" else "не указано"
            await query.edit_message_text(
                f"✅ Дата: *{date_str}*\n"
                f"✅ Время: *{time_display}*\n\n"
                "📝 Теперь отправьте название задачи текстовым сообщением.\n\n"
                "💡 *Пример:*\n"
                "`Согласовать КП с клиентом`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    elif query.data.startswith("weeek_view_project_"):
        await show_weeek_project_details(query, context)
        return
    
    elif query.data.startswith("weeek_update_select_project_"):
        await show_weeek_tasks_for_update(query, context)
        return
    
    elif query.data.startswith("weeek_edit_task_"):
        await show_weeek_task_edit_menu(query, context)
        return
    
    elif query.data.startswith("weeek_edit_field_"):
        await handle_weeek_edit_field(query, context)
        return
    
    elif query.data.startswith("weeek_edit_title_"):
        from telegram_bot.handlers.commands.weeek import handle_weeek_edit_title
        await handle_weeek_edit_title(query, context)
        return
    
    elif query.data.startswith("weeek_edit_date_"):
        from telegram_bot.handlers.commands.weeek import handle_weeek_edit_date
        await handle_weeek_edit_date(query, context)
        return
    
    elif query.data.startswith("weeek_edit_date_select_"):
        # Обработка выбора даты при редактировании
        # Формат: weeek_edit_date_select_taskId_date
        parts = query.data.replace("weeek_edit_date_select_", "").split("_", 1)
        if len(parts) == 2:
            task_id = parts[0]
            date_str = parts[1]
            
            try:
                from services.helpers.weeek_helper import update_task, get_task
                
                if date_str == "none":
                    # Удаляем дату - используем пустую строку или None
                    result = await update_task(task_id, due_date="")
                    if result:
                        await query.answer("✅ Дата удалена")
                    else:
                        await query.answer("❌ Ошибка обновления даты")
                else:
                    # Конвертируем формат DD.MM.YYYY в YYYY-MM-DD для API
                    from datetime import datetime
                    try:
                        date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                        api_date = date_obj.strftime('%Y-%m-%d')
                        result = await update_task(task_id, due_date=api_date)
                        if result:
                            await query.answer(f"✅ Дата обновлена: {date_str}")
                        else:
                            await query.answer("❌ Ошибка обновления даты")
                    except ValueError:
                        await query.answer("❌ Неверный формат даты")
                        return
                
                # Обновляем меню редактирования
                query.data = f"weeek_edit_task_{task_id}"
                from telegram_bot.handlers.commands.weeek import show_weeek_task_edit_menu
                await show_weeek_task_edit_menu(query, context)
            except Exception as e:
                log.error(f"❌ Ошибка обновления даты: {e}")
                await query.answer(f"❌ Ошибка: {str(e)}")
        return
    
    elif query.data.startswith("weeek_complete_"):
        await handle_weeek_complete_task(query, context)
        return
    
    elif query.data.startswith("weeek_delete_"):
        await handle_weeek_delete_task(query, context)
        return
    
    elif query.data.startswith("weeek_set_priority_"):
        await handle_weeek_set_priority(query, context)
        return
    
    elif query.data.startswith("weeek_set_type_"):
        await handle_weeek_set_type(query, context)
        return
    
    # Обработчики помощи
    elif query.data == "help_commands":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_help")]]
        await query.edit_message_text(
            "📖 *Команды бота*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🏠 *Основные:*\n"
            "`/start` — главное меню\n"
            "`/menu` — главное меню\n\n"
            "📚 *База знаний:*\n"
            "`/rag_search [запрос]` — поиск\n"
            "`/rag_upload` — загрузка документов\n"
            "`/rag_stats` — статистика\n"
            "`/rag_docs` — список документов\n"
            "`/rag_upload` — загрузка документов\n\n"
            "📋 *WEEEK проекты:*\n"
            "`/weeek_info` — workspace info\n"
            "`/weeek_projects` — список проектов\n"
            "`/weeek_create_project [название]`\n"
            "`/weeek_tasks [id] [фильтры]`\n"
            "`/weeek_task [проект] | [задача]`\n"
            "`/weeek_update` — обновить задачу\n"
            "`/status` — статус проектов\n\n"
            "📧 *Email:*\n"
            "`/email_check` — проверить письма\n"
            "`/email_draft [текст]` — черновик\n\n"
            "🛠 *Генерация:*\n"
            "`/demo_proposal [запрос]` — КП\n"
            "`/summary [проект]` — суммаризация\n"
            "💡 *Совет:* Ответьте на сообщение из канала командой `/demo_proposal` или `/summary`\n\n"
            "📤 *Загрузка:*\n"
            "`/upload` — инструкция\n"
            "Отправьте PDF/Word/Excel файл",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    elif query.data == "help_examples":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_help")]]
        await query.edit_message_text(
            "💡 *Примеры использования*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔍 *Поиск:*\n"
            "`/rag_search автоматизация HR`\n"
            "`/rag_search бизнес-анализ`\n\n"
            "📝 *Генерация КП:*\n"
            "`/demo_proposal нужна помощь с автоматизацией HR-процессов`\n"
            "💡 Или ответьте на сообщение из канала командой `/demo_proposal`\n\n"
            "📋 *Проекты:*\n"
            "`/status` — список проектов\n"
            "`/summary Проект X` — сводка",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Суммаризация
    elif query.data == "summary_menu":
        try:
            from services.helpers.weeek_helper import get_projects
            await query.edit_message_text("⏳ Загружаю проекты...")
            projects = await get_projects()
            if not projects:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
                await query.edit_message_text(
                    "❌ *Проекты не найдены*\n\n"
                    "Сначала создайте проекты в WEEEK.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            keyboard = []
            # Группируем кнопки по 2 в ряд
            for i in range(0, len(projects[:10]), 2):
                row = []
                row.append(InlineKeyboardButton(
                    f"📝 {projects[i].get('title', 'Без названия')[:20]}",
                    callback_data=f"summary_project_{projects[i].get('id')}"
                ))
                if i + 1 < len(projects[:10]):
                    row.append(InlineKeyboardButton(
                        f"📝 {projects[i+1].get('title', 'Без названия')[:20]}",
                        callback_data=f"summary_project_{projects[i+1].get('id')}"
                    ))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")])
            await query.edit_message_text(
                "📝 *Суммаризация проекта*\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Выберите проект:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            log.error(f"❌ Ошибка: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return  
    
    elif query.data.startswith("summary_project_"):
        try:
            project_id = query.data.replace("summary_project_", "")
            
            from services.helpers.weeek_helper import get_project, get_tasks
            from telegram_bot.handlers.commands.tools import summary_command
            
            await query.edit_message_text("⏳ Суммаризирую проект...")
            
            project = await get_project(project_id)
            if not project:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="summary_menu")]]
                await query.edit_message_text(
                    "❌ Проект не найден",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            project_title = project.get("title", project.get("name", "Без названия"))
            
            # Получаем задачи проекта
            tasks_result = await get_tasks(project_id=project_id, per_page=50)
            tasks = tasks_result.get("tasks", []) if tasks_result.get("success") else []
            
            # Формируем сводку
            text = (
                f"📝 *Суммаризация проекта*\n"
                f"*{project_title}*\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            
            if tasks:
                completed = sum(1 for t in tasks if t.get("isCompleted", False))
                active = len(tasks) - completed
                high_priority = sum(1 for t in tasks if t.get("priority") == 2)
                
                text += "📊 *Статистика:*\n"
                text += f"📋 Всего: {len(tasks)}\n"
                text += f"✅ Завершено: {completed}\n"
                text += f"⏳ Активных: {active}\n"
                if high_priority > 0:
                    text += f"🔴 Высокий приоритет: {high_priority}\n"
                text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                text += "📋 *Последние задачи:*\n\n"
                
                # Последние задачи
                recent_tasks = tasks[:5]
                for task in recent_tasks:
                    task_title = task.get("title", task.get("name", "Без названия"))
                    is_completed = task.get("isCompleted", False)
                    status = "✅" if is_completed else "⏳"
                    text += f"{status} *{task_title}*\n"
            else:
                text += "❌ Задач в проекте не найдено.\n"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="summary_menu")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            
            await query.edit_message_text(
                text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        except Exception as e:
            log.error(f"❌ Ошибка суммаризации: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="summary_menu")]]
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    elif query.data == "quick_summary_menu":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_tools")]]
        await query.edit_message_text(
            "📄 *Быстрая суммаризация*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Способы использования:**\n\n"
            "1️⃣ Команда с текстом:\n"
            "`/summary [название проекта]`\n\n"
            "2️⃣ Ответ на сообщение из канала:\n"
            "Перейдите в канал https://t.me/HRAI_ANovoselova_Leads\n"
            "Ответьте на нужное сообщение командой `/summary`\n\n"
            "💡 *Совет:* При ответе на сообщение система автоматически суммаризирует текст этого сообщения",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Новые обработчики для консалтингового меню
    elif query.data == "rag_search_menu":
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_knowledge_base")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "🔍 *Поиск в базе знаний*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Используйте команду:\n"
            "`/rag_search [ваш запрос]`\n\n"
            "💡 *Примеры:*\n"
            "• `/rag_search автоматизация HR`\n"
            "• `/rag_search бизнес-анализ`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "generate_proposal":
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_tools")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "📝 *Генерация КП*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Способы использования:**\n\n"
            "1️⃣ Текст запроса:\n"
            "`/demo_proposal нужна помощь с автоматизацией HR-процессов`\n\n"
            "2️⃣ Ответ на сообщение из канала:\n"
            "Перейдите в канал https://t.me/HRAI_ANovoselova_Leads\n"
            "Ответьте на нужное сообщение командой `/demo_proposal`\n\n"
            "💡 *Совет:* При ответе на сообщение из канала система автоматически использует текст этого сообщения для генерации КП",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "rag_stats":
        try:
            from services.rag.qdrant_helper import get_collection_stats
            stats = await get_collection_stats()
            
            if "error" in stats:
                text = f"❌ Ошибка: {stats['error']}"
            else:
                text = (
                    "📊 *Статистика базы знаний*\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📚 Коллекция: `{stats.get('collection_name', 'N/A')}`\n"
                    f"✅ Статус: {'Активна' if stats.get('exists') else 'Не найдена'}\n"
                )
                if stats.get('exists'):
                    text += f"📄 Документов: {stats.get('points_count', 0)}\n"
                    text += f"🔢 Размерность: {stats.get('vector_size', 'N/A')}\n"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="menu_knowledge_base")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            log.error(f"❌ Ошибка получения статистики: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    elif query.data == "rag_docs":
        try:
            from services.rag.qdrant_helper import list_documents
            docs = await list_documents(limit=20)
            
            if docs:
                text = (
                    f"📚 Документы в базе\n"
                    f"Показано: {len(docs)}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                )
                for i, doc in enumerate(docs[:10], 1):
                    title = doc.get("title", "Без названия")
                    category = doc.get("category", "Неизвестно")
                    text += f"{i}. 📄 {title}\n"
                    text += f"   🏷 {category}\n\n"
                if len(docs) > 10:
                    text += f"...и еще {len(docs) - 10} документов"
            else:
                text = "❌ В базе знаний нет документов."
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="menu_knowledge_base")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            log.error(f"❌ Ошибка получения списка документов: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    elif query.data == "rag_upload_menu":
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_knowledge_base")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        text = (
            "📤 *Загрузка документов в базу знаний*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "*Как загрузить документ:*\n\n"
            "1️⃣ Просто отправьте файл боту\n"
            "   (перетащите файл в чат или\n"
            "   используйте кнопку \"📎\")\n\n"
            "2️⃣ Бот автоматически:\n"
            "   • Извлечет текст из документа\n"
            "   • Разобьет на части (чанки)\n"
            "   • Создаст векторные представления\n"
            "   • Загрузит в базу знаний\n\n"
            "*Поддерживаемые форматы:*\n"
            "• 📄 PDF (`.pdf`)\n"
            "• 📝 Word (`.docx`, `.doc`)\n"
            "• 📊 Excel (`.xlsx`, `.xls`)\n"
            "• 📋 Текст (`.txt`)\n"
            "• 📝 Markdown (`.md`)\n\n"
            "*Ограничения:*\n"
            "• Максимальный размер: 20 МБ\n"
            "• Документ должен содержать текст\n\n"
            "*После загрузки:*\n"
            "Используйте `/rag_search [запрос]`\n"
            "для поиска информации в\n"
            "загруженных документах.\n\n"
            "*Примеры:*\n"
            "• `/rag_search автоматизация HR`\n"
            "• `/rag_search бизнес-анализ`"
        )
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "status":
        try:
            from services.helpers.weeek_helper import get_project_deadlines
            
            await query.edit_message_text("⏳ Загружаю задачи...")
            
            # Получаем проекты с ближайшими дедлайнами
            upcoming_tasks = await get_project_deadlines(days_ahead=7)
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            
            if upcoming_tasks:
                text = (
                    "📊 *Статус проектов*\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📅 *Дедлайны на 7 дней*\n\n"
                )
                
                for task in upcoming_tasks[:10]:  # Показываем первые 10
                    task_name = task.get("name", task.get("title", "Задача"))
                    due_date = task.get("due_date", "Не указан")
                    status = task.get("status", "Активна")
                    
                    # Иконка статуса
                    status_icon = "✅" if status == "Завершена" else "⏳"
                    
                    text += f"{status_icon} *{task_name}*\n"
                    text += f"   📅 {due_date}\n"
                    text += f"   📊 {status}\n\n"
                
                if len(upcoming_tasks) > 10:
                    text += f"_...и еще {len(upcoming_tasks) - 10} задач_"
            else:
                text = (
                    "📊 *Статус проектов*\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "✅ Нет задач с ближайшими дедлайнами\n\n"
                    "Используйте WEEEK для управления проектами."
                )
            
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            log.error(f"❌ Ошибка получения статуса: {e}")
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "chat":
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
        await query.edit_message_text(
            "💬 *Чат с AI*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Теперь вы можете писать сообщения\n"
            "для общения с AI-помощником.\n\n"
            "🤖 Ассистент использует базу знаний\n"
            "для формирования ответов.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    # Старые обработчики (для обратной совместимости, можно будет удалить)
    elif query.data == "services":
        await show_services(query)
    elif query.data == "masters":
        await show_masters(query)
    elif query.data == "my_records":
        await show_user_records(query)
    elif query.data == "book_appointment":
        await start_booking_process(query)
    elif query.data == "back_to_menu":
        await show_main_menu(query)
    elif query.data.startswith("delete_record_"):
        # Старый формат для обратной совместимости
        record_id = query.data.replace("delete_record_", "")
        try:
            record_id_int = int(record_id)
            await delete_user_record(query, str(record_id_int))
        except ValueError:
            await delete_user_record(query, record_id)
    elif query.data.startswith("delete_booking_"):
        # Новый формат с booking_id из Google Sheets
        booking_id = query.data.replace("delete_booking_", "")
        await delete_user_record(query, booking_id)
    elif query.data == "reset_session":
        await reset_user_session(query)
    elif query.data.startswith("delete_booking_"):
        # Новый формат с booking_id из Google Sheets
        booking_id = query.data.replace("delete_booking_", "")
        await delete_user_record(query, booking_id)
    elif query.data == "reset_session":
        await reset_user_session(query)
    elif query.data.startswith("services_page_"):
        await show_services_page(query)
    
    # Обработчики для действий с письмами
    elif query.data == "email_reply_last":
        # Обработка кнопки "Ответить на последний мейл"
        await handle_email_reply_last(query)
    elif query.data.startswith("email_reply_primary_"):
        email_id = query.data.replace("email_reply_primary_", "")
        await handle_email_reply_primary(query, email_id)
    elif query.data.startswith("email_reply_followup_"):
        email_id = query.data.replace("email_reply_followup_", "")
        await handle_email_reply_followup(query, email_id)
    elif query.data.startswith("email_reply_proposal_"):
        email_id = query.data.replace("email_reply_proposal_", "")
        await handle_email_proposal(query, email_id)
    elif query.data.startswith("email_reply_report_"):
        email_id = query.data.replace("email_reply_report_", "")
        await handle_email_reply_report(query, email_id)
    elif query.data.startswith("email_reply_"):
        email_id = query.data.replace("email_reply_", "")
        await handle_email_reply(query, email_id)
    elif query.data.startswith("email_proposal_"):
        email_id = query.data.replace("email_proposal_", "")
        await handle_email_proposal(query, email_id)
    elif query.data.startswith("email_task_"):
        email_id = query.data.replace("email_task_", "")
        await handle_email_task(query, email_id)
    elif query.data.startswith("email_done_"):
        email_id = query.data.replace("email_done_", "")
        await handle_email_done(query, email_id)
    elif query.data.startswith("email_full_"):
        email_id = query.data.replace("email_full_", "")
        await handle_email_full(query, email_id)
    elif query.data.startswith("email_send_reply_"):
        email_id = query.data.replace("email_send_reply_", "")
        await handle_email_send_reply(query, email_id)
    elif query.data.startswith("email_task_create_"):
        # Формат: email_task_create_{email_id}_{project_id}
        parts = query.data.replace("email_task_create_", "").split("_", 1)
        if len(parts) == 2:
            email_id = parts[0]
            project_id = int(parts[1])
            await handle_email_create_task(query, email_id, project_id)
    elif query.data.startswith("email_cancel_"):
        email_id = query.data.replace("email_cancel_", "")
        await handle_email_cancel(query, email_id)
    
    # Обработчики кнопок для сообщений
    elif query.data.startswith("lead_confirm_"):
        # Обработка кнопки "Подтвердить ответ"
        message_id = query.data.replace("lead_confirm_", "")
        message_data = context.user_data.get(f"lead_message_{message_id}")
        
        if message_data:
            # Показываем typing индикатор
            chat_id = query.message.chat.id
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            
            await query.answer("✅ Ответ подтвержден", show_alert=False)
            await query.edit_message_reply_markup(reply_markup=None)  # Убираем кнопки
            log.info(f"✅ Ответ подтвержден для сообщения {message_id}")
        else:
            await query.answer("❌ Данные сообщения не найдены", show_alert=True)
    
    elif query.data.startswith("lead_proposal_"):
        # Обработка кнопки "Создать КП"
        message_id = query.data.replace("lead_proposal_", "")
        message_data = context.user_data.get(f"lead_message_{message_id}")
        
        if not message_data:
            await query.answer("❌ Данные сообщения не найдены", show_alert=True)
            return
        
        try:
            # Показываем typing индикатор
            chat_id = query.message.chat.id
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            
            await query.answer("⏳ Генерирую коммерческое предложение...")
            
            user_message = message_data.get("user_message", "")
            user = query.from_user
            user_id = user.id
            user_name = user.first_name or user.username or "Клиент"
            
            # Получаем историю беседы для контекста
            conversation_history = None
            try:
                from telegram_bot.services.memory_service import get_recent_history
                conversation_history = get_recent_history(user_id, limit=20)
                if conversation_history:
                    log.info(f"📝 Использую историю беседы ({len(conversation_history)} символов) для генерации КП")
                else:
                    log.info("📝 История беседы пуста, используем только текущий запрос")
            except Exception as e:
                log.warning(f"⚠️ Не удалось получить историю беседы: {e}")
            
            # Импортируем функцию генерации КП
            try:
                from services.agents.lead_processor import generate_proposal
                
                # Продолжаем показывать typing во время генерации
                import asyncio
                async def keep_typing():
                    while True:
                        await asyncio.sleep(3)
                        try:
                            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                        except Exception:
                            break
                
                typing_task = asyncio.create_task(keep_typing())
                
                # Генерируем КП
                lead_contact = {
                    "name": user_name,
                    "email": "",
                    "phone": ""
                }
                
                try:
                    proposal = await generate_proposal(
                        lead_request=user_message,
                        lead_contact=lead_contact,
                        rag_results=None,
                        conversation_history=conversation_history
                    )
                finally:
                    # Останавливаем typing индикатор
                    typing_task.cancel()
                    try:
                        await typing_task
                    except asyncio.CancelledError:
                        pass
                
                if proposal:
                    # Отправляем КП пользователю
                    proposal_text = (
                        f"📝 *Коммерческое предложение*\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"{proposal}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"💡 *Следующие шаги:*\n"
                        f"• Проверьте и при необходимости отредактируйте КП\n"
                        f"• Отправьте клиенту по email или через другой канал связи"
                    )
                    
                    # Убираем кнопки из исходного сообщения
                    try:
                        await query.edit_message_reply_markup(reply_markup=None)
                    except Exception:
                        pass  # Игнорируем ошибку, если сообщение уже было изменено
                    
                    # Отправляем КП
                    keyboard = [
                        [InlineKeyboardButton("✅ КП готово", callback_data=f"lead_proposal_done_{message_id}")],
                        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.message.reply_text(
                        proposal_text,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                    
                    # Сохраняем сгенерированное КП в context
                    context.user_data[f"lead_proposal_{message_id}"] = proposal
                    
                    log.info(f"✅ КП сгенерировано для сообщения {message_id}")
                else:
                    await query.answer("❌ Не удалось сгенерировать КП", show_alert=True)
                    
            except ImportError:
                await query.answer("❌ Модуль генерации КП недоступен", show_alert=True)
                log.error("❌ Модуль lead_processor недоступен")
            except Exception as e:
                log.error(f"❌ Ошибка генерации КП: {e}")
                import traceback
                log.error(traceback.format_exc())
                await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
                
        except Exception as e:
            log.error(f"❌ Ошибка обработки создания КП: {e}")
            import traceback
            log.error(traceback.format_exc())
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
    
    elif query.data.startswith("lead_proposal_done_"):
        # Обработка кнопки "КП готово"
        message_id = query.data.replace("lead_proposal_done_", "")
        await query.answer("✅ КП сохранено", show_alert=False)
        await query.edit_message_reply_markup(reply_markup=None)
        log.info(f"✅ КП помечено как готовое (message_id: {message_id})")
    
    elif query.data.startswith("lead_task_week_"):
        # Обработка кнопки "Создать задачу week"
        message_id = query.data.replace("lead_task_week_", "")
        message_data = context.user_data.get(f"lead_message_{message_id}")
        
        if not message_data:
            await query.answer("❌ Данные сообщения не найдены", show_alert=True)
            return
        
        try:
            # Показываем typing индикатор
            chat_id = query.message.chat.id
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            
            from services.helpers.weeek_helper import get_projects
            
            await query.answer("⏳ Загружаю проекты...")
            
            # Получаем список проектов
            projects = await get_projects()
            
            if not projects:
                await query.answer("❌ Проекты не найдены. Создайте проект сначала.", show_alert=True)
                return
            
            # Формируем клавиатуру с проектами
            keyboard = []
            # Группируем кнопки по 2 в ряд
            for i in range(0, min(len(projects), 10), 2):
                row = []
                row.append(InlineKeyboardButton(
                    f"📁 {projects[i].get('title', 'Без названия')[:20]}",
                    callback_data=f"lead_task_week_select_{message_id}_{projects[i].get('id')}"
                ))
                if i + 1 < len(projects) and i + 1 < 10:
                    row.append(InlineKeyboardButton(
                        f"📁 {projects[i+1].get('title', 'Без названия')[:20]}",
                        callback_data=f"lead_task_week_select_{message_id}_{projects[i+1].get('id')}"
                    ))
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="back_to_menu")])
            
            user_message = message_data.get("user_message", "")
            text = (
                f"📋 *Создание задачи в WEEEK*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"*Сообщение:* {user_message[:100]}{'...' if len(user_message) > 100 else ''}\n\n"
                f"*Выберите проект для создания задачи:*"
            )
            
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            log.error(f"❌ Ошибка получения проектов: {e}")
            import traceback
            log.error(traceback.format_exc())
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
    
    elif query.data.startswith("lead_task_week_select_"):
        # Обработка выбора проекта для создания задачи
        # Формат: lead_task_week_select_{message_id}_{project_id}
        parts = query.data.replace("lead_task_week_select_", "").split("_", 1)
        if len(parts) != 2:
            await query.answer("❌ Ошибка формата данных", show_alert=True)
            return
        
        message_id = parts[0]
        project_id = parts[1]
        
        message_data = context.user_data.get(f"lead_message_{message_id}")
        
        if not message_data:
            await query.answer("❌ Данные сообщения не найдены", show_alert=True)
            return
        
        try:
            # Показываем typing индикатор
            chat_id = query.message.chat.id
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            
            from services.helpers.weeek_helper import create_task, get_project
            
            await query.answer("⏳ Создаю задачу...")
            
            # Получаем информацию о проекте
            project = await get_project(project_id)
            project_title = project.get("title", f"Проект {project_id}") if project else f"Проект {project_id}"
            
            # Используем сообщение пользователя как название задачи
            user_message = message_data.get("user_message", "Задача из бота")
            task_title = user_message[:100]  # Ограничиваем длину
            
            # Создаем задачу
            task = await create_task(
                project_id=project_id,
                title=task_title,
                description=f"Создано из сообщения в Telegram боте\n\nСообщение: {user_message}"
            )
            
            if task:
                task_id = task.get("id", "")
                
                # Убираем кнопки из исходного сообщения
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass
                
                success_text = (
                    f"✅ *Задача создана в WEEEK!*\n\n"
                    f"📁 *Проект:* {project_title}\n"
                    f"📝 *Задача:* {task_title}\n"
                    f"🆔 *ID задачи:* `{task_id}`"
                )
                
                keyboard = [
                    [InlineKeyboardButton("✅ Готово", callback_data=f"lead_task_week_done_{message_id}")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
                ]
                
                await query.message.reply_text(
                    success_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
                log.info(f"✅ Задача создана в WEEEK: {task_title} в проекте {project_id}")
            else:
                await query.answer("❌ Не удалось создать задачу", show_alert=True)
                
        except Exception as e:
            log.error(f"❌ Ошибка создания задачи: {e}")
            import traceback
            log.error(traceback.format_exc())
            await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
    
    elif query.data.startswith("lead_task_week_done_"):
        # Обработка кнопки "Готово" после создания задачи
        message_id = query.data.replace("lead_task_week_done_", "")
        await query.answer("✅ Задача создана", show_alert=False)
        await query.edit_message_reply_markup(reply_markup=None)
        log.info(f"✅ Задача помечена как созданная (message_id: {message_id})")