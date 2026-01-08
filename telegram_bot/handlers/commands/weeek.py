"""
Weeek команды
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
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
        text = f"📊 *WORKSPACE INFO*\n\n"
        text += f"🆔 ID: `{workspace_id}`\n"
        text += f"📝 Название: {title}\n"
        text += f"👤 Персональный: {'Да' if is_personal else 'Нет'}\n\n"
        
        if projects:
            text += f"📋 *ПРОЕКТЫ* (всего: {len(projects)})\n\n"
            for i, project in enumerate(projects[:10], 1):
                project_title = project.get("title", "Без названия")
                project_id = project.get("id", "")
                color = project.get("color", "")
                is_private = project.get("isPrivate", False)
                
                text += f"{i}. *{project_title}*\n"
                text += f"   🆔 ID: `{project_id}`\n"
                if color:
                    text += f"   🎨 Цвет: {color}\n"
                if is_private:
                    text += f"   🔒 Приватный\n"
                text += "\n"
            
            if len(projects) > 10:
                text += f"_...и еще {len(projects) - 10} проектов_\n\n"
            
            text += f"💡 *Используйте:*\n"
            text += f"• `/weeek_tasks [ID]` - задачи проекта\n"
            text += f"• `/weeek_task [название] | [задача]` - создать задачу"
        else:
            text += "❌ Проектов не найдено\n\n"
            text += "Создайте проект:\n"
            text += "`/weeek_create_project [название]`"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка получения workspace info: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

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
        
        if task:
            await update.message.reply_text(
                f"✅ *Задача создана в WEEEK!*\n\n"
                f"Проект: {project_name}\n"
                f"Задача: {task_name}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Не удалось создать задачу в WEEEK")
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
            text = f"📋 *Проекты в WEEEK* (всего: {len(projects)})\n\n"
            for i, project in enumerate(projects[:20], 1):
                title = project.get("title", "Без названия")
                project_id = project.get("id", "")
                color = project.get("color", "")
                text += f"{i}. *{title}*\n"
                text += f"   ID: `{project_id}`"
                if color:
                    text += f" • {color}"
                text += "\n\n"

            await update.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ Проектов не найдено.\n\n"
                "Проверьте WEEEK_TOKEN в настройках."
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
        
        if project:
            project_id = project.get("id")
            await update.message.reply_text(
                f"✅ Проект создан в WEEEK!\n\n"
                f"📁 Название: {project_name}\n"
                f"🆔 ID: `{project_id}`\n\n"
                f"Теперь можете добавить задачи:\n"
                f"`/weeek_task {project_name} | Название задачи`\n"
                f"или через меню: `/weeek_update`",
                parse_mode='Markdown'
            )
            log.info(f"✅ Проект создан: {project_name} (ID: {project_id})")
        else:
            await update.message.reply_text("❌ Не удалось создать проект в WEEEK")
            
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
        
        # Показываем список проектов для выбора
        keyboard = []
        for project in projects[:15]:
            project_name = project.get("name", "Без названия")
            project_id = project.get("id", "")
            keyboard.append([
                InlineKeyboardButton(
                    f"📁 {project_name}",
                    callback_data=f"weeek_update_select_project_{project_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")])
        
        await update.message.reply_text(
            "🔄 *Обновление задачи*\n\n"
            "Шаг 1/3: Выберите проект с задачей:",
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
            
            await update.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                f"📋 *Проект: {project_title}*\n\n"
                "❌ Задач не найдено.",
                parse_mode='Markdown'
            )
            
    except ValueError:
        await update.message.reply_text("❌ Неверный ID проекта (должно быть число)")
    except Exception as e:
        log.error(f"❌ Ошибка получения задач: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
