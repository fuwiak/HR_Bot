"""
Tools команды
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.nlp.text_utils import remove_markdown
import logging

log = logging.getLogger(__name__)

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /summary - суммаризация проекта с использованием WEEEK и RAG"""
    project_name = " ".join(context.args) if context.args else "текущий"
    
    try:
        await update.message.reply_text(f"⏳ Суммаризирую проект '{project_name}'...")

        # 1. Получаем данные из WEEEK
        weeek_data = ""
        try:
            from services.helpers.weeek_helper import get_projects, get_tasks
            
            projects = await get_projects()
            target_project = None
            
            # Ищем проект по названию или ID
            if project_name.lower() != "текущий":
                # Сначала проверяем, не указан ли ID (число)
                try:
                    project_id_input = int(project_name.strip())
                    # Ищем по ID
                    for project in projects:
                        if project.get('id') == project_id_input:
                            target_project = project
                            log.info(f"✅ Найден проект по ID: {project_id_input} - {project.get('title')}")
                            break
                except ValueError:
                    # Не число, ищем по названию
                    project_name_lower = project_name.lower().strip()
                    
                    # 1. Сначала точное совпадение
                    for project in projects:
                        if project.get('title', '').lower().strip() == project_name_lower:
                            target_project = project
                            log.info(f"✅ Найден проект точным совпадением: {project.get('title')}")
                            break
                    
                    # 2. Если не нашли, ищем частичное совпадение (но только если название короткое)
                    if not target_project and len(project_name_lower) > 3:
                        for project in projects:
                            project_title_lower = project.get('title', '').lower()
                            # Проверяем, что название проекта начинается с запроса или запрос - это отдельное слово
                            if (project_title_lower.startswith(project_name_lower) or 
                                f" {project_name_lower} " in f" {project_title_lower} "):
                                target_project = project
                                log.info(f"✅ Найден проект частичным совпадением: {project.get('title')}")
                                break
            
            # Если не нашли, берем первый активный
            if not target_project and projects:
                target_project = [p for p in projects if not p.get('isArchived', False)][0] if projects else None
                if target_project:
                    log.info(f"⚠️ Проект '{project_name}' не найден, используется первый активный: {target_project.get('title')}")
            
            if target_project:
                project_id = target_project.get('id')
                project_title = target_project.get('title', 'Без названия')
                
                # Получаем задачи проекта
                tasks = await get_tasks(project_id=project_id, per_page=20)
                
                weeek_data = f"Проект: {project_title} (ID: {project_id})\n\n"
                
                if tasks and tasks.get('tasks'):
                    completed = [t for t in tasks['tasks'] if t.get('isCompleted', False)]
                    active = [t for t in tasks['tasks'] if not t.get('isCompleted', False)]
                    
                    weeek_data += f"Задач всего: {len(tasks['tasks'])}\n"
                    weeek_data += f"Активных: {len(active)}\n"
                    weeek_data += f"Завершенных: {len(completed)}\n\n"
                    
                    if active:
                        weeek_data += "Активные задачи:\n"
                        for task in active[:10]:
                            task_name = task.get('name') or task.get('title', 'Задача')
                            priority = task.get('priority', 0)
                            weeek_data += f"  • {task_name} (приоритет: {priority})\n"
                    
                    if completed:
                        weeek_data += "\nЗавершенные задачи:\n"
                        for task in completed[:5]:
                            task_name = task.get('name') or task.get('title', 'Задача')
                            weeek_data += f"  • {task_name}\n"
                
                log.info(f"✅ Получены данные из WEEEK для проекта {project_title}")
        except Exception as e:
            log.warning(f"⚠️ Ошибка получения данных WEEEK: {e}")
        
        # 2. Получаем релевантную информацию из RAG
        rag_context = ""
        try:
            from services.rag.qdrant_helper import get_qdrant_client, generate_embedding_async
            
            client = get_qdrant_client()
            if client:
                # Ищем по названию проекта
                search_query = f"{project_name} {target_project.get('title', '') if target_project else ''}"
                query_embedding = await generate_embedding_async(search_query)
                
                if query_embedding:
                    collection_name = "hr2137_bot_knowledge_base"
                    log.info(f"🔍 [RAG] Поиск в коллекции '{collection_name}' для команды /summary: '{search_query[:100]}'")
                    search_results = client.query_points(
                        collection_name=collection_name,
                        query=query_embedding,
                        limit=5
                    )
                    
                    if search_results.points:
                        log.info(f"✅ [RAG] Найдено {len(search_results.points)} результатов в коллекции '{collection_name}'")
                        rag_docs = []
                        for point in search_results.points:
                            payload = point.payload if hasattr(point, 'payload') else {}
                            file_name = payload.get("file_name", "Документ")
                            text_chunk = payload.get("text", "")
                            
                            if text_chunk:
                                rag_docs.append(f"📄 {file_name}: {text_chunk[:400]}")
                        
                        if rag_docs:
                            rag_context = "Релевантные документы из базы знаний:\n\n" + "\n\n".join(rag_docs) + "\n\n"
                            log.info(f"✅ [RAG] Использовано {len(rag_docs)} документов из коллекции '{collection_name}' для контекста")
                    else:
                        log.info(f"ℹ️ [RAG] Результаты не найдены в коллекции '{collection_name}' для запроса: '{search_query[:100]}'")
        except Exception as e:
            log.warning(f"⚠️ Ошибка RAG поиска: {e}")
        
        # 3. Генерируем суммаризацию через LLM
        from services.helpers.llm_helper import generate_with_fallback
        
        prompt = f"""Создай подробную суммаризацию проекта на основе следующих данных:

Название проекта: {project_name}

Данные из WEEEK:
{weeek_data if weeek_data else "Данные из WEEEK недоступны"}

Релевантные документы:
{rag_context if rag_context else "Релевантные документы не найдены"}

Создай структурированную суммаризацию, включающую:
1. Общее описание проекта
2. Текущий статус (активные задачи, прогресс)
3. Ключевые достижения
4. Следующие шаги
5. Рекомендации

ВАЖНО: Не используй Markdown форматирование (**, ###, __ и т.д.). Пиши обычным текстом с переносами строк."""
        
        summary = await generate_with_fallback(
            messages=[{"role": "user", "content": prompt}],
            use_system_message=True,
            system_content="Ты AI-ассистент HR консультанта. Создавай подробные и структурированные суммаризации проектов.",
            max_tokens=1500,
            temperature=0.7
        )
        
        if not summary:
            summary = "Не удалось создать суммаризацию. Проверьте доступность LLM и данных."

        # Очищаем summary от Markdown
        summary_clean = remove_markdown(summary)
        
        # Формируем сообщение без Markdown
        message_text = f"Суммаризация проекта '{project_name}':\n\n{summary_clean}"
        
        # Если сообщение слишком длинное, разбиваем на части
        max_length = 4000  # Лимит Telegram
        
        if len(message_text) > max_length:
            # Разбиваем на части
            parts = []
            header = f"Суммаризация проекта '{project_name}':\n\n"
            current_part = header
            
            # Пробуем разбить по разделам
            lines = summary_clean.split('\n')
            for line in lines:
                if len(current_part) + len(line) + 1 > max_length:
                    parts.append(current_part)
                    current_part = ""
                current_part += line + "\n"
            
            if current_part:
                parts.append(current_part)
            
            # Отправляем все части без Markdown
            for part in parts:
                await update.message.reply_text(part)
        else:
            # Отправляем без Markdown
            await update.message.reply_text(message_text)
    except Exception as e:
        log.error(f"❌ Ошибка суммаризации: {e}")
        import traceback
        log.error(traceback.format_exc())
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def demo_proposal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /demo_proposal - генерация КП для демонстрации"""
    request_text = " ".join(context.args) if context.args else ""
    
    if not request_text:
        await update.message.reply_text(
            "❌ Укажите запрос клиента.\n"
            "Использование: `/demo_proposal нужна помощь с подбором персонала`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from lead_processor import generate_proposal
        
        await update.message.reply_text("⏳ Генерирую коммерческое предложение...")
        
        proposal = await generate_proposal(request_text, lead_contact={})
        
        # Разбиваем длинное сообщение на части если нужно
        if len(proposal) > 4000:
            # Отправляем по частям
            parts = [proposal[i:i+4000] for i in range(0, len(proposal), 4000)]
            for part in parts:
                await update.message.reply_text(f"*Черновик КП:*\n\n{part}", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"*Черновик КП:*\n\n{proposal}", parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка генерации КП: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка генерации КП: {str(e)}")

async def hypothesis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /hypothesis - генерация гипотез для проекта"""
    project_context = " ".join(context.args) if context.args else ""
    
    if not project_context:
        await update.message.reply_text(
            "❌ Укажите контекст проекта.\n"
            "Использование: `/hypothesis [описание проекта/задачи]`\n\n"
            "Пример: `/hypothesis автоматизация HR процессов в IT компании`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from lead_processor import generate_hypothesis
        
        await update.message.reply_text("⏳ Генерирую гипотезы...")
        
        hypothesis = await generate_hypothesis(project_context)
        
        text = f"💡 *Гипотезы для проекта:*\n\n{hypothesis}"
        
        # Разбиваем длинное сообщение если нужно
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        log.error(f"❌ Ошибка генерации гипотез: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /report - генерация отчёта по проекту"""
    project_name = " ".join(context.args) if context.args else ""
    
    if not project_name:
        await update.message.reply_text(
            "❌ Укажите название проекта.\n"
            "Использование: `/report [название проекта]`\n\n"
            "Пример: `/report Подбор HR-менеджера`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from summary_helper import generate_project_report
        
        await update.message.reply_text(f"⏳ Генерирую отчёт по проекту '{project_name}'...")
        
        # Получаем информацию о проекте из WEEEK
        from services.helpers.weeek_helper import get_projects
        projects = await get_projects()
        project_data = None
        for project in projects:
            if project_name.lower() in project.get("title", "").lower():
                project_data = project
                break
        
        if not project_data:
            await update.message.reply_text(f"❌ Проект '{project_name}' не найден в WEEEK")
            return
        
        # Пример данных для отчета (в будущем можно получать из WEEEK)
        conversations = [{"role": "user", "content": f"Работа над проектом {project_name}"}]
        
        report = await generate_project_report(conversations, project_name=project_name)
        
        text = f"📊 *Отчёт по проекту '{project_name}':*\n\n{report}"
        
        # Разбиваем длинное сообщение если нужно
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        log.error(f"❌ Ошибка генерации отчёта: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def upload_document_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /upload - инструкция по загрузке документов"""
    await update.message.reply_text(
        "📤 *Загрузка документов в базу знаний*\n\n"
        "Отправьте мне документ в одном из форматов:\n"
        "• PDF (.pdf)\n"
        "• Word (.docx, .doc)\n"
        "• Excel (.xlsx, .xls)\n"
        "• Текст (.txt)\n\n"
        "Документ будет автоматически обработан и загружен в Qdrant Cloud.\n"
        "После загрузки вы сможете задавать вопросы по этому документу.\n\n"
        "💡 *Совет:* Дайте документу понятное имя файла для удобства поиска.",
        parse_mode='Markdown'
    )
