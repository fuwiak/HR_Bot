"""
Yandex Disk API Helper
Интеграция с Яндекс.Диском для работы с файлами
"""
import os
import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

log = logging.getLogger()

# ===================== CONFIGURATION =====================
YANDEX_DISK_TOKEN = os.getenv("YANDEX_TOKEN") or os.getenv("YANDEX_DISK_TOKEN")
YANDEX_DISK_API = "https://cloud-api.yandex.net/v1/disk"

if YANDEX_DISK_TOKEN:
    log.info(f"✅ Yandex Disk Token установлен (длина: {len(YANDEX_DISK_TOKEN)})")
else:
    log.warning("⚠️ Yandex Disk Token не установлен!")

# ===================== HELPER FUNCTIONS =====================

def get_headers() -> Dict[str, str]:
    """Получить заголовки для API запросов"""
    if not YANDEX_DISK_TOKEN:
        return {}
    return {
        "Authorization": f"OAuth {YANDEX_DISK_TOKEN}",
        "Content-Type": "application/json"
    }

# ===================== DISK INFO =====================

async def get_disk_info() -> Optional[Dict]:
    """
    Получить информацию о диске
    API: GET /disk/
    """
    if not YANDEX_DISK_TOKEN:
        log.error("❌ Yandex Disk Token не установлен")
        return None
    
    url = f"{YANDEX_DISK_API}/"
    headers = get_headers()
    
    try:
        log.info(f"📤 [Yandex Disk] Запрос информации о диске")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [Yandex Disk] Ошибка: {response.status}")
                    log.error(f"❌ Response: {error_text[:500]}")
                    return None
                
                result = await response.json()
                log.info(f"✅ [Yandex Disk] Информация получена")
                return result
                
    except Exception as e:
        log.error(f"❌ [Yandex Disk] Ошибка получения информации: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

# ===================== FILES OPERATIONS =====================

async def list_files(path: str = "/", limit: int = 100, offset: int = 0) -> Optional[Dict]:
    """
    Получить список файлов в папке
    API: GET /disk/resources?path={path}
    
    Args:
        path: Путь к папке (по умолчанию корень "/")
        limit: Количество файлов
        offset: Смещение для пагинации
    
    Returns:
        Словарь с файлами и метаданными
    """
    if not YANDEX_DISK_TOKEN:
        log.error("❌ Yandex Disk Token не установлен")
        return None
    
    url = f"{YANDEX_DISK_API}/resources"
    headers = get_headers()
    params = {
        "path": path,
        "limit": limit,
        "offset": offset,
        "fields": "name,type,size,created,modified,path,_embedded.items"
    }
    
    try:
        log.info(f"📤 [Yandex Disk] Запрос файлов: {path}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [Yandex Disk] Ошибка: {response.status}")
                    log.error(f"❌ Response: {error_text[:500]}")
                    return None
                
                result = await response.json()
                
                items = result.get("_embedded", {}).get("items", [])
                log.info(f"✅ [Yandex Disk] Получено файлов: {len(items)}")
                return result
                
    except Exception as e:
        log.error(f"❌ [Yandex Disk] Ошибка получения файлов: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

async def search_files(query: str, limit: int = 50) -> Optional[List[Dict]]:
    """
    Поиск файлов на диске
    API: GET /disk/resources?path=/&fields=...
    
    Args:
        query: Поисковый запрос
        limit: Максимальное количество результатов
    
    Returns:
        Список найденных файлов
    """
    if not YANDEX_DISK_TOKEN:
        log.error("❌ Yandex Disk Token не установлен")
        return None
    
    # Получаем все файлы и фильтруем локально
    result = await list_files(path="/", limit=limit)
    
    if not result:
        return []
    
    items = result.get("_embedded", {}).get("items", [])
    query_lower = query.lower()
    
    # Фильтруем по названию
    filtered = [
        item for item in items
        if query_lower in item.get("name", "").lower()
    ]
    
    log.info(f"🔍 [Yandex Disk] Найдено файлов по запросу '{query}': {len(filtered)}")
    return filtered

async def get_download_link(path: str) -> Optional[str]:
    """
    Получить ссылку для скачивания файла
    API: GET /disk/resources/download?path={path}
    
    Args:
        path: Путь к файлу
    
    Returns:
        URL для скачивания
    """
    if not YANDEX_DISK_TOKEN:
        log.error("❌ Yandex Disk Token не установлен")
        return None
    
    url = f"{YANDEX_DISK_API}/resources/download"
    headers = get_headers()
    params = {"path": path}
    
    try:
        log.info(f"📤 [Yandex Disk] Запрос ссылки на скачивание: {path}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [Yandex Disk] Ошибка: {response.status}")
                    log.error(f"❌ Response: {error_text[:500]}")
                    return None
                
                result = await response.json()
                download_url = result.get("href")
                
                if download_url:
                    log.info(f"✅ [Yandex Disk] Ссылка получена")
                    return download_url
                else:
                    log.error(f"❌ [Yandex Disk] Ссылка не найдена в ответе")
                    return None
                
    except Exception as e:
        log.error(f"❌ [Yandex Disk] Ошибка получения ссылки: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

async def download_file_content(path: str) -> Optional[bytes]:
    """
    Скачать содержимое файла
    
    Args:
        path: Путь к файлу на диске
    
    Returns:
        Содержимое файла в байтах
    """
    download_url = await get_download_link(path)
    
    if not download_url:
        return None
    
    try:
        log.info(f"📥 [Yandex Disk] Скачивание файла: {path}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status >= 400:
                    log.error(f"❌ [Yandex Disk] Ошибка скачивания: {response.status}")
                    return None
                
                content = await response.read()
                log.info(f"✅ [Yandex Disk] Файл скачан: {len(content)} байт")
                return content
                
    except Exception as e:
        log.error(f"❌ [Yandex Disk] Ошибка скачивания: {e}")
        return None

async def read_text_file(path: str, encoding: str = "utf-8") -> Optional[str]:
    """
    Прочитать текстовый файл
    
    Args:
        path: Путь к файлу
        encoding: Кодировка (по умолчанию utf-8)
    
    Returns:
        Содержимое файла как строка
    """
    content = await download_file_content(path)
    
    if not content:
        return None
    
    try:
        text = content.decode(encoding)
        log.info(f"✅ [Yandex Disk] Текстовый файл прочитан: {len(text)} символов")
        return text
    except UnicodeDecodeError:
        # Пробуем другие кодировки
        for enc in ['cp1251', 'latin-1', 'utf-16']:
            try:
                text = content.decode(enc)
                log.info(f"✅ [Yandex Disk] Текстовый файл прочитан (кодировка: {enc})")
                return text
            except:
                continue
        
        log.error(f"❌ [Yandex Disk] Не удалось декодировать файл")
        return None

# ===================== FILE TYPES =====================

def get_file_type(filename: str) -> str:
    """Определить тип файла по расширению"""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    # Документы
    if ext in ['doc', 'docx', 'txt', 'pdf', 'rtf']:
        return 'document'
    # Таблицы
    elif ext in ['xls', 'xlsx', 'csv']:
        return 'spreadsheet'
    # Презентации
    elif ext in ['ppt', 'pptx']:
        return 'presentation'
    # Изображения
    elif ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg']:
        return 'image'
    # Архивы
    elif ext in ['zip', 'rar', '7z', 'tar', 'gz']:
        return 'archive'
    # Код
    elif ext in ['py', 'js', 'html', 'css', 'json', 'xml', 'yaml', 'yml']:
        return 'code'
    else:
        return 'other'

def format_file_size(size_bytes: int) -> str:
    """Форматировать размер файла"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} ТБ"

# ===================== RECENT FILES =====================

async def get_recent_files(limit: int = 20) -> Optional[List[Dict]]:
    """
    Получить последние измененные файлы
    
    Args:
        limit: Количество файлов
    
    Returns:
        Список файлов, отсортированных по дате изменения
    """
    result = await list_files(path="/", limit=100)
    
    if not result:
        return []
    
    items = result.get("_embedded", {}).get("items", [])
    
    # Фильтруем только файлы (не папки) и сортируем по дате изменения
    files = [
        item for item in items
        if item.get("type") == "file"
    ]
    
    # Сортируем по дате изменения (новые первые)
    files.sort(key=lambda x: x.get("modified", ""), reverse=True)
    
    return files[:limit]
