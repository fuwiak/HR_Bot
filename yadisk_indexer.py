"""
Yandex Disk Indexer - фоновая индексация файлов в Qdrant Cloud
Автоматически сканирует Яндекс.Диск и индексирует документы в векторную БД
"""
import os
import sys
import logging
import asyncio
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
import hashlib

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('yadisk_indexer.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# ===================== CONFIGURATION =====================

# Папки на Яндекс.Диске для индексации (по умолчанию корень)
WATCH_FOLDERS = os.getenv("YADISK_WATCH_FOLDERS", "/").split(",")

# Интервал сканирования (в секундах)
SCAN_INTERVAL = int(os.getenv("YADISK_SCAN_INTERVAL", "300"))  # 5 минут

# Коллекция Qdrant
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "hr_knowledge_base")

# Максимальный размер файла для обработки (в МБ)
MAX_FILE_SIZE_MB = int(os.getenv("YADISK_MAX_FILE_SIZE", "50"))

# Поддерживаемые расширения
SUPPORTED_EXTENSIONS = {
    '.txt', '.md', '.pdf', 
    '.doc', '.docx', 
    '.xls', '.xlsx',
    '.csv', '.json', '.xml'
}

# ===================== IMPORTS =====================

try:
    from yandex_disk_helper import (
        list_files, 
        download_file_content,
        get_file_type
    )
    from qdrant_helper import (
        get_qdrant_client,
        generate_embedding_async
    )
    from text_splitter import RecursiveCharacterTextSplitter
    log.info("✅ Все модули импортированы")
