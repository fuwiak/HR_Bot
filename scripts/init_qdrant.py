#!/usr/bin/env python3
"""
Скрипт инициализации Qdrant коллекций при старте контейнера
Создает коллекцию если её нет
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from services.rag.qdrant_helper import ensure_collection, get_qdrant_client, COLLECTION_NAME, QDRANT_URL
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log = logging.getLogger(__name__)
    
    def main():
        """Инициализация Qdrant коллекции"""
        log.info("🔧 Инициализация Qdrant коллекции...")
        log.info(f"📍 Qdrant URL: {QDRANT_URL}")
        log.info(f"📦 Коллекция: {COLLECTION_NAME}")
        
        # Просто вызываем ensure_collection - она сама проверит и создаст если нужно
        # Если коллекция уже существует или не удалось проверить - продолжаем без ошибок
        try:
            if ensure_collection():
                log.info(f"✅ Коллекция '{COLLECTION_NAME}' готова к использованию")
            else:
                log.info(f"ℹ️ Коллекция '{COLLECTION_NAME}' будет проверена при первом использовании")
            return 0
        except Exception as e:
            # Если ошибка - просто продолжаем, коллекция может существовать
            log.warning(f"⚠️ Ошибка при инициализации коллекции: {e}")
            log.info(f"   Продолжаем работу, коллекция '{COLLECTION_NAME}' будет проверена при использовании")
            return 0
    
    if __name__ == "__main__":
        exit_code = main()
        sys.exit(exit_code)
        
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("   Убедитесь, что все зависимости установлены")
    sys.exit(1)
except Exception as e:
    print(f"❌ Неожиданная ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
