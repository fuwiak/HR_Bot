"""
Интеграция с Qdrant векторной базой данных
"""
import logging

log = logging.getLogger(__name__)

# Попытка импорта Qdrant модуля
try:
    from services.rag.qdrant_helper import search_service, index_services
    QDRANT_AVAILABLE = True
    log.info("✅ Qdrant модуль загружен")
except ImportError as e:
    QDRANT_AVAILABLE = False
    log.warning(f"⚠️ Qdrant модуль не доступен: {e}")
    def search_service(query: str, limit: int = 3):
        return []
    def index_services(services):
        return False
    def refresh_index():
        return False
