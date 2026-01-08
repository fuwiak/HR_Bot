"""
Qdrant векторная база данных для RAG (Retrieval-Augmented Generation)
Используется для семантического поиска по базе знаний консультанта
Эмбеддинги генерируются через OpenRouter API (qwen/qwen3-embedding-8b) - поддерживает русский и другие языки
"""
import os
import json
import logging
import asyncio
import sys
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
import hashlib
import aiohttp

# Добавляем корневую директорию проекта в sys.path для импорта config
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Импортируем config loader
from config import load_config

# Получаем логгер, но не используем до настройки логирования в основном приложении
def get_logger():
    """Получить логгер, инициализируя его если нужно"""
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        # Если логирование еще не настроено, настраиваем базовую конфигурацию
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    return logger

log = get_logger()

# Попытка импорта Qdrant
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    log.warning("⚠️ Qdrant библиотеки не установлены. Установите: pip install qdrant-client")

# Конфигурация для эмбеддингов из config.yaml
_llm_config = load_config("llm")
_embeddings_config = _llm_config.get("llm", {}).get("embeddings", {})

OPENROUTER_API_KEY = _embeddings_config.get("api_key") or os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_API_KEY = OPENROUTER_API_KEY or OPENAI_API_KEY  # Приоритет OpenRouter

# ВАЖНО: Коллекция в Qdrant создана с размерностью из конфига
# Поэтому всегда используем модель с этой размерностью или дополняем вектор
TARGET_DIMENSION = _qdrant_settings.get("target_dimension", 1536)  # Размерность коллекции в Qdrant

