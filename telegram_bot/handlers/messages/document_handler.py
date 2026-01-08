"""
Обработчик документов
"""
import os
import asyncio
import logging
import tempfile
import uuid
from typing import Dict
from telegram import Update
from telegram.ext import ContextTypes
from qdrant_client.models import PointStruct

log = logging.getLogger(__name__)


async def extract_text_from_file(file_path: str, file_extension: str) -> str:
    """Извлечение текста из различных форматов файлов"""
    try:
        if file_extension == 'pdf':
            # PDF
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n\n"
            return text
        
        elif file_extension in ['docx', 'doc']:
            # Word документы
            try:
                import docx
                doc = docx.Document(file_path)
                text = "\n\n".join([para.text for para in doc.paragraphs])
                return text
            except ImportError:
                log.error("❌ python-docx не установлен. Установите: pip install python-docx")
                return ""
        
        elif file_extension in ['xlsx', 'xls']:
            # Excel
            import pandas as pd
            df = pd.read_excel(file_path, sheet_name=None)  # Читаем все листы
            text = ""
            for sheet_name, sheet_df in df.items():
                text += f"=== Лист: {sheet_name} ===\n\n"
                text += sheet_df.to_string(index=False) + "\n\n"
            return text
        
        elif file_extension == 'txt':
            # Текстовый файл
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        else:
            return ""
    
    except Exception as e:
        log.error(f"❌ Ошибка извлечения текста из {file_path}: {e}")
        return ""


