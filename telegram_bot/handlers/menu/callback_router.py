"""
Роутер для callback кнопок
"""
import sys
from pathlib import Path
from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
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

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
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
            [InlineKeyboardButton("📊 Статистика", callback_data="rag_stats")],
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
            "   о базе знаний"
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
            "`/rag_stats` — статистика\n"
            "`/rag_docs` — список документов\n\n"
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
            "`/summary [проект]` — суммаризация\n\n"
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
            "`/rag_search подбор персонала`\n"
            "`/rag_search автоматизация HR`\n\n"
            "📝 *Генерация КП:*\n"
            "`/demo_proposal нужна помощь с подбором HR-менеджера`\n\n"
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
            "Отправьте текст для суммаризации,\n"
            "и я создам краткую сводку.",
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
            "• `/rag_search подбор персонала`\n"
            "• `/rag_search автоматизация HR`",
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
            "Используйте команду:\n"
            "`/demo_proposal [запрос клиента]`\n\n"
            "💡 *Пример:*\n"
            "`/demo_proposal нужна помощь с подбором HR-менеджера`",
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
                    f"📚 *Документы в базе*\n"
                    f"Показано: {len(docs)}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                )
                for i, doc in enumerate(docs[:10], 1):
                    title = doc.get("title", "Без названия")
                    category = doc.get("category", "Неизвестно")
                    text += f"{i}. 📄 *{title}*\n"
                    text += f"   🏷 {category}\n\n"
                if len(docs) > 10:
                    text += f"_...и еще {len(docs) - 10} документов_"
            else:
                text = "❌ В базе знаний нет документов."
            
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
            log.error(f"❌ Ошибка получения списка документов: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
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