# Определяем URL и модель из конфига
EMBEDDING_API_URL = _embeddings_config.get("api_url") or os.getenv("EMBEDDING_API_URL", "https://openrouter.ai/api/v1/embeddings")
EMBEDDING_MODEL = _embeddings_config.get("model") or os.getenv("EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
EMBEDDING_DIMENSION = _embeddings_config.get("dimension") or int(os.getenv("EMBEDDING_DIMENSION", str(TARGET_DIMENSION)))

if OPENROUTER_API_KEY:
    log.info(f"🔧 Используется OpenRouter (модель: {EMBEDDING_MODEL})")
    log.info(f"🔧 Вектора будут дополнены до {TARGET_DIMENSION} для совместимости с Qdrant")
elif OPENAI_API_KEY:
    log.info(f"🔧 Используется OpenAI API для эмбеддингов (модель: {EMBEDDING_MODEL}, размерность: {EMBEDDING_DIMENSION})")
else:
    log.warning(f"⚠️ API ключ для эмбеддингов не установлен")

# Конфигурация Qdrant из config.yaml
from config import load_config

_qdrant_config = load_config("qdrant")
_qdrant_settings = _qdrant_config.get("qdrant", {})

# Railway Qdrant сервис
RAILWAY_QDRANT_HOST = _qdrant_settings.get("host") or os.getenv("QDRANT_HOST")
RAILWAY_QDRANT_PORT = _qdrant_settings.get("port") or os.getenv("QDRANT_PORT", "6333")
RAILWAY_QDRANT_URL = None

# Проверяем Railway Qdrant сервис
if RAILWAY_QDRANT_HOST:
    # Railway предоставляет внутренний домен для сервисов
    RAILWAY_QDRANT_URL = f"http://{RAILWAY_QDRANT_HOST}:{RAILWAY_QDRANT_PORT}"
    log.info(f"🔧 Обнаружен Railway Qdrant сервис: {RAILWAY_QDRANT_URL}")
else:
    # Локальный сервер для разработки
    RAILWAY_QDRANT_URL = _qdrant_settings.get("local_url") or os.getenv("QDRANT_URL", "http://localhost:6333")
    log.info(f"⚠️ QDRANT_HOST не установлен, используется локальный Qdrant: {RAILWAY_QDRANT_URL}")

# Используем только Railway Qdrant
QDRANT_URL = RAILWAY_QDRANT_URL
log.info(f"✅ Используется Qdrant: {QDRANT_URL}")

COLLECTION_NAME = _qdrant_settings.get("collection_name", "hr2137_bot_knowledge_base")

# Глобальные переменные
_qdrant_client = None
_collection_initialized = False
_embedding_dimension = EMBEDDING_DIMENSION

def get_qdrant_client():
    """Получить клиент Qdrant"""
    global _qdrant_client
    
    if not QDRANT_AVAILABLE:
        return None
    
    if _qdrant_client is not None:
        return _qdrant_client
    
    try:
        # Создаем клиент для Railway Qdrant (без API ключа, внутренняя сеть)
        _qdrant_client = QdrantClient(url=QDRANT_URL)
        log.info(f"🔗 Подключение к Railway Qdrant: {QDRANT_URL}")
        
        # Проверяем подключение
        _qdrant_client.get_collections()
        log.info(f"✅ Qdrant клиент успешно подключен: {QDRANT_URL}")
        log.info("✅ Используется Railway Qdrant (основная векторная база для RAG)")
        
        return _qdrant_client
    except Exception as e:
        log.error(f"❌ Ошибка подключения к Qdrant ({QDRANT_URL}): {e}")
        
        if RAILWAY_QDRANT_HOST:
            log.error(f"❌ Проверьте Railway Qdrant сервис:")
            log.error(f"   - Убедитесь что Qdrant сервис запущен в Railway")
            log.error(f"   - Проверьте переменную QDRANT_HOST в HR_Bot сервисе")
            log.error(f"   - QDRANT_HOST должен указывать на private domain Qdrant сервиса")
            log.error(f"   - QDRANT_PORT должен быть установлен (по умолчанию 6333)")
        else:
            log.error(f"❌ Для локальной разработки:")
            log.error(f"   - Запустите: docker run -p 6333:6333 qdrant/qdrant")
            log.error(f"   - Или установите QDRANT_HOST для Railway Qdrant сервиса")
        
        return None

async def generate_embedding_async(text: str) -> Optional[List[float]]:
    """
    Генерирует эмбеддинг для текста через OpenAI API (асинхронно)
    
    Args:
        text: Текст для генерации эмбеддинга
    
    Returns:
        Список чисел (эмбеддинг) или None при ошибке
    """
    if not EMBEDDING_API_KEY:
        log.error("❌ OPENAI_API_KEY или OPENROUTER_API_KEY не установлен для эмбеддингов")
        return None
    
    url = EMBEDDING_API_URL
    headers = {
        "Authorization": f"Bearer {EMBEDDING_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Если используем OpenRouter, добавляем заголовки
    if "openrouter" in url.lower():
        app_url = os.getenv("APP_URL", "https://github.com/HR2137_bot").strip()
        headers["HTTP-Referer"] = app_url
        headers["X-Title"] = "HR2137_bot"
    
    data = {
        "model": EMBEDDING_MODEL,
        "input": text[:8000]  # Ограничение для API
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ Ошибка API эмбеддингов {response.status}: {error_text}")
                    return None
                
                result = await response.json()
                if "data" in result and len(result["data"]) > 0:
                    embedding = result["data"][0]["embedding"]
                    embedding_size = len(embedding)
                    
                    # КРИТИЧНО: Всегда приводим к целевой размерности
                    if embedding_size != _embedding_dimension:
                        log.warning(f"⚠️ Размерность эмбеддинга ({embedding_size}) != целевой ({_embedding_dimension})")
                        if embedding_size > _embedding_dimension:
                            # Обрезаем до нужной размерности
                            embedding = embedding[:_embedding_dimension]
                            log.info(f"✂️ Эмбеддинг обрезан: {embedding_size} → {_embedding_dimension}")
                        else:
                            # Дополняем нулями если меньше
                            padding_size = _embedding_dimension - embedding_size
                            embedding = embedding + [0.0] * padding_size
                            log.info(f"📌 Эмбеддинг дополнен: {embedding_size} → {_embedding_dimension} (+{padding_size} нулей)")
                    else:
                        log.debug(f"✅ Эмбеддинг сгенерирован (размерность: {embedding_size})")
                    
                    # Финальная проверка
                    if len(embedding) != _embedding_dimension:
                        log.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: размерность {len(embedding)} != {_embedding_dimension}")
                        return None
                    
                    return embedding
                else:
                    log.error(f"❌ Неожиданный формат ответа от API: {result}")
                    return None
    except asyncio.TimeoutError:
        log.error("❌ Таймаут при генерации эмбеддинга")
        return None
    except Exception as e:
        log.error(f"❌ Ошибка генерации эмбеддинга: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Генерирует эмбеддинг для текста через OpenAI API (синхронная обертка)
    
    Args:
        text: Текст для генерации эмбеддинга
    
    Returns:
        Список чисел (эмбеддинг) или None при ошибке
    """
    try:
        # Пытаемся использовать существующий event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Если loop уже запущен, создаем новый в потоке
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, generate_embedding_async(text))
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(generate_embedding_async(text))
        except RuntimeError:
            # Нет event loop, создаем новый
            return asyncio.run(generate_embedding_async(text))
    except Exception as e:
        log.error(f"❌ Ошибка синхронной обертки: {e}")
        return None

def ensure_collection():
    """Создать коллекцию в Qdrant если её нет"""
    global _collection_initialized, _embedding_dimension
    
    client = get_qdrant_client()
    if not client:
        return False
    
    try:
        # Проверяем, существует ли коллекция
        collections = client.get_collections()
        collection_exists = any(col.name == COLLECTION_NAME for col in collections.collections)
        
        if not collection_exists:
            # Создаем коллекцию с фиксированной размерностью
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=_embedding_dimension, distance=Distance.COSINE),
            )
            log.info(f"✅ Создана коллекция '{COLLECTION_NAME}' в Qdrant (размерность: {_embedding_dimension})")
        else:
            log.debug(f"ℹ️ Коллекция '{COLLECTION_NAME}' уже существует")
        
        _collection_initialized = True
        return True
    except Exception as e:
        # Проверяем, если это ошибка о том, что коллекция уже существует - это нормально
        error_str = str(e)
        if "already exists" in error_str or "409" in error_str or "Conflict" in error_str:
            log.debug(f"ℹ️ Коллекция '{COLLECTION_NAME}' уже существует (это нормально)")
            _collection_initialized = True
            return True
        log.error(f"❌ Ошибка создания коллекции в Qdrant: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return False

def generate_service_id(service: Dict) -> str:
    """Генерирует уникальный ID для услуги на основе её данных"""
    service_str = f"{service.get('title', '')}_{service.get('master', '')}_{service.get('price', 0)}"
    return hashlib.md5(service_str.encode()).hexdigest()

def index_services(services: List[Dict]) -> bool:
    """
    Индексировать услуги в Qdrant (старая функция, оставлена для обратной совместимости)
    В новой версии эта функция будет использоваться для индексации документов базы знаний
    """
    """Индексировать услуги в Qdrant"""
    if not QDRANT_AVAILABLE:
        log.warning("⚠️ Qdrant библиотеки не установлены. Установите: pip install qdrant-client")
        return False
    
    client = get_qdrant_client()
    
    if not client:
        log.error(f"❌ Qdrant клиент не доступен. Проверьте подключение к {QDRANT_URL}")
        log.error(f"❌ Запустите Qdrant: docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant")
        return False
    
    # Проверяем доступность API эмбеддингов
    if not EMBEDDING_API_KEY:
        log.error("❌ API ключ для эмбеддингов не установлен. Установите OPENAI_API_KEY или OPENROUTER_API_KEY")
        return False
    
    if not ensure_collection():
        log.error("❌ Не удалось создать коллекцию")
        return False
    
    try:
        points = []
        
        for service in services:
            # Создаем текстовое представление услуги для поиска
            service_text = f"{service.get('title', '')} {service.get('master', '')} {service.get('price_str', '')} {service.get('duration', 0)}"
            
            # Генерируем эмбеддинг через API
            embedding = generate_embedding(service_text)
            if embedding is None:
                log.warning(f"⚠️ Не удалось сгенерировать эмбеддинг для услуги: {service.get('title', '')}")
                continue
            
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
                "indexed_at": datetime.now().isoformat(),
                "source_type": "service"  # Маркер для фильтрации услуг
            }
            
            # Генерируем ID
            service_id = generate_service_id(service)
            
            points.append(PointStruct(
                id=int(service_id[:8], 16),  # Конвертируем hex в int для Qdrant
                vector=embedding,
                payload=payload
            ))
        
        # Проверяем, что есть точки для вставки
        if not points:
            log.warning("⚠️ Нет точек для индексации (все эмбеддинги не удалось сгенерировать)")
            return False
        
        # Удаляем старые данные и вставляем новые
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception as e:
            log.debug(f"ℹ️ Коллекция не существовала или уже удалена: {e}")
        
        if not ensure_collection():
            log.error("❌ Не удалось создать/проверить коллекцию")
            return False
        
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

def search_service(query: str, limit: Optional[int] = None) -> List[Dict]:
    """
    Поиск в базе знаний по семантическому запросу в Qdrant
    (обновлено для работы с базой знаний консультанта)
    """
    # Используем дефолтный limit из конфига если не указан
    if limit is None:
        limit = _qdrant_settings.get("default_limit", 3)
    
    client = get_qdrant_client()
    
    if not client:
        log.warning("⚠️ Qdrant недоступен, используем обычный поиск")
        return []
    
    try:
        # Проверяем, что коллекция существует
        collections = client.get_collections()
        collection_exists = any(col.name == COLLECTION_NAME for col in collections.collections)
        if not collection_exists:
            log.warning(f"⚠️ Коллекция '{COLLECTION_NAME}' не существует в Qdrant")
            return []
        
        # Генерируем эмбеддинг для запроса через API
        query_embedding = generate_embedding(query)
        if query_embedding is None:
            log.warning("⚠️ Не удалось сгенерировать эмбеддинг для запроса")
            return []
        
        # Ищем в Qdrant - используем правильный метод query_points
        # Фильтруем только услуги (source_type="service" или есть поле id)
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        # Фильтр: только услуги (source_type="service")
        try:
            service_filter = Filter(
                must=[
                    FieldCondition(
                        key="source_type",
                        match=MatchValue(value="service")
                    )
                ]
            )
            
            # Ищем с фильтром
            search_results = client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_embedding,
                limit=limit * 2,  # Берем больше, чтобы после фильтрации осталось достаточно
                query_filter=service_filter
            )
        except Exception as e:
            # Если фильтр не работает (старые данные без source_type), ищем без фильтра
            log.debug(f"⚠️ Фильтр не применился, используем поиск без фильтра: {e}")
            search_results = client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_embedding,
                limit=limit * 2
            )
        
        results = []
        # QueryResponse содержит points
        points_list = search_results.points if hasattr(search_results, 'points') else []
        
        for result in points_list:
            # Преобразуем payload обратно в формат услуги
            payload = result.payload if hasattr(result, 'payload') else {}
            score = result.score if hasattr(result, 'score') else 0.0
            
            # Пропускаем документы (если нет id или title пустой)
            if not payload.get("id") and not payload.get("title"):
                continue
            
            # Пропускаем документы базы знаний (если есть file_name или text, но нет source_type="service")
            if payload.get("file_name") or payload.get("text"):
                if payload.get("source_type") != "service":
                    continue
            
            service = {
                "id": payload.get("id", 0),
                "title": payload.get("title", ""),
                "price": payload.get("price", 0),
                "price_str": payload.get("price_str", ""),
                "duration": payload.get("duration", 0),
                "master": payload.get("master", ""),
                "master1": payload.get("master1", ""),
                "master2": payload.get("master2", ""),
                "type": payload.get("type", ""),
                "additional_services": payload.get("additional_services", ""),
                "score": score  # Схожесть (0-1)
            }
            results.append(service)
        
        # Ограничиваем количество результатов
        results = results[:limit]
        
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

# ===================== ASYNC FUNCTIONS FOR DEMONSTRATION =====================

async def search_with_preview(query: str, limit: int = 5) -> Dict:
    """
    Поиск в RAG базе с предпросмотром результатов (для демонстрации)
    
    Args:
        query: Поисковый запрос
        limit: Количество результатов
    
    Returns:
        Словарь с результатами поиска и метаданными
    """
    results = await asyncio.to_thread(search_service, query, limit)
    
    return {
        "query": query,
        "total_results": len(results),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }

async def get_collection_stats() -> Dict:
    """
    Получить статистику коллекции в Qdrant (для демонстрации)
    
    Returns:
        Словарь со статистикой базы знаний
    """
    client = get_qdrant_client()
    if not client:
        return {
            "error": "Qdrant клиент недоступен",
            "collection_name": COLLECTION_NAME
        }
    
    try:
        collections = client.get_collections()
        collection_exists = any(col.name == COLLECTION_NAME for col in collections.collections)
        
        if not collection_exists:
            return {
                "collection_name": COLLECTION_NAME,
                "exists": False,
                "points_count": 0,
                "vector_size": _embedding_dimension
            }
        
        # Получаем информацию о коллекции
        collection_info = client.get_collection(COLLECTION_NAME)
        points_count = collection_info.points_count if hasattr(collection_info, 'points_count') else 0
        
        return {
            "collection_name": COLLECTION_NAME,
            "exists": True,
            "points_count": points_count,
            "vector_size": _embedding_dimension,
            "distance": "COSINE",
            "status": "ready"
        }
    except Exception as e:
        log.error(f"❌ Ошибка получения статистики коллекции: {e}")
        return {
            "error": str(e),
            "collection_name": COLLECTION_NAME
        }

async def list_documents(limit: int = 50) -> List[Dict]:
    """
    Получить список документов из базы знаний (для демонстрации)
    
    Args:
        limit: Максимальное количество документов
    
    Returns:
        Список документов с метаданными
    """
    client = get_qdrant_client()
    if not client:
        return []
    
    try:
        collections = client.get_collections()
        collection_exists = any(col.name == COLLECTION_NAME for col in collections.collections)
        
        if not collection_exists:
            return []
        
        # Получаем точки из коллекции (scroll)
        scroll_result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        
        documents = []
        points = scroll_result[0] if isinstance(scroll_result, tuple) else []
        
        for point in points:
            payload = point.payload if hasattr(point, 'payload') else {}
            documents.append({
                "id": str(point.id) if hasattr(point, 'id') else None,
                "title": payload.get("title", payload.get("document_title", "Без названия")),
                "category": payload.get("category", payload.get("type", "Неизвестно")),
                "snippet": payload.get("text", payload.get("content", ""))[:200] + "..." if len(payload.get("text", payload.get("content", ""))) > 200 else payload.get("text", payload.get("content", "")),
                "indexed_at": payload.get("indexed_at", "Неизвестно")
            })
        
        return documents
    except Exception as e:
        log.error(f"❌ Ошибка получения списка документов: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return []


def index_message_to_qdrant(text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """
    Индексировать сообщение Telegram в Qdrant для RAG
    
    Args:
        text: Текст сообщения
        metadata: Метаданные сообщения (user_id, message_id, etc.)
    
    Returns:
        True если успешно, False при ошибке
    """
    if not text or not text.strip():
        return False
    
    try:
        # Генерируем эмбеддинг
        embedding = generate_embedding(text)
        if not embedding:
            log.warning("⚠️ Не удалось сгенерировать эмбеддинг для сообщения")
            return False
        
        # Получаем клиент Qdrant
        client = get_qdrant_client()
        if not client:
            log.warning("⚠️ Qdrant клиент недоступен")
            return False
        
        # Убеждаемся что коллекция существует
        if not ensure_collection():
            log.error("❌ Не удалось создать/проверить коллекцию")
            return False
        
        # Подготавливаем метаданные
        payload = {
            "source": "telegram_message",
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            payload.update(metadata)
        
        # Генерируем ID для точки
        text_hash = hashlib.md5(f"{text}{metadata.get('message_id', '') if metadata else ''}".encode()).hexdigest()
        point_id = int(text_hash[:8], 16)
        
        # Добавляем точку в Qdrant
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            ]
        )
        
        log.info(f"✅ Сообщение индексировано в Qdrant (point_id={point_id})")
        return True
        
    except Exception as e:
        log.error(f"❌ Ошибка индексации сообщения в Qdrant: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return False

