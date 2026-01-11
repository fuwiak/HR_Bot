"""
Weeek команды
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram import Update
from telegram.ext import ContextTypes
import logging

log = logging.getLogger(__name__)

async def weeek_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weeek_info - информация о workspace и проектах"""
    try:
        from services.helpers.weeek_helper import get_workspace_info, get_projects
        
        await update.message.reply_text("⏳ Получаю информацию о workspace...")
        
        # Получаем workspace info
        workspace = await get_workspace_info()
        
        if not workspace:
            await update.message.reply_text("❌ Не удалось получить информацию о workspace")
            return
        
        workspace_id = workspace.get("id")
        title = workspace.get("title", "Без названия")
        is_personal = workspace.get("isPersonal", False)
        
        # Получаем список проектов
        projects = await get_projects()
        
        # Формируем сообщение
        text = (
            "📊 *WORKSPACE INFO*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{workspace_id}`\n"
            f"📝 Название: {title}\n"
            f"👤 Персональный: {'Да' if is_personal else 'Нет'}\n\n"
        )
        
        if projects:
            text += f"📋 *ПРОЕКТЫ* ({len(projects)})\n\n"
            for i, project in enumerate(projects[:10], 1):
                project_title = project.get("title", "Без названия")
                project_id = project.get("id", "")
                color = project.get("color", "")
                is_private = project.get("isPrivate", False)
                
                text += f"{i}. 📁 *{project_title}*\n"
                text += f"   🆔 `{project_id}`"
                if color:
                    text += f" | 🎨 {color}"
                if is_private:
                    text += f" | 🔒 Приватный"
                text += "\n\n"
            
            if len(projects) > 10:
                text += f"_...и еще {len(projects) - 10} проектов_\n\n"
            
            text += (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "💡 *Команды:*\n"
                "• `/weeek_tasks [ID]` — задачи\n"
                "• `/weeek_task [проект] | [задача]` — создать"
            )
        else:
            text += (
                "❌ Проектов не найдено\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Создайте проект:\n"
                "`/weeek_create_project [название]`"
            )
        
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        log.error(f"❌ Ошибка получения workspace info: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"❌ Ошибка: {str(e)}", reply_markup=reply_markup)

async def weeek_create_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weeek_task - создание задачи в Weeek"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Укажите название проекта и задачу.\n"
            "Использование: `/weeek_task [проект] | [задача]`\n\n"
            "Пример: `/weeek_task Подбор HR | Согласовать КП`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from services.helpers.weeek_helper import create_task, get_projects
        
        # Парсим аргументы (формат: проект | задача)
        full_text = " ".join(context.args)
        if "|" in full_text:
            parts = full_text.split("|", 1)
            project_name = parts[0].strip()
            task_name = parts[1].strip()
        else:
            await update.message.reply_text(
                "❌ Неправильный формат. Используйте: `/weeek_task [проект] | [задача]`",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_text(f"⏳ Создаю задачу '{task_name}' в проекте '{project_name}'...")
        
        # Получаем список проектов для поиска ID
        projects = await get_projects()
        project_id = None
        for project in projects:
            if project_name.lower() in project.get("title", "").lower():
                project_id = project.get("id")
                break
        
        if not project_id:
            await update.message.reply_text(
                f"❌ Проект '{project_name}' не найден в WEEEK.\n"
                f"Используйте `/weeek_projects` для просмотра списка проектов.",
                parse_mode='Markdown'
            )
            return
        
        task = await create_task(
            project_id=project_id,
            title=task_name,
            description=f"Создано через Telegram бот"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if task:
            await update.message.reply_text(
                f"✅ *Задача создана в WEEEK!*\n\n"
                f"Проект: {project_name}\n"
                f"Задача: {task_name}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Не удалось создать задачу в WEEEK", reply_markup=reply_markup)
    except Exception as e:
        log.error(f"❌ Ошибка создания задачи в Weeek: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def weeek_projects_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weeek_projects - список проектов в Weeek"""
    try:
        from services.helpers.weeek_helper import get_projects

        await update.message.reply_text("⏳ Получаю список проектов из WEEEK...")

        projects = await get_projects()

        if projects:
            text = (
                f"📋 *Проекты в WEEEK* ({len(projects)})\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            for i, project in enumerate(projects[:20], 1):
                title = project.get("title", "Без названия")
                project_id = project.get("id", "")
                color = project.get("color", "")
                text += f"{i}. *{title}*\n"
                text += f"   ID: `{project_id}`"
                if color:
                    text += f" • {color}"
                text += "\n\n"

            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "❌ Проектов не найдено.\n\n"
                "Проверьте WEEEK_TOKEN в настройках.",
                reply_markup=reply_markup
            )
    except Exception as e:
        log.error(f"❌ Ошибка получения проектов: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def weeek_create_project_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weeek_create_project - создание проекта в Weeek"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название проекта.\n"
            "Использование: `/weeek_create_project [название]`\n\n"
            "Примеры:\n"
            "`/weeek_create_project Новый проект HR`\n"
            "`/weeek_create_project Консалтинг 2025`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from services.helpers.weeek_helper import create_project
        
        project_name = " ".join(context.args)
        username = update.message.from_user.username or update.message.from_user.first_name
        
        await update.message.reply_text(f"⏳ Создаю проект: {project_name}")
        
        project = await create_project(
            name=project_name,
            description=f"Создано через Telegram бот пользователем @{username}"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if project:
            project_id = project.get("id")
            await update.message.reply_text(
                f"✅ Проект создан в WEEEK!\n\n"
                f"📁 Название: {project_name}\n"
                f"🆔 ID: `{project_id}`\n\n"
                f"Теперь можете добавить задачи:\n"
                f"`/weeek_task {project_name} | Название задачи`\n"
                f"или через меню: `/weeek_update`",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            log.info(f"✅ Проект создан: {project_name} (ID: {project_id})")
        else:
            await update.message.reply_text("❌ Не удалось создать проект в WEEEK", reply_markup=reply_markup)
            
    except Exception as e:
        log.error(f"❌ Ошибка создания проекта: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def weeek_update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weeek_update - обновление задачи в Weeek (интерактивное меню)"""
    try:
        from services.helpers.weeek_helper import get_projects
        
        await update.message.reply_text("⏳ Загружаю проекты...")
        
        projects = await get_projects()
        
        if not projects:
            await update.message.reply_text(
                "❌ Проектов не найдено.\n\n"
                "Сначала создайте проекты в WEEEK."
            )
            return
        
        # Показываем список проектов для выбора (группируем по 2)
        keyboard = []
        for i in range(0, len(projects[:15]), 2):
            row = []
            row.append(InlineKeyboardButton(
                f"📁 {projects[i].get('name', 'Без названия')[:20]}",
                callback_data=f"weeek_update_select_project_{projects[i].get('id')}"
            ))
            if i + 1 < len(projects[:15]):
                row.append(InlineKeyboardButton(
                    f"📁 {projects[i+1].get('name', 'Без названия')[:20]}",
                    callback_data=f"weeek_update_select_project_{projects[i+1].get('id')}"
                ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")])
        
        await update.message.reply_text(
            "🔄 *Обновление задачи*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 Шаг 1/3: Выберите проект:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def weeek_tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weeek_tasks - просмотр задач проекта с фильтрами"""
    if not context.args:
        await update.message.reply_text(
            "📋 *Просмотр задач проекта*\n\n"
            "**Использование:**\n"
            "`/weeek_tasks [project_id] [фильтры]`\n\n"
            "**Примеры:**\n"
            "`/weeek_tasks 1` - все активные\n"
            "`/weeek_tasks 1 all` - все задачи\n"
            "`/weeek_tasks 1 high` - высокий приоритет\n"
            "`/weeek_tasks 1 completed` - завершенные\n\n"
            "**Фильтры:**\n"
            "• `all` - все задачи\n"
            "• `completed` - завершенные\n"
            "• `active` - активные\n"
            "• `low/medium/high/hold` - по приоритету\n\n"
            "Узнайте ID проектов:\n"
            "`/weeek_info`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from services.helpers.weeek_helper import get_tasks, get_project
        
        project_id = int(context.args[0])
        
        # Парсим фильтры
        filters = " ".join(context.args[1:]).lower() if len(context.args) > 1 else ""
        
        completed = None
        priority = None
        show_all = False
        
        if "all" in filters:
            show_all = True
        elif "completed" in filters:
            completed = True
        elif "active" in filters:
            completed = False
        
        if "low" in filters:
            priority = 0
        elif "medium" in filters:
            priority = 1
        elif "high" in filters:
            priority = 2
        elif "hold" in filters:
            priority = 3
        
        await update.message.reply_text("⏳ Загружаю задачи...")
        
        # Получаем название проекта
        project = await get_project(project_id)
        project_title = project.get("title", f"Проект {project_id}") if project else f"Проект {project_id}"
        
        # Получаем задачи с фильтрами
        result = await get_tasks(
            project_id=project_id,
            completed=completed,
            priority=priority,
            all_tasks=show_all,
            per_page=50
        )
        
        if result["success"] and result["tasks"]:
            tasks = result["tasks"]
            has_more = result["hasMore"]
            
            # Формируем заголовок
            filter_text = []
            if show_all:
                filter_text.append("все")
            elif completed is True:
                filter_text.append("завершенные")
            elif completed is False:
                filter_text.append("активные")
            
            if priority is not None:
                priority_names = ["низкий", "средний", "высокий", "в ожидании"]
                filter_text.append(f"приоритет: {priority_names[priority]}")
            
            filter_str = f" ({', '.join(filter_text)})" if filter_text else ""
            
            text = f"📋 *Задачи: {project_title}*{filter_str}\n"
            text += f"Найдено: {len(tasks)}\n"
            if has_more:
                text += f"⚠️ Показаны первые {len(tasks)}, есть еще\n"
            text += "\n"
            
            # Группируем по приоритету
            priority_groups = {0: [], 1: [], 2: [], 3: [], None: []}
            for task in tasks:
                p = task.get("priority")
                priority_groups[p].append(task)
            
            priority_emoji = {0: "🟢", 1: "🟡", 2: "🔴", 3: "⏸", None: "⚪"}
            priority_names = {0: "Низкий", 1: "Средний", 2: "Высокий", 3: "В ожидании", None: "Без приоритета"}
            
            count = 0
            for p in [2, 3, 1, 0, None]:  # Высокий -> Hold -> Средний -> Низкий -> Нет
                if priority_groups[p]:
                    text += f"\n*{priority_emoji[p]} {priority_names[p]}:*\n"
                    for task in priority_groups[p]:
                        count += 1
                        title = task.get("title", "Без названия")
                        task_id = task.get("id", "")
                        is_completed = task.get("isCompleted", False)
                        status = "✅" if is_completed else "⭕"
                        
                        # Обрезаем длинные названия
                        if len(title) > 40:
                            title = title[:37] + "..."
                        
                        text += f"{count}. {status} {title}\n"
                        text += f"   ID: `{task_id}`\n"
            
            text += f"\n💡 Для редактирования: `/weeek_update`"
            
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"📋 *Проект: {project_title}*\n\n"
                "❌ Задач не найдено.",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
    except ValueError:
        await update.message.reply_text("❌ Неверный ID проекта (должно быть число)")
    except Exception as e:
        log.error(f"❌ Ошибка получения задач: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def show_weeek_projects(query: CallbackQuery):
    """Показать список проектов из WEEEK"""
    try:
        from services.helpers.weeek_helper import get_projects

        await query.edit_message_text("⏳ Загружаю проекты...")

        projects = await get_projects()

        if not projects:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
            await query.edit_message_text(
                "❌ *Проекты не найдены*\n\n"
                "Создайте проект через меню или командой:\n"
                "`/weeek_create_project [название]`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        keyboard = []
        # Группируем кнопки по 2 в ряд для компактности
        for i in range(0, len(projects[:10]), 2):
            row = []
            row.append(InlineKeyboardButton(
                f"📁 {projects[i].get('title', 'Без названия')[:20]}",
                callback_data=f"weeek_view_project_{projects[i].get('id')}"
            ))
            if i + 1 < len(projects[:10]):
                row.append(InlineKeyboardButton(
                    f"📁 {projects[i+1].get('title', 'Без названия')[:20]}",
                    callback_data=f"weeek_view_project_{projects[i+1].get('id')}"
                ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")])
        
        text = (
            f"📋 *Проекты* ({len(projects)})\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        for i, project in enumerate(projects[:10], 1):
            title = project.get("title", "Без названия")
            text += f"{i}. 📁 *{title}*\n"
        
        if len(projects) > 10:
            text += f"\n_...и еще {len(projects) - 10} проектов_"
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        log.error(f"❌ Ошибка получения проектов: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
        await query.edit_message_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def show_weeek_create_task_menu(query: CallbackQuery):
    """Показать меню создания задачи"""
    try:
        from services.helpers.weeek_helper import get_projects

        await query.edit_message_text("⏳ Загружаю проекты...")

        projects = await get_projects()

        if not projects:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
            await query.edit_message_text(
                "❌ Проектов не найдено.\n\n"
                "Сначала создайте проект в WEEEK.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        keyboard = []
        for project in projects[:15]:  # Показываем до 15 проектов
            project_title = project.get("title", "Без названия")
            project_id = project.get("id", "")
            keyboard.append([
                InlineKeyboardButton(
                    f"➕ {project_title}",
                    callback_data=f"weeek_select_project_{project_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")])
        
        await query.edit_message_text(
            "➕ *Создание задачи*\n\n"
            "Выберите проект, в который хотите добавить задачу:",
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

async def show_weeek_project_details(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Показать детали проекта"""
    try:
        project_id = query.data.replace("weeek_view_project_", "")
        
        from services.helpers.weeek_helper import get_project, get_tasks
        
        await query.edit_message_text("⏳ Загружаю информацию о проекте...")
        
        project = await get_project(project_id)
        
        if not project:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="weeek_list_projects")]]
            await query.edit_message_text(
                "❌ Не удалось загрузить информацию о проекте",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        project_title = project.get("title", project.get("name", "Без названия"))
        project_desc = project.get("description", "Описание отсутствует")
        
        # Получаем задачи проекта
        tasks_result = await get_tasks(project_id=project_id, completed=False, per_page=10)
        tasks_count = len(tasks_result.get("tasks", [])) if tasks_result.get("success") else 0
        
        text = f"📁 *{project_title}*\n\n"
        text += f"Описание: {project_desc}\n"
        text += f"Активных задач: {tasks_count}\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Создать задачу", callback_data=f"weeek_select_project_{project_id}")],
            [InlineKeyboardButton("🔙 К списку проектов", callback_data="weeek_list_projects")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="weeek_list_projects")]]
        await query.edit_message_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def show_weeek_tasks_for_update(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Показать список задач проекта для обновления"""
    try:
        project_id = query.data.replace("weeek_update_select_project_", "")
        
        from services.helpers.weeek_helper import get_tasks, get_project
        
        await query.edit_message_text("⏳ Загружаю задачи...")
        
        # Получаем информацию о проекте
        project = await get_project(project_id)
        project_title = project.get("title", f"Проект {project_id}") if project else f"Проект {project_id}"
        
        # Получаем задачи
        result = await get_tasks(project_id=project_id, completed=False, per_page=20)
        
        if not result["success"] or not result["tasks"]:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
            await query.edit_message_text(
                f"📋 *Проект: {project_title}*\n\n"
                "❌ Активных задач не найдено.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        tasks = result["tasks"]
        keyboard = []
        
        for task in tasks[:15]:
            task_title = task.get("title", task.get("name", "Без названия"))
            task_id = task.get("id", "")
            
            # Обрезаем длинные названия
            if len(task_title) > 40:
                task_title = task_title[:37] + "..."
            
            keyboard.append([
                InlineKeyboardButton(
                    f"📝 {task_title}",
                    callback_data=f"weeek_edit_task_{task_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")])
        
        text = f"📋 *Задачи: {project_title}*\n\n"
        text += f"Найдено активных задач: {len(tasks)}\n"
        text += "Выберите задачу для редактирования:"
        
        await query.edit_message_text(
            text,
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

async def show_weeek_task_edit_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню редактирования задачи"""
    try:
        task_id = query.data.replace("weeek_edit_task_", "")
        
        from services.helpers.weeek_helper import get_task
        
        await query.edit_message_text("⏳ Загружаю информацию о задаче...")
        
        task = await get_task(task_id)
        
        if not task:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
            await query.edit_message_text(
                "❌ Не удалось загрузить информацию о задаче",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        task_title = task.get("title", task.get("name", "Без названия"))
        is_completed = task.get("isCompleted", False)
        priority = task.get("priority")
        priority_names = {0: "Низкий", 1: "Средний", 2: "Высокий", 3: "В ожидании", None: "Не указан"}
        priority_name = priority_names.get(priority, "Не указан")
        task_date = task.get("day") or task.get("dueDate") or task.get("startDate") or "не указана"
        
        text = f"📝 *Задача: {task_title}*\n\n"
        text += f"Статус: {'✅ Завершена' if is_completed else '⭕ Активна'}\n"
        text += f"Приоритет: {priority_name}\n"
        text += f"📅 Дата: {task_date}\n"
        
        keyboard = [
            [InlineKeyboardButton("✏️ Редактировать название", callback_data=f"weeek_edit_title_{task_id}")],
            [InlineKeyboardButton("📅 Редактировать дату", callback_data=f"weeek_edit_date_{task_id}")],
            [InlineKeyboardButton("✅ Завершить" if not is_completed else "⭕ Возобновить", 
                                callback_data=f"weeek_complete_{task_id}")],
            [InlineKeyboardButton("🗑 Удалить", callback_data=f"weeek_delete_{task_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]
        ]
        
        await query.edit_message_text(
            text,
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

async def handle_weeek_edit_field(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик редактирования поля задачи"""
    await query.answer("⚠️ Функция редактирования полей в разработке")

async def handle_weeek_edit_title(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик редактирования названия задачи"""
    try:
        task_id = query.data.replace("weeek_edit_title_", "")
        context.user_data["editing_task_id"] = task_id
        context.user_data["editing_task_field"] = "title"
        context.user_data["waiting_for_task_edit"] = True
        
        from services.helpers.weeek_helper import get_task
        task = await get_task(task_id)
        current_title = task.get("title", task.get("name", "")) if task else ""
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"weeek_edit_task_{task_id}")]]
        await query.edit_message_text(
            f"✏️ *Редактирование названия задачи*\n\n"
            f"Текущее название: *{current_title}*\n\n"
            "📝 Отправьте новое название задачи текстовым сообщением.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}")

async def handle_weeek_edit_date(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик редактирования даты задачи"""
    try:
        task_id = query.data.replace("weeek_edit_date_", "")
        context.user_data["editing_task_id"] = task_id
        context.user_data["editing_task_field"] = "date"
        context.user_data["waiting_for_task_edit"] = True
        
        from services.helpers.weeek_helper import get_task
        from datetime import datetime, timedelta
        
        task = await get_task(task_id)
        current_date = task.get("day") or task.get("dueDate") or "не указана" if task else "не указана"
        
        # Кнопки для быстрого выбора даты
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        
        keyboard = [
            [InlineKeyboardButton("📅 Сегодня", callback_data=f"weeek_edit_date_select_{task_id}_{today.strftime('%d.%m.%Y')}")],
            [InlineKeyboardButton("📅 Завтра", callback_data=f"weeek_edit_date_select_{task_id}_{tomorrow.strftime('%d.%m.%Y')}")],
            [InlineKeyboardButton("📅 Через неделю", callback_data=f"weeek_edit_date_select_{task_id}_{next_week.strftime('%d.%m.%Y')}")],
            [InlineKeyboardButton("📝 Без даты", callback_data=f"weeek_edit_date_select_{task_id}_none")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"weeek_edit_task_{task_id}")]
        ]
        
        await query.edit_message_text(
            f"📅 *Редактирование даты задачи*\n\n"
            f"Текущая дата: *{current_date}*\n\n"
            "Выберите новую дату кнопкой или отправьте свою дату текстом (формат: ДД.ММ.ГГГГ или ДД.ММ)",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}")

async def handle_weeek_complete_task(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик завершения/возобновления задачи"""
    try:
        task_id = query.data.replace("weeek_complete_", "")
        
        from services.helpers.weeek_helper import get_task, complete_task, uncomplete_task
        
        task = await get_task(task_id)
        if not task:
            await query.answer("❌ Задача не найдена")
            return
        
        is_completed = task.get("isCompleted", False)
        
        if is_completed:
            success = await uncomplete_task(task_id)
            message = "⭕ Задача возобновлена"
        else:
            success = await complete_task(task_id)
            message = "✅ Задача завершена"
        
        if success:
            await query.answer(message)
            # Обновляем меню
            await show_weeek_task_edit_menu(query, context)
        else:
            await query.answer("❌ Ошибка обновления задачи")
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}")

async def handle_weeek_delete_task(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик удаления задачи"""
    try:
        task_id = query.data.replace("weeek_delete_", "")
        
        from services.helpers.weeek_helper import delete_task
        
        success = await delete_task(task_id)
        
        if success:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
            await query.edit_message_text(
                "✅ Задача удалена",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.answer("❌ Ошибка удаления задачи")
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}")

async def handle_weeek_set_priority(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик установки приоритета задачи"""
    await query.answer("⚠️ Функция установки приоритета в разработке")

async def handle_weeek_set_type(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик установки типа задачи"""
    await query.answer("⚠️ Функция установки типа в разработке")
