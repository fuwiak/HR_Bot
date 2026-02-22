"""
Rag команды
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from telegram_bot.nlp.text_utils import remove_markdown
import logging
import asyncio

log = logging.getLogger(__name__)

async def rag_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rag_search - поиск в RAG базе знаний с генерацией ответа"""
    query = " ".join(context.args) if context.args else "помощь"
    
    # Показываем индикатор "печатает..."
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    
    # Функция для периодического обновления typing
    async def keep_typing():
        """Периодически обновляет typing индикатор каждые 3 секунды"""
        while True:
            await asyncio.sleep(3)
            try:
                await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            except Exception:
                break
    
    try:
        await update.message.reply_text(f"🔍 Ищу в базе знаний: *{query}*...", parse_mode='Markdown')
        
        # AnythingLLM: при включённом флаге — один вызов к workspace API
        try:
            from services.integrations.anythingllm_client import (
                use_anythingllm_rag,
                is_configured,
                chat_with_workspace_env,
            )
            if use_anythingllm_rag() and is_configured():
                log.info("🔍 [AnythingLLM] /rag_search через workspace API")
                answer, sources_list = await chat_with_workspace_env(message=query, history=None)
                if answer:
                    answer_clean = remove_markdown(answer)
                    text_out = f"🔍 Результаты поиска: {query}\n\n💡 Ответ на основе документов:\n\n{answer_clean}"
                    if sources_list:
                        text_out += "\n\n📚 Источники:\n\n"
                        for i, s in enumerate(sources_list[:5], 1):
                            content = (s.get("content") or s.get("text") or str(s))[:200]
                            text_out += f"{i}. {content}...\n\n"
                    if len(text_out) > 4000:
                        parts = [text_out[i:i+4000] for i in range(0, len(text_out), 4000)]
                        for part in parts:
                            await update.message.reply_text(part)
                    else:
                        await update.message.reply_text(text_out)
                    return
        except Exception as e:
            log.warning("⚠️ [AnythingLLM] /rag_search ошибка: %s, fallback на Qdrant", e)
        
        from services.rag.qdrant_helper import get_qdrant_client, generate_embedding_async
        from services.helpers.llm_helper import generate_with_fallback
        
        # Обновляем индикатор перед получением клиента
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        
        client = get_qdrant_client()
        if not client:
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("❌ Qdrant недоступен", reply_markup=reply_markup)
            return
        
        # Обновляем индикатор перед генерацией эмбеддинга (может занять время)
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        
        # Создаем задачу для периодического обновления typing во время генерации эмбеддинга
        typing_task = asyncio.create_task(keep_typing())
        
        try:
            # Генерируем эмбеддинг для запроса
            query_embedding = await generate_embedding_async(query)
        finally:
            # Останавливаем задачу обновления typing
            if typing_task:
                typing_task.cancel()
                try:
                    await typing_task
                except asyncio.CancelledError:
                    pass
        
        if not query_embedding:
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("❌ Ошибка создания эмбеддинга", reply_markup=reply_markup)
            return
        
        # Обновляем индикатор перед поиском в Qdrant
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        
        # Ищем в Qdrant с обработкой таймаутов
        collection_name = "hr2137_bot_knowledge_base"
        log.info(f"🔍 [RAG] Поиск в коллекции '{collection_name}' для команды /rag_search: '{query}'")
        
        # Создаем задачу для периодического обновления typing во время поиска
        typing_task = asyncio.create_task(keep_typing())
        
        try:
            search_results = client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=5
            )
            log.info(f"✅ [RAG] Найдено {len(search_results.points) if search_results.points else 0} результатов в коллекции '{collection_name}'")
        except Exception as search_error:
            # Останавливаем задачу обновления typing при ошибке
            if typing_task:
                typing_task.cancel()
                try:
                    await typing_task
                except asyncio.CancelledError:
                    pass
            
            error_str = str(search_error).lower()
            if "timeout" in error_str or "timed out" in error_str:
                log.error(f"❌ [RAG] Таймаут при поиске в Qdrant: {search_error}")
                keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"⏱️ *Таймаут при поиске*\n\n"
                    f"Поиск в базе знаний занял слишком много времени.\n"
                    f"Попробуйте позже или упростите запрос.",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return
            else:
                log.error(f"❌ [RAG] Ошибка поиска в Qdrant: {search_error}")
                keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"❌ *Ошибка поиска*\n\n"
                    f"Не удалось выполнить поиск в базе знаний.\n"
                    f"Ошибка: {str(search_error)[:200]}",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return
        finally:
            # Останавливаем задачу обновления typing после поиска
            if typing_task:
                typing_task.cancel()
                try:
                    await typing_task
                except asyncio.CancelledError:
                    pass
        
        if not search_results.points:
            await update.message.reply_text(f"❌ По запросу '{query}' ничего не найдено в базе знаний.")
            return
        
        # Собираем результаты и источники
        results = []
        sources = {}
        
        for point in search_results.points:
            payload = point.payload if hasattr(point, 'payload') else {}
            score = point.score if hasattr(point, 'score') else 0.0
            
            # Извлекаем информацию о документе
            file_name = payload.get("file_name", "Документ")
            file_path = payload.get("file_path", "")
            text = payload.get("text", "")
            source = payload.get("source", "")
            
            if text:  # Только если есть текст
                results.append({
                    "file_name": file_name,
                    "text": text,
                    "file_path": file_path,
                    "source": source,
                    "score": score
                })
                
                # Собираем уникальные источники
                if file_name and file_name not in sources:
                    sources[file_name] = file_path
        
        if not results:
            await update.message.reply_text(f"❌ Найдены документы, но без текстового содержимого.")
            return
        
        # Формируем контекст для LLM
        llm_context = "\n\n".join([
            f"Источник: {r['file_name']}\n{r['text'][:500]}"
            for r in results[:3]  # Берем топ-3 для контекста
        ])
        
        # Обновляем индикатор перед генерацией ответа (может занять время)
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        
        # Создаем задачу для периодического обновления typing во время генерации ответа
        typing_task = asyncio.create_task(keep_typing())
        
        # Генерируем ответ через LLM
        prompt = f"""На основе следующих документов из базы знаний ответь на вопрос пользователя.

Вопрос: {query}

Документы:
{llm_context}

Ответь подробно и структурированно, ссылаясь на источники. Если информации недостаточно, укажи это.

ВАЖНО: Не используй Markdown форматирование (**, ###, __ и т.д.). Пиши обычным текстом."""
        
        try:
            answer = await generate_with_fallback(
                messages=[{"role": "user", "content": prompt}],
                use_system_message=True,
                system_content="Ты AI-ассистент HR консультанта. Отвечай профессионально и по делу на основе предоставленных документов.",
                max_tokens=1000,
                temperature=0.7
            )
        finally:
            # Останавливаем задачу обновления typing
            if typing_task:
                typing_task.cancel()
                try:
                    await typing_task
                except asyncio.CancelledError:
                    pass
        
        # Убираем Markdown из ответа
        if answer:
            answer_clean = remove_markdown(answer)
        else:
            answer_clean = "Не удалось сгенерировать ответ. Проверьте доступность LLM."
        
        # Формируем ответ пользователю
        text = f"🔍 Результаты поиска: {query}\n\n"
        
        # Ответ на основе документов
        if answer_clean:
            text += f"💡 Ответ на основе документов:\n\n"
            text += f"{answer_clean}\n\n"
        
        # Источники
        if sources:
            text += f"📚 Источники ({len(sources)}):\n\n"
            for i, (name, path) in enumerate(sources.items(), 1):
                text += f"{i}. 📄 {name}\n"
                if path:
                    text += f"   {path}\n"
                text += "\n"
        
        # Релевантные фрагменты
        text += f"\n📋 Релевантные фрагменты:\n\n"
        for i, r in enumerate(results[:3], 1):
            text += f"{i}. {r['file_name']} (релевантность: {r['score']:.2f})\n"
            snippet = r['text'][:200] + "..." if len(r['text']) > 200 else r['text']
            text += f"   {snippet}\n\n"
        
        # Если сообщение слишком длинное, разбиваем на части
        max_length = 4000
        if len(text) > max_length:
            # Разбиваем на части
            parts = []
            current_part = ""
            
            lines = text.split('\n')
            for line in lines:
                if len(current_part) + len(line) + 1 > max_length:
                    parts.append(current_part)
                    current_part = ""
                current_part += line + "\n"
            
            if current_part:
                parts.append(current_part)
            
            # Отправляем все части
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(text)
        
    except Exception as e:
        log.error(f"❌ Ошибка поиска в RAG: {e}")
        import traceback
        log.error(traceback.format_exc())
        error_str = str(e).lower()
        
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if "timeout" in error_str or "timed out" in error_str:
            error_message = (
                f"⏱️ *Таймаут при поиске*\n\n"
                f"Поиск в базе знаний занял слишком много времени.\n"
                f"Возможные причины:\n"
                f"• Qdrant сервер перегружен\n"
                f"• Проблемы с сетью\n"
                f"• Слишком сложный запрос\n\n"
                f"Попробуйте позже или упростите запрос."
            )
        elif "connect" in error_str or "connection" in error_str:
            error_message = (
                f"🔌 *Ошибка подключения*\n\n"
                f"Не удалось подключиться к базе знаний.\n"
                f"Проверьте доступность Qdrant сервера."
            )
        else:
            error_message = f"❌ *Ошибка поиска*\n\n{str(e)[:300]}"
        
        await update.message.reply_text(error_message, parse_mode='Markdown', reply_markup=reply_markup)