async def upload_to_qdrant(text_content: str, file_name: str, user_id: int, username: str) -> dict:
    """Загрузка документа в Qdrant с чанкингом"""
    try:
        from services.rag.qdrant_loader import QdrantLoader
        from services.rag.qdrant_helper import generate_embedding_async
        
        # Создаем уникальный ID для документа
        doc_id = str(uuid.uuid4())
        
        # Инициализируем QdrantLoader
        loader = QdrantLoader()
        
        # Разбиваем текст на чанки
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            from text_splitter import RecursiveCharacterTextSplitter
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = text_splitter.split_text(text_content)
        log.info(f"📄 Создано {len(chunks)} чанков из документа {file_name}")
        
        # Создаем документы для загрузки
        documents = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 10:  # Пропускаем очень короткие чанки
                continue
            
            doc = {
                "id": f"{doc_id}_chunk_{i}",
                "text": chunk,
                "metadata": {
                    "source": file_name,
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "uploaded_by": username,
                    "user_id": user_id,
                    "category": "user_upload",
                    "title": file_name
                }
            }
            documents.append(doc)
        
        # Загружаем в Qdrant через loader
        # Обрабатываем чанки батчами для ускорения
        points = []
        batch_size = 10  # Обрабатываем по 10 чанков за раз
        
        for batch_start in range(0, len(documents), batch_size):
            batch_end = min(batch_start + batch_size, len(documents))
            batch_docs = documents[batch_start:batch_end]
            
            log.info(f"📊 Обрабатываю чанки {batch_start + 1}-{batch_end} из {len(documents)}")
            
            # Генерируем эмбеддинги для батча
            batch_tasks = []
            for doc in batch_docs:
                batch_tasks.append(generate_embedding_async(doc["text"]))
            
            # Ждем все эмбеддинги батча параллельно
            batch_embeddings = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Создаем точки для батча
            for doc, embedding in zip(batch_docs, batch_embeddings):
                if isinstance(embedding, Exception) or embedding is None:
                    log.warning(f"⚠️ Не удалось получить эмбеддинг для чанка {doc['id']}")
                    continue
                
                # Создаем числовой ID из hash строки
                point_id = abs(hash(doc["id"])) % (10 ** 10)
                
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": doc["text"],
                        "source": doc["metadata"]["source"],
                        "doc_id": doc["metadata"]["doc_id"],
                        "chunk_index": doc["metadata"]["chunk_index"],
                        "uploaded_by": doc["metadata"]["uploaded_by"],
                        "user_id": doc["metadata"]["user_id"],
                        "category": doc["metadata"]["category"],
                        "title": doc["metadata"]["title"],
                        "chunk_id": doc["id"]  # Сохраняем строковый ID в payload
                    }
                )
                points.append(point)
            
            log.info(f"✅ Обработано {len(batch_embeddings)} эмбеддингов в батче")
        
        # Загружаем в Qdrant
        if points:
            loader.client.upsert(
                collection_name=loader.collection_name,
                points=points
            )
            log.info(f"✅ Загружено {len(points)} чанков в Qdrant")
            
            return {
                "success": True,
                "chunks_count": len(points),
                "doc_id": doc_id
            }
        else:
            return {
                "success": False,
                "error": "Не удалось создать эмбеддинги для документа"
            }
    
    except Exception as e:
        log.error(f"❌ Ошибка загрузки в Qdrant: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки документов через Telegram"""
    try:
        document = update.message.document
        user_id = update.message.from_user.id
        username = update.message.from_user.username or "unknown"
        
        # Проверяем размер файла (макс 20MB)
        if document.file_size > 20 * 1024 * 1024:
            await update.message.reply_text(
                "❌ Файл слишком большой. Максимальный размер: 20 МБ"
            )
            return
        
        file_name = document.file_name
        file_extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
        
        # Проверяем формат файла
        supported_formats = ['pdf', 'docx', 'doc', 'xlsx', 'xls', 'txt']
        if file_extension not in supported_formats:
            await update.message.reply_text(
                f"❌ Формат `.{file_extension}` не поддерживается.\n\n"
                f"Поддерживаемые форматы: {', '.join(supported_formats)}",
                parse_mode='Markdown'
            )
            return
        
        log.info(f"📤 Получен документ от пользователя {username} (ID: {user_id}): {file_name}")
        
        # Отправляем статус (без Markdown для избежания ошибок с названиями файлов)
        status_msg = await update.message.reply_text(
            f"⏳ Загружаю документ: {file_name}\n"
            f"Размер: {document.file_size / 1024:.1f} КБ"
        )
        
        # Скачиваем файл
        file = await context.bot.get_file(document.file_id)
        
        # Создаем временную директорию если не существует
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file_name)
        
        await file.download_to_drive(file_path)
        log.info(f"✅ Файл скачан: {file_path}")
        
        # Обновляем статус
        await status_msg.edit_text(
            f"⏳ Обрабатываю документ: {file_name}\n"
            f"Извлекаю текст и создаю чанки..."
        )
        
        # Обрабатываем документ
        text_content = await extract_text_from_file(file_path, file_extension)
        
        if not text_content or len(text_content.strip()) < 50:
            await status_msg.edit_text(
                f"❌ Не удалось извлечь текст из документа `{file_name}`.\n"
                f"Проверьте, что документ содержит текст.",
                parse_mode='Markdown'
            )
            # Удаляем временный файл
            try:
                os.remove(file_path)
                os.rmdir(temp_dir)
            except:
                pass
            return
        
        log.info(f"✅ Извлечено {len(text_content)} символов из {file_name}")
        
        # Загружаем в Qdrant
        await status_msg.edit_text(
            f"⏳ Загружаю в базу знаний...\n"
            f"Индексирую чанки в Qdrant..."
        )
        
        result = await upload_to_qdrant(
            text_content=text_content,
            file_name=file_name,
            user_id=user_id,
            username=username
        )
        
        # Удаляем временный файл
        try:
            os.remove(file_path)
            os.rmdir(temp_dir)
        except Exception as e:
            log.warning(f"⚠️ Не удалось удалить временный файл: {e}")
        
        if result['success']:
            await status_msg.edit_text(
                f"✅ Документ загружен в базу знаний!\n\n"
                f"📄 Файл: {file_name}\n"
                f"📊 Создано чанков: {result['chunks_count']}\n"
                f"🆔 ID документа: {result['doc_id']}\n\n"
                f"Теперь вы можете задавать вопросы по этому документу:\n"
                f"• Просто напишите вопрос в чате\n"
                f"• Или используйте /rag_search [запрос]"
            )
            log.info(f"✅ Документ {file_name} успешно загружен (ID: {result['doc_id']})")
        else:
            await status_msg.edit_text(
                f"❌ Ошибка загрузки документа:\n{result['error']}"
            )
            log.error(f"❌ Ошибка загрузки {file_name}: {result['error']}")
            
    except Exception as e:
        log.error(f"❌ Ошибка обработки документа: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке документа:\n{str(e)}"
        )


__all__ = ['handle_document']
