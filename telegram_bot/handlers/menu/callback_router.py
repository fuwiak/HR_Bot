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
            [InlineKeyboardButton("🔍 Поиск в базе знаний", callback_data="rag_search_menu")],
            [InlineKeyboardButton("📚 Список документов", callback_data="rag_docs")],
            [InlineKeyboardButton("📊 Статистика RAG", callback_data="rag_stats")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        message_text = (
            "📚 *База знаний*\n\n"
            "🔍 *Поиск* - семантический поиск по методикам, кейсам, шаблонам\n"
            "📚 *Документы* - список всех документов в базе\n"
            "📊 *Статистика* - информация о базе знаний"
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
            [InlineKeyboardButton("📋 Мои проекты", callback_data="weeek_list_projects")],
            [InlineKeyboardButton("➕ Создать задачу", callback_data="weeek_create_task_menu")],
            [InlineKeyboardButton("📊 Статус проектов", callback_data="status")],
            [InlineKeyboardButton("📝 Суммаризация", callback_data="summary_menu")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "📋 *Управление проектами (WEEEK)*\n\n"
            "📋 *Мои проекты* - список всех проектов\n"
            "➕ *Создать задачу* - добавить задачу в проект\n"
            "📊 *Статус* - задачи с ближайшими дедлайнами\n"
            "📝 *Суммаризация* - краткая сводка по проекту",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Подменю "Инструменты"
    elif query.data == "menu_tools":
        keyboard = [
            [InlineKeyboardButton("📝 Сгенерировать КП", callback_data="generate_proposal")],
            [InlineKeyboardButton("📄 Быстрая суммаризация", callback_data="quick_summary_menu")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "🛠 *Инструменты*\n\n"
            "📝 *Генерация КП* - создать коммерческое предложение\n"
            "📄 *Суммаризация* - краткая сводка текста",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Подменю "Помощь"
    elif query.data == "menu_help":
        keyboard = [
            [InlineKeyboardButton("📖 Команды бота", callback_data="help_commands")],
            [InlineKeyboardButton("💡 Примеры использования", callback_data="help_examples")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "❓ *Помощь*\n\n"
            "📖 *Команды* - список всех команд\n"
            "💡 *Примеры* - примеры использования",
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
        await query.edit_message_text(
            "✅ Проект выбран!\n\n"
            "Теперь отправьте название задачи (текстовым сообщением).\n\n"
            "Например: `Согласовать КП с клиентом`",
            parse_mode='Markdown'
        )
        context.user_data["waiting_for_task_name"] = True
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
            "📖 *Команды бота:*\n\n"
            "**Основные:**\n"
            "`/start` - главное меню\n"
            "`/menu` - главное меню\n\n"
            "**База знаний (RAG):**\n"
            "`/rag_search [запрос]` - поиск в базе знаний\n"
            "`/rag_stats` - статистика базы\n"
            "`/rag_docs` - список документов\n\n"
            "**WEEEK проекты:**\n"
            "`/weeek_info` - workspace info + список проектов с ID\n"
            "`/weeek_projects` - список проектов\n"
            "`/weeek_create_project [название]` - создать проект\n"
            "`/weeek_tasks [id] [фильтры]` - задачи проекта\n"
            "   Фильтры: all, completed, active, high, low\n"
            "`/weeek_task [проект] | [задача]` - создать задачу\n"
            "`/weeek_update` - обновить задачу (интерактивно)\n"
            "`/status` - статус проектов\n\n"
            "**Яндекс.Диск:**\n"
            "`/yadisk_list [путь]` - список файлов\n"
            "`/yadisk_search [запрос]` - поиск файлов\n"
            "`/yadisk_recent` - последние файлы\n\n"
            "**Email:**\n"
            "`/email_check` - проверить новые письма\n"
            "`/email_draft [текст]` - черновик ответа\n\n"
            "**Генерация:**\n"
            "`/demo_proposal [запрос]` - КП\n"
            "`/hypothesis [описание]` - гипотезы\n"
            "`/report [проект]` - отчет по проекту\n"
            "`/summary [проект]` - суммаризация проекта\n"
            "`/report [проект]` - отчёт\n"
            "`/summary [проект]` - суммаризация\n\n"
            "**Загрузка документов:**\n"
            "`/upload` - инструкция по загрузке\n"
            "Отправьте PDF/Word/Excel файл для индексации",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    elif query.data == "help_examples":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_help")]]
        await query.edit_message_text(
            "💡 *Примеры использования:*\n\n"
            "🔍 *Поиск:*\n"
            "`/rag_search подбор персонала`\n"
            "`/rag_search автоматизация HR`\n\n"
            "📝 *Генерация КП:*\n"
            "`/demo_proposal нужна помощь с подбором HR-менеджера`\n\n"
            "📋 *Проекты:*\n"
            "`/status` - список проектов\n"
            "`/summary Проект X` - сводка по проекту",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Суммаризация
    elif query.data == "summary_menu":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
        await query.edit_message_text(
            "📝 *Суммаризация проекта*\n\n"
            "Используйте команду:\n"
            "`/summary [название проекта]`\n\n"
            "Например:\n"
            "`/summary Подбор HR-менеджера`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    elif query.data == "quick_summary_menu":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_tools")]]
        await query.edit_message_text(
            "📄 *Быстрая суммаризация*\n\n"
            "Отправьте текст для суммаризации, и я создам краткую сводку.",
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
            "Используйте команду:\n"
            "`/rag_search [ваш запрос]`\n\n"
            "Например:\n"
            "`/rag_search подбор персонала`\n"
            "`/rag_search автоматизация HR процессов`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "generate_proposal":
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_tools")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "📝 *Генерация коммерческого предложения*\n\n"
            "Используйте команду:\n"
            "`/demo_proposal [запрос клиента]`\n\n"
            "Например:\n"
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
                text = f"📊 *Статистика RAG базы знаний*\n\n"
                text += f"Коллекция: `{stats.get('collection_name', 'N/A')}`\n"
                text += f"Существует: {'✅' if stats.get('exists') else '❌'}\n"
                if stats.get('exists'):
                    text += f"Документов: {stats.get('points_count', 0)}\n"
                    text += f"Размерность векторов: {stats.get('vector_size', 'N/A')}\n"
            
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
                text = f"📚 *Документы в базе знаний* (показано: {len(docs)})\n\n"
                for i, doc in enumerate(docs[:10], 1):
                    title = doc.get("title", "Без названия")
                    category = doc.get("category", "Неизвестно")
                    text += f"*{i}. {title}*\n"
                    text += f"   Категория: {category}\n\n"
                if len(docs) > 10:
                    text += f"... и еще {len(docs) - 10} документов"
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
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "📋 *Статус проектов*\n\n"
            "Используйте команду:\n"
            "`/status`\n\n"
            "Для суммаризации проекта:\n"
            "`/summary [название проекта]`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "chat":
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
        await query.edit_message_text(
            "💬 *Чат с AI*\n\n"
            "Теперь вы можете писать сообщения для общения с AI-помощником.\n\n"
            "Ассистент использует базу знаний для формирования ответов.",
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
