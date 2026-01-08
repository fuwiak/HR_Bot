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
        
        # Проверяем подключение к Qdrant
        client = get_qdrant_client()
        if not client:
            log.error("❌ Не удалось подключиться к Qdrant")
            log.error("   Убедитесь, что Qdrant сервис запущен и доступен")
            return 1
        
        # Проверяем, существует ли коллекция перед созданием
        try:
            collections = client.get_collections()
            collection_exists = any(col.name == COLLECTION_NAME for col in collections.collections)
            
            if collection_exists:
                log.info(f"✅ Коллекция '{COLLECTION_NAME}' уже существует, пропускаем создание")
                return 0
        except Exception as e:
            log.warning(f"⚠️ Не удалось проверить существование коллекции: {e}")
            log.info("   Продолжаем попытку создания...")
        
        # Создаем коллекцию только если её нет
        if ensure_collection():
            log.info(f"✅ Коллекция '{COLLECTION_NAME}' готова к использованию")
            return 0
        else:
            log.error(f"❌ Не удалось создать/проверить коллекцию '{COLLECTION_NAME}'")
            return 1
    
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
