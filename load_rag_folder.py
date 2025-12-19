"""
Загрузка всех файлов из папки /RAG HR-Business-Consultant в Qdrant
Фоновый скрипт для индексации документов в векторную базу данных
"""
import os
import sys
import asyncio
import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('load_rag_folder.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# ===================== CONFIGURATION =====================

# Yandex Disk
TOKEN = os.getenv("YANDEX_TOKEN", "y0__xDwjeyGARi1ujwg-6Lo3RVdezzMTmMlylbqtmwcpcYAWEQ5Dg")
BASE_URL = "https://cloud-api.yandex.net/v1/disk"
HEADERS = {"Authorization": f"OAuth {TOKEN}"}

# Папка для загрузки
FOLDER_PATH = "/RAG HR-Business-Consultant"

# Qdrant
COLLECTION_NAME = "hr2137_bot_knowledge_base"

# Поддерживаемые форматы
SUPPORTED_EXTENSIONS = {'.txt', '.md', '.pdf', '.docx', '.xlsx', '.xls', '.csv', '.json', '.xml'}

# ===================== IMPORTS =====================

try:
    from qdrant_helper import get_qdrant_client, generate_embedding_async
    from text_splitter import RecursiveCharacterTextSplitter
    from ydisk_indexer import extract_text_from_content  # Используем функцию из indexer
    log.info("✅ Все модули импортированы")
except ImportError as e:
    log.error(f"❌ Ошибка импорта: {e}")
    # Попробуем импортировать напрямую
    try:
        from yadisk_indexer import extract_text_from_content
        log.info("✅ Импорт extract_text_from_content успешен")
    except:
        log.error("❌ Не удалось импортировать функции обработки текста")
        sys.exit(1)

# ===================== YANDEX DISK FUNCTIONS =====================

def list_folder_recursive(folder_path: str) -> List[Dict]:
    """
    Рекурсивно получить все файлы из папки и подпапок
    
    Args:
        folder_path: Путь к папке
    
    Returns:
        Список всех файлов
    """
    all_files = []
    
    try:
        response = requests.get(
            f"{BASE_URL}/resources",
            headers=HEADERS,
            params={"path": folder_path, "limit": 1000},
            verify=False  # Отключаем проверку SSL
        )
        
        if response.status_code != 200:
            log.error(f"❌ Ошибка получения {folder_path}: {response.status_code}")
            return []
        
        data = response.json()
        items = data.get('_embedded', {}).get('items', [])
        
        log.info(f"📂 {folder_path}: найдено {len(items)} элементов")
        
        for item in items:
            if item['type'] == 'dir':
                # Рекурсивно обрабатываем подпапки
                log.info(f"📁 Сканирование подпапки: {item['name']}")
                subfolder_files = list_folder_recursive(item['path'])
                all_files.extend(subfolder_files)
            else:
                # Добавляем файл
                all_files.append(item)
        
        return all_files
        
    except Exception as e:
        log.error(f"❌ Ошибка сканирования {folder_path}: {e}")
        return []

def download_file(file_path: str) -> Optional[bytes]:
    """
    Скачать файл с Yandex Disk
    
    Args:
        file_path: Путь к файлу
    
    Returns:
        Содержимое файла в байтах
    """
    try:
        # Получаем ссылку на скачивание
        response = requests.get(
            f"{BASE_URL}/resources/download",
            headers=HEADERS,
            params={"path": file_path},
            verify=False
        )
        
        if response.status_code != 200:
            log.error(f"❌ Ошибка получения ссылки: {response.status_code}")
            return None
        
        download_url = response.json().get('href')
        
        if not download_url:
            log.error(f"❌ Не удалось получить ссылку на скачивание")
            return None
        
        # Скачиваем файл
        file_response = requests.get(download_url, verify=False)
        
        if file_response.status_code == 200:
            return file_response.content
        else:
            log.error(f"❌ Ошибка скачивания: {file_response.status_code}")
            return None
            
    except Exception as e:
        log.error(f"❌ Ошибка скачивания {file_path}: {e}")
        return None

# ===================== TEXT EXTRACTION =====================

def extract_text_from_file(content: bytes, filename: str) -> Optional[str]:
    """
    Извлечь текст из файла
    
    Args:
        content: Содержимое файла
        filename: Имя файла
    
    Returns:
        Извлеченный текст
    """
    ext = Path(filename).suffix.lower()
    
    try:
        # Текстовые форматы
        if ext in ['.txt', '.md', '.json', '.xml', '.csv']:
            for encoding in ['utf-8', 'cp1251', 'latin-1']:
                try:
                    return content.decode(encoding)
                except:
                    continue
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
                log.error(f"❌ Ошибка PDF: {e}")
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
                log.error(f"❌ Ошибка DOCX: {e}")
                return None
        
        # Excel
        elif ext in ['.xlsx', '.xls']:
            try:
                import pandas as pd
                import io
                excel_file = io.BytesIO(content)
                dfs = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl' if ext == '.xlsx' else None)
                text = ""
                for sheet_name, df in dfs.items():
                    text += f"\n=== {sheet_name} ===\n"
                    text += df.to_string(index=False)
                    text += "\n"
                return text.strip()
            except Exception as e:
                log.error(f"❌ Ошибка Excel: {e}")
                return None
        
        else:
            log.warning(f"⚠️ Неподдерживаемый формат: {ext}")
            return None
            
    except Exception as e:
        log.error(f"❌ Ошибка извлечения текста: {e}")
        return None

# ===================== QDRANT INDEXING =====================

async def index_file_to_qdrant(file_info: Dict) -> bool:
    """
    Индексировать файл в Qdrant
    
    Args:
        file_info: Информация о файле
    
    Returns:
        True если успешно
    """
    file_name = file_info.get('name', '')
    file_path = file_info.get('path', '')
    file_size = file_info.get('size', 0)
    
    try:
        log.info(f"📄 Обработка: {file_name}")
        
        # Проверяем расширение
        ext = Path(file_name).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            log.warning(f"⚠️ Пропускаем (неподдерживаемый формат): {file_name}")
            return False
        
        # Проверяем размер (макс 50 МБ)
        if file_size > 50 * 1024 * 1024:
            log.warning(f"⚠️ Пропускаем (слишком большой): {file_name} ({file_size / (1024*1024):.1f} МБ)")
            return False
        
        # Скачиваем файл
        log.info(f"📥 Скачивание: {file_name}")
        content = download_file(file_path)
        
        if not content:
            log.error(f"❌ Не удалось скачать: {file_name}")
            return False
        
        # Извлекаем текст
        log.info(f"📝 Извлечение текста: {file_name}")
        text = extract_text_from_file(content, file_name)
        
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
        import hashlib
        
        points = []
        file_hash = hashlib.md5(content).hexdigest()
        
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
                "source": "yadisk_rag_folder",
                "file_path": file_path,
                "file_name": file_name,
                "file_hash": file_hash,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "modified": file_info.get('modified', ''),
                "indexed_at": datetime.now().isoformat(),
                "folder": FOLDER_PATH
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
                    collection_name=COLLECTION_NAME,
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

# ===================== MAIN =====================

async def main():
    """Основная функция"""
    log.info("="*70)
    log.info(f"🚀 Загрузка файлов из папки: {FOLDER_PATH}")
    log.info(f"📦 Коллекция Qdrant: {COLLECTION_NAME}")
    log.info("="*70)
    
    # Получаем все файлы
    log.info(f"\n📂 Сканирование папки: {FOLDER_PATH}")
    all_files = list_folder_recursive(FOLDER_PATH)
    
    log.info(f"\n📊 Всего найдено файлов: {len(all_files)}")
    
    if not all_files:
        log.error("❌ Файлов не найдено!")
        return
    
    # Фильтруем по поддерживаемым форматам
    supported_files = [
        f for f in all_files
        if Path(f['name']).suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    log.info(f"📄 Поддерживаемых файлов: {len(supported_files)}")
    
    if not supported_files:
        log.error("❌ Нет файлов для обработки!")
        return
    
    # Обрабатываем файлы
    log.info(f"\n🔧 Начинаем индексацию...")
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for idx, file_info in enumerate(supported_files, 1):
        file_name = file_info.get('name', '')
        
        log.info(f"\n{'='*70}")
        log.info(f"[{idx}/{len(supported_files)}] Файл: {file_name}")
        log.info(f"{'='*70}")
        
        try:
            result = await index_file_to_qdrant(file_info)
            
            if result:
                success_count += 1
                log.info(f"✅ [{success_count}] Успешно: {file_name}")
            else:
                skipped_count += 1
                log.warning(f"⚠️ Пропущен: {file_name}")
            
            # Небольшая задержка между файлами
            await asyncio.sleep(1)
            
        except Exception as e:
            error_count += 1
            log.error(f"❌ Ошибка обработки {file_name}: {e}")
            continue
    
    # Итоги
    log.info(f"\n{'='*70}")
    log.info(f"📊 ИТОГИ")
    log.info(f"{'='*70}")
    log.info(f"✅ Успешно: {success_count}")
    log.info(f"⚠️ Пропущено: {skipped_count}")
    log.info(f"❌ Ошибок: {error_count}")
    log.info(f"📄 Всего: {len(supported_files)}")
    log.info(f"\n🎉 Загрузка завершена!")

if __name__ == "__main__":
    # Отключаем предупреждения SSL
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Запускаем
    asyncio.run(main())