async def rag_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rag_stats - статистика RAG базы знаний"""
    try:
        from services.rag.qdrant_helper import get_collection_stats
        stats = await get_collection_stats()
        
        if "error" in stats:
            await update.message.reply_text(f"❌ Ошибка: {stats['error']}")
            return
        
        text = f"📊 *Статистика RAG базы знаний*\n\n"
        text += f"Коллекция: `{stats.get('collection_name', 'N/A')}`\n"
        text += f"Существует: {'✅' if stats.get('exists') else '❌'}\n"
        
        if stats.get('exists'):
            text += f"Документов: {stats.get('points_count', 0)}\n"
            text += f"Размерность векторов: {stats.get('vector_size', 'N/A')}\n"
            text += f"Метрика расстояния: {stats.get('distance', 'N/A')}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        log.error(f"❌ Ошибка получения статистики: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def rag_docs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rag_docs - список документов в базе знаний"""
    limit = int(context.args[0]) if context.args and context.args[0].isdigit() else 20
    
    try:
        from services.rag.qdrant_helper import list_documents
        docs = await list_documents(limit=limit)
        
        if docs:
            text = f"📚 Документы в базе знаний (показано: {len(docs)})\n\n"
            
            for i, doc in enumerate(docs[:limit], 1):
                title = doc.get("title", "Без названия")
                category = doc.get("category", "Неизвестно")
                text += f"{i}. {title}\n"
                text += f"   Категория: {category}\n\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("❌ В базе знаний нет документов.", reply_markup=reply_markup)
    except Exception as e:
        log.error(f"❌ Ошибка получения списка документов: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"❌ Ошибка: {str(e)}", reply_markup=reply_markup)

async def rag_upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rag_upload - инструкция по загрузке документов в RAG"""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    text = """📤 *Загрузка документов в базу знаний RAG*

*Как загрузить документ:*

1️⃣ Просто отправьте файл боту (перетащите файл в чат или используйте кнопку "📎")

2️⃣ Бот автоматически:
   • Извлечет текст из документа
   • Разобьет на части (чанки)
   • Создаст векторные представления
   • Загрузит в базу знаний

*Поддерживаемые форматы:*
• 📄 PDF (`.pdf`)
• 📝 Word (`.docx`, `.doc`)
• 📊 Excel (`.xlsx`, `.xls`)
• 📋 Текст (`.txt`)
• 📝 Markdown (`.md`)

*Ограничения:*
• Максимальный размер файла: 20 МБ
• Документ должен содержать текст

*После загрузки:*
Используйте `/rag_search [ваш запрос]` для поиска информации в загруженных документах.

*Примеры:*
• `/rag_search автоматизация HR`
• `/rag_search бизнес-анализ`

*Другие команды RAG:*
• `/rag_stats` — статистика базы знаний
• `/rag_docs` — список загруженных документов"""

    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
