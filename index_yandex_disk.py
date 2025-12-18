"""
Скрипт для скачивания и индексации файлов с Яндекс Диска в Qdrant
Поддерживает скачивание через Яндекс Диск API и индексацию документов
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import hashlib

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger()

# Импорты для работы с Яндекс Диском
try:
    from yadisk import YaDisk
    YADISK_AVAILABLE = True
except ImportError:
    YADISK_AVAILABLE = False
    log.warning("⚠️ yadisk не установлен. Для скачивания с Яндекс Диска установите: pip install yadisk")

# Импорты для индексации
try:
    from qdrant_loader import QdrantLoader
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    log.error("❌ qdrant_loader не доступен")

# Поддерживаемые форматы файлов
SUPPORTED_EXTENSIONS = [".docx", ".xlsx", ".xls", ".pdf", ".txt", ".md"]


def download_from_yandex_disk(folder_url: str, local_path: Path, token: Optional[str] = None) -> bool:
    """
    Скачивает файлы с Яндекс Диска
    
    Args:
        folder_url: URL папки на Яндекс Диске (например, из браузера)
        local_path: Локальная папка для сохранения файлов
        token: OAuth токен Яндекс Диска (опционально)
    
    Returns:
        True при успехе
    """
    if not YADISK_AVAILABLE:
        log.error("❌ Библиотека yadisk не установлена")
        log.info("📥 Для скачивания файлов с Яндекс Диска:")
        log.info("   1. Установите: pip install yadisk")
        log.info("   2. Получите OAuth токен: https://yandex.ru/dev/id/doc/ru/register-client")
        log.info("   3. Или скачайте файлы вручную в папку и используйте --local-path")
        return False
    
    if not token:
        log.error("❌ Яндекс Диск токен не предоставлен")
        log.info("📥 Получите OAuth токен: https://yandex.ru/dev/id/doc/ru/register-client")
        log.info("   Установите переменную окружения: export YANDEX_DISK_TOKEN=your_token")
        return False
    
    try:
        yadisk = YaDisk(token=token)
        
        # Проверяем авторизацию
        if not yadisk.check_token():
            log.error("❌ Неверный токен Яндекс Диска")
            return False
        
        # Извлекаем путь папки из URL
        # URL вида: https://disk.yandex.ru/d/-BtoZgh5VMdsPQ
        folder_path = None
        if "/d/" in folder_url:
            # Публичная ссылка - нужно использовать публичную загрузку
            log.info(f"📥 Используется публичная ссылка: {folder_url}")
            log.warning("⚠️ Для публичных папок скачивание через API может быть ограничено")
            log.info("💡 Рекомендуется скачать файлы вручную и использовать --local-path")
            return False
        else:
            # Прямой путь к папке
            folder_path = folder_url
        
        # Скачиваем файлы рекурсивно
        local_path.mkdir(parents=True, exist_ok=True)
        
        def download_recursive(remote_path: str, local_dir: Path):
            """Рекурсивное скачивание"""
            try:
                items = list(yadisk.listdir(remote_path))
                for item in items:
                    if item.type == "file":
                        # Скачиваем файл
                        file_ext = Path(item.name).suffix.lower()
                        if file_ext in SUPPORTED_EXTENSIONS:
                            local_file = local_dir / item.name
                            log.info(f"📥 Скачивание: {item.name}")
                            yadisk.download(item.path, str(local_file))
                        else:
                            log.debug(f"⏭️  Пропуск (неподдерживаемый формат): {item.name}")
                    elif item.type == "dir":
                        # Создаем подпапку и рекурсивно скачиваем
                        subdir = local_dir / item.name
                        subdir.mkdir(exist_ok=True)
                        download_recursive(item.path, subdir)
            except Exception as e:
                log.error(f"❌ Ошибка скачивания {remote_path}: {e}")
        
        download_recursive(folder_path, local_path)
        log.info(f"✅ Файлы скачаны в: {local_path}")
        return True
        
    except Exception as e:
        log.error(f"❌ Ошибка работы с Яндекс Диском: {e}")
        return False


def index_directory(directory: Path, category: str = "yandex_disk") -> Dict:
    """
    Индексирует все документы в директории
    
    Args:
        directory: Путь к директории
        category: Категория документов
    
    Returns:
        Статистика индексации
    """
    stats = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "files": []
    }
    
    if not QDRANT_AVAILABLE:
        log.error("❌ QdrantLoader не доступен")
        return stats
    
    loader = QdrantLoader()
    
    # Рекурсивно обходим все файлы
    for file_path in directory.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            stats["total"] += 1
            log.info(f"📄 Индексация: {file_path.relative_to(directory)}")
            
            try:
                # Формируем source_url относительно директории
                relative_path = file_path.relative_to(directory)
                source_url = f"file://media/yandex_disk/{relative_path}"
                
                # Индексируем файл
                chunks_count = loader.load_from_file(
                    file_path=str(file_path),
                    source_url=source_url,
                    metadata={
                        "category": category,
                        "source": "yandex_disk",
                        "indexed_at": datetime.now().isoformat()
                    }
                )
                
                if chunks_count > 0:
                    stats["success"] += 1
                    stats["files"].append(str(file_path))
                    log.info(f"✅ Индексировано {chunks_count} чанков")
                else:
                    stats["failed"] += 1
                    log.warning(f"⚠️ Файл не индексирован (возможно, пустой или отфильтрован)")
                    
            except Exception as e:
                stats["failed"] += 1
                log.error(f"❌ Ошибка индексации {file_path}: {e}")
    
    return stats


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Индексация файлов с Яндекс Диска в Qdrant")
    parser.add_argument(
        "--yandex-url",
        type=str,
        help="URL папки на Яндекс Диске (например, https://disk.yandex.ru/d/...)",
        default=os.getenv("YANDEX_DISK_FOLDER_URL", "https://disk.yandex.ru/d/-BtoZgh5VMdsPQ")
    )
    parser.add_argument(
        "--local-path",
        type=str,
        help="Локальная папка с файлами (если файлы уже скачаны)",
        default=None
    )
    parser.add_argument(
        "--download-path",
        type=str,
        help="Папка для скачивания файлов с Яндекс Диска",
        default="media/yandex_disk"
    )
    parser.add_argument(
        "--token",
        type=str,
        help="OAuth токен Яндекс Диска",
        default=os.getenv("YANDEX_DISK_TOKEN")
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Категория документов",
        default="yandex_disk"
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Не скачивать файлы, только индексировать локальную папку"
    )
    
    args = parser.parse_args()
    
    log.info("="*60)
    log.info("📚 Индексация файлов с Яндекс Диска в Qdrant")
    log.info("="*60)
    
    # Определяем путь к папке с файлами
    if args.local_path:
        # Используем указанную локальную папку
        local_path = Path(args.local_path)
        if not local_path.exists():
            log.error(f"❌ Локальная папка не существует: {local_path}")
            sys.exit(1)
        log.info(f"📁 Используется локальная папка: {local_path}")
    else:
        # Используем папку для скачивания
        local_path = Path(args.download_path)
        
        if not args.no_download:
            # Скачиваем файлы с Яндекс Диска
            log.info(f"📥 Скачивание файлов с Яндекс Диска...")
            log.info(f"   URL: {args.yandex_url}")
            log.info(f"   Папка: {local_path}")
            
            if not download_from_yandex_disk(args.yandex_url, local_path, args.token):
                log.warning("⚠️ Не удалось скачать файлы с Яндекс Диска")
                log.info("💡 Скачайте файлы вручную в папку и используйте --local-path")
                sys.exit(1)
        else:
            if not local_path.exists():
                log.error(f"❌ Папка не существует: {local_path}")
                log.info("💡 Используйте --local-path или убедитесь, что файлы скачаны")
                sys.exit(1)
    
    # Индексируем файлы
    log.info(f"\n📚 Начало индексации файлов...")
    stats = index_directory(local_path, category=args.category)
    
    # Выводим статистику
    log.info("\n" + "="*60)
    log.info("📊 Статистика индексации:")
    log.info(f"   Всего файлов: {stats['total']}")
    log.info(f"   Успешно: {stats['success']}")
    log.info(f"   Ошибок: {stats['failed']}")
    log.info("="*60)
    
    if stats['success'] > 0:
        log.info("✅ Индексация завершена успешно!")
    else:
        log.warning("⚠️ Не удалось проиндексировать ни одного файла")
        sys.exit(1)


if __name__ == "__main__":
    main()