except ImportError as e:
    log.error(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

# ===================== FILE PROCESSING =====================

def get_file_hash(content: bytes) -> str:
    """Получить хеш файла для отслеживания изменений"""
    return hashlib.md5(content).hexdigest()

def extract_text_from_content(content: bytes, filename: str) -> Optional[str]:
    """
    Извлечь текст из содержимого файла
    
    Args:
        content: Содержимое файла в байтах
        filename: Имя файла для определения типа
    
    Returns:
        Извлеченный текст или None
    """
    ext = Path(filename).suffix.lower()
    
    try:
        # TXT, MD, JSON, XML, CSV
        if ext in ['.txt', '.md', '.json', '.xml', '.csv']:
            for encoding in ['utf-8', 'cp1251', 'latin-1']:
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    continue
            log.warning(f"⚠️ Не удалось декодировать {filename}")
            return None
        
        # PDF
        elif ext == '.pdf':
            try:
                import PyPDF2
                import io
                
                pdf_file = io.BytesIO(content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = ""
                
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                return text.strip()
            except Exception as e:
                log.error(f"❌ Ошибка обработки PDF {filename}: {e}")
                return None
        
        # DOCX
        elif ext == '.docx':
            try:
                from docx import Document
                import io
                
                doc_file = io.BytesIO(content)
                doc = Document(doc_file)
                text = "\n".join([para.text for para in doc.paragraphs])
                
                return text.strip()
            except Exception as e:
                log.error(f"❌ Ошибка обработки DOCX {filename}: {e}")
                return None
        
        # DOC (старый формат)
        elif ext == '.doc':
            log.warning(f"⚠️ Формат .doc не поддерживается напрямую: {filename}")
            return None
        
        # XLSX
        elif ext in ['.xlsx', '.xls']:
            try:
                import pandas as pd
                import io
                
                excel_file = io.BytesIO(content)
                
                # Читаем все листы
                dfs = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl' if ext == '.xlsx' else 'xlrd')
                
                text = ""
                for sheet_name, df in dfs.items():
                    text += f"\n=== {sheet_name} ===\n"
                    text += df.to_string(index=False)
                    text += "\n"
                
                return text.strip()
            except Exception as e:
                log.error(f"❌ Ошибка обработки Excel {filename}: {e}")
                return None
        
        else:
            log.warning(f"⚠️ Неподдерживаемый формат: {filename}")
            return None
            
    except Exception as e:
        log.error(f"❌ Ошибка извлечения текста из {filename}: {e}")
        return None

# ===================== QDRANT OPERATIONS =====================

async def index_document(
    file_path: str,
    file_name: str,
    content: bytes,
    file_hash: str,
    modified: str
) -> bool:
    """
    Индексировать документ в Qdrant
    
    Args:
        file_path: Путь к файлу на Яндекс.Диске
        file_name: Имя файла
        content: Содержимое файла
        file_hash: MD5 хеш файла
        modified: Дата изменения
    
    Returns:
        True если успешно, False если ошибка
    """
    try:
        log.info(f"📄 Обработка: {file_name}")
        
        # Извлекаем текст
        text = extract_text_from_content(content, file_name)
        
        if not text or len(text.strip()) < 50:
            log.warning(f"⚠️ Слишком мало текста в {file_name}, пропускаем")
            return False
        
        log.info(f"✅ Извлечено {len(text)} символов из {file_name}")
        
        # Разбиваем на чанки
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        chunks = text_splitter.split_text(text)
        log.info(f"📦 Создано {len(chunks)} чанков из {file_name}")
        
        if not chunks:
            log.warning(f"⚠️ Нет чанков для {file_name}")
            return False
        
        # Получаем клиент Qdrant
        client = get_qdrant_client()
        
        if not client:
            log.error("❌ Не удалось подключиться к Qdrant")
            return False
        
        # Создаем точки для загрузки
        from qdrant_client.models import PointStruct
        points = []
        
        for i, chunk in enumerate(chunks):
            # Генерируем эмбеддинг
            embedding = await generate_embedding_async(chunk)
            
            if not embedding:
                log.warning(f"⚠️ Не удалось создать эмбеддинг для чанка {i} из {file_name}")
                continue
            
            # Создаем уникальный ID
            point_id = abs(hash(f"{file_hash}_{i}")) % (10 ** 10)
            
            # Метаданные
            metadata = {
                "text": chunk,
                "source": "yadisk",
                "file_path": file_path,
                "file_name": file_name,
                "file_hash": file_hash,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "modified": modified,
                "indexed_at": datetime.now().isoformat()
            }
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=metadata
            )
            
            points.append(point)
        
        if not points:
            log.error(f"❌ Не удалось создать точки для {file_name}")
            return False
        
        # Загружаем в Qdrant батчами
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            
            try:
                client.upsert(
                    collection_name=QDRANT_COLLECTION,
                    points=batch
                )
                log.info(f"✅ Загружено {len(batch)} точек ({i+1}-{i+len(batch)} из {len(points)}) для {file_name}")
            except Exception as e:
                log.error(f"❌ Ошибка загрузки батча для {file_name}: {e}")
                return False
        
        log.info(f"🎉 Файл {file_name} успешно проиндексирован ({len(points)} точек)")
        return True
        
    except Exception as e:
        log.error(f"❌ Ошибка индексации {file_name}: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return False

# ===================== FILE SCANNING =====================

async def scan_folder(folder_path: str, processed_hashes: Set[str]) -> List[Dict]:
    """
    Сканировать папку на Яндекс.Диске
    
    Args:
        folder_path: Путь к папке
        processed_hashes: Множество хешей уже обработанных файлов
    
    Returns:
        Список новых/измененных файлов для обработки
    """
    try:
        log.info(f"🔍 Сканирование папки: {folder_path}")
        
        result = await list_files(path=folder_path, limit=1000)
        
        if not result:
            log.warning(f"⚠️ Не удалось получить список файлов из {folder_path}")
            return []
        
        items = result.get("_embedded", {}).get("items", [])
        files_to_process = []
        
        for item in items:
            item_type = item.get("type")
            
            # Рекурсивно обрабатываем подпапки
            if item_type == "dir":
                subfolder_path = item.get("path", "")
                log.info(f"📁 Найдена подпапка: {subfolder_path}")
                # Можно раскомментировать для рекурсивного обхода
                # subfiles = await scan_folder(subfolder_path, processed_hashes)
                # files_to_process.extend(subfiles)
                continue
            
            # Обрабатываем только файлы
            if item_type != "file":
                continue
            
            name = item.get("name", "")
            path = item.get("path", "")
            size = item.get("size", 0)
            modified = item.get("modified", "")
            
            # Проверяем расширение
            ext = Path(name).suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            
            # Проверяем размер
            size_mb = size / (1024 * 1024)
            if size_mb > MAX_FILE_SIZE_MB:
                log.warning(f"⚠️ Файл {name} слишком большой ({size_mb:.1f} МБ), пропускаем")
                continue
            
            files_to_process.append({
                "name": name,
                "path": path,
                "size": size,
                "modified": modified
            })
        
        log.info(f"✅ Найдено {len(files_to_process)} файлов для обработки в {folder_path}")
        return files_to_process
        
    except Exception as e:
        log.error(f"❌ Ошибка сканирования {folder_path}: {e}")
        return []

async def process_files(files: List[Dict], processed_hashes: Set[str]) -> int:
    """
    Обработать список файлов
    
    Args:
        files: Список файлов
        processed_hashes: Множество обработанных хешей
    
    Returns:
        Количество успешно обработанных файлов
    """
    success_count = 0
    
    for file_info in files:
        name = file_info["name"]
        path = file_info["path"]
        modified = file_info["modified"]
        
        try:
            # Скачиваем файл
            log.info(f"📥 Скачивание: {name}")
            content = await download_file_content(path)
            
            if not content:
                log.warning(f"⚠️ Не удалось скачать {name}")
                continue
            
            # Получаем хеш
            file_hash = get_file_hash(content)
            
            # Проверяем, обрабатывали ли уже
            if file_hash in processed_hashes:
                log.info(f"⏭️ Файл {name} уже обработан, пропускаем")
                continue
            
            # Индексируем
            success = await index_document(
                file_path=path,
                file_name=name,
                content=content,
                file_hash=file_hash,
                modified=modified
            )
            
            if success:
                processed_hashes.add(file_hash)
                success_count += 1
                log.info(f"✅ [{success_count}] Успешно: {name}")
            else:
                log.warning(f"⚠️ Не удалось проиндексировать {name}")
            
            # Небольшая задержка между файлами
            await asyncio.sleep(1)
            
        except Exception as e:
            log.error(f"❌ Ошибка обработки {name}: {e}")
            continue
    
    return success_count

# ===================== MAIN LOOP =====================

async def indexer_loop():
    """Основной цикл индексации"""
    log.info("🚀 Запуск Yandex Disk Indexer")
    log.info(f"📂 Папки для мониторинга: {WATCH_FOLDERS}")
    log.info(f"⏱️ Интервал сканирования: {SCAN_INTERVAL} секунд")
    log.info(f"📦 Коллекция Qdrant: {QDRANT_COLLECTION}")
    log.info(f"📏 Макс. размер файла: {MAX_FILE_SIZE_MB} МБ")
    log.info(f"📄 Поддерживаемые форматы: {', '.join(SUPPORTED_EXTENSIONS)}")
    
    # Множество обработанных файлов (по хешу)
    processed_hashes: Set[str] = set()
    
    iteration = 0
    
    while True:
        iteration += 1
        log.info(f"\n{'='*60}")
        log.info(f"🔄 ИТЕРАЦИЯ #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log.info(f"{'='*60}")
        
        try:
            all_files = []
            
            # Сканируем все указанные папки
            for folder in WATCH_FOLDERS:
                folder = folder.strip()
                log.info(f"\n📂 Сканирование: {folder}")
                files = await scan_folder(folder, processed_hashes)
                all_files.extend(files)
            
            log.info(f"\n📊 Всего найдено файлов: {len(all_files)}")
            log.info(f"📊 Уже обработано: {len(processed_hashes)}")
            
            if all_files:
                log.info(f"\n🔧 Начинаем обработку {len(all_files)} файлов...")
                success_count = await process_files(all_files, processed_hashes)
                
                log.info(f"\n✅ Итерация #{iteration} завершена")
                log.info(f"✅ Обработано файлов: {success_count}")
                log.info(f"📊 Всего в кеше: {len(processed_hashes)} файлов")
            else:
                log.info(f"\n💤 Новых файлов не найдено")
            
            # Ждем следующей итерации
            log.info(f"\n⏳ Следующее сканирование через {SCAN_INTERVAL} секунд...")
            await asyncio.sleep(SCAN_INTERVAL)
            
        except KeyboardInterrupt:
            log.info("\n🛑 Получен сигнал остановки")
            break
        except Exception as e:
            log.error(f"\n❌ Ошибка в основном цикле: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            log.info(f"⏳ Повтор через {SCAN_INTERVAL} секунд...")
            await asyncio.sleep(SCAN_INTERVAL)
    
    log.info("👋 Yandex Disk Indexer остановлен")

# ===================== ENTRY POINT =====================

def main():
    """Точка входа"""
    try:
        asyncio.run(indexer_loop())
    except KeyboardInterrupt:
        log.info("\n👋 Завершение работы...")
        sys.exit(0)

if __name__ == "__main__":
    main()
