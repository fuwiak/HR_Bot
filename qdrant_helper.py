"""
Qdrant векторная база данных для точного поиска услуг из Google Sheets
Используется для семантического поиска услуг, чтобы избежать выдумывания цен AI
"""
import os
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import hashlib

log = logging.getLogger()

# Попытка импорта Qdrant
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from sentence_transformers import SentenceTransformer
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    log.warning("⚠️ Qdrant библиотеки не установлены. Установите: pip install qdrant-client sentence-transformers")

# Конфигурация
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION_NAME = "romanbot_services"

# Глобальные переменные
_qdrant_client = None
_embedding_model = None
_collection_initialized = False

def get_qdrant_client():
    """Получить клиент Qdrant"""
    global _qdrant_client
    
    if not QDRANT_AVAILABLE:
        return None
    
    if _qdrant_client is not None:
        return _qdrant_client
    
    try:
        if QDRANT_API_KEY:
            _qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        else:
            _qdrant_client = QdrantClient(url=QDRANT_URL)
        log.info(f"✅ Qdrant клиент успешно подключен: {QDRANT_URL}")
        return _qdrant_client
    except Exception as e:
        log.error(f"❌ Ошибка подключения к Qdrant: {e}")
        return None

def get_embedding_model():
    """Получить модель для эмбеддингов"""
    global _embedding_model
    
    if not QDRANT_AVAILABLE:
        return None
    
    if _embedding_model is not None:
        return _embedding_model
    
    try:
        # Используем русскоязычную модель для лучшего качества
        _embedding_model = SentenceTransformer('intfloat/multilingual-e5-base')
        log.info("✅ Модель для эмбеддингов загружена")
        return _embedding_model
    except Exception as e:
        log.error(f"❌ Ошибка загрузки модели эмбеддингов: {e}")
        return None

def ensure_collection():
    """Создать коллекцию в Qdrant если её нет"""
    global _collection_initialized
    
    client = get_qdrant_client()
    if not client:
        return False
    
    try:
        # Проверяем, существует ли коллекция
        collections = client.get_collections()
        collection_exists = any(col.name == COLLECTION_NAME for col in collections.collections)
        
        if not collection_exists:
            # Создаем коллекцию
            model = get_embedding_model()
            if not model:
                log.error("❌ Не удалось загрузить модель для определения размерности вектора")
                return False
            
            vector_size = model.get_sentence_embedding_dimension()
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            log.info(f"✅ Создана коллекция '{COLLECTION_NAME}' в Qdrant")
        
        _collection_initialized = True
        return True
    except Exception as e:
        log.error(f"❌ Ошибка создания коллекции в Qdrant: {e}")
        return False

def generate_service_id(service: Dict) -> str:
    """Генерирует уникальный ID для услуги на основе её данных"""
    service_str = f"{service.get('title', '')}_{service.get('master', '')}_{service.get('price', 0)}"
    return hashlib.md5(service_str.encode()).hexdigest()

def index_services(services: List[Dict]) -> bool:
    """Индексировать услуги в Qdrant"""
    client = get_qdrant_client()
    model = get_embedding_model()
    
    if not client or not model:
        log.error("❌ Qdrant клиент или модель не доступны")
        return False
    
    if not ensure_collection():
        log.error("❌ Не удалось создать коллекцию")
        return False
    
    try:
        points = []
        
        for service in services:
            # Создаем текстовое представление услуги для поиска
            service_text = f"{service.get('title', '')} {service.get('master', '')} {service.get('price_str', '')} {service.get('duration', 0)}"
            
            # Генерируем эмбеддинг
            embedding = model.encode(service_text, normalize_embeddings=True).tolist()
            
            # Создаем payload с полной информацией об услуге
            payload = {
                "id": service.get("id"),
                "title": service.get("title", ""),
                "price": service.get("price", 0),
                "price_str": service.get("price_str", ""),
                "duration": service.get("duration", 0),
                "master": service.get("master", ""),
                "master1": service.get("master1", ""),
                "master2": service.get("master2", ""),
                "type": service.get("type", ""),
                "additional_services": service.get("additional_services", ""),
                "row_number": service.get("row_number", 0),
                "indexed_at": datetime.now().isoformat()
            }
            
            # Генерируем ID
            service_id = generate_service_id(service)
            
            points.append(PointStruct(
                id=int(service_id[:8], 16),  # Конвертируем hex в int для Qdrant
                vector=embedding,
                payload=payload
            ))
        
        # Удаляем старые данные и вставляем новые
        client.delete_collection(COLLECTION_NAME)
        ensure_collection()
        
        # Вставляем новые точки
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        
        log.info(f"✅ Индексировано {len(points)} услуг в Qdrant")
        return True
        
    except Exception as e:
        log.error(f"❌ Ошибка индексации услуг в Qdrant: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return False

def search_service(query: str, limit: int = 3) -> List[Dict]:
    """Поиск услуги по семантическому запросу в Qdrant"""
    client = get_qdrant_client()
    model = get_embedding_model()
    
    if not client or not model:
        log.warning("⚠️ Qdrant недоступен, используем обычный поиск")
        return []
    
    try:
        # Генерируем эмбеддинг для запроса
        query_embedding = model.encode(query, normalize_embeddings=True).tolist()
        
        # Ищем в Qdrant
        search_results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=limit
        )
        
        results = []
        for result in search_results:
            # Преобразуем payload обратно в формат услуги
            payload = result.payload
            service = {
                "id": payload.get("id"),
                "title": payload.get("title"),
                "price": payload.get("price", 0),
                "price_str": payload.get("price_str", ""),
                "duration": payload.get("duration", 0),
                "master": payload.get("master", ""),
                "master1": payload.get("master1", ""),
                "master2": payload.get("master2", ""),
                "type": payload.get("type", ""),
                "additional_services": payload.get("additional_services", ""),
                "score": result.score  # Схожесть (0-1)
            }
            results.append(service)
        
        if results:
            log.info(f"🔍 Найдено {len(results)} услуг в Qdrant для запроса '{query}'")
            for r in results:
                log.info(f"  📋 {r.get('title')} - {r.get('price_str') or r.get('price')}₽ (score: {r.get('score', 0):.3f})")
        
        return results
        
    except Exception as e:
        log.error(f"❌ Ошибка поиска в Qdrant: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return []

def refresh_index():
    """Обновить индекс услуг из Google Sheets"""
    try:
        from google_sheets_helper import get_services
        services = get_services()
        if services:
            return index_services(services)
        return False
    except Exception as e:
        log.error(f"❌ Ошибка обновления индекса: {e}")
        return False

