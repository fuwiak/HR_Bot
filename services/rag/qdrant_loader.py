"""
Модуль для загрузки документов в Qdrant векторную БД.
Поддерживает чанкинг, индексацию и фильтрацию по whitelist.
"""

import os
import logging
import asyncio
import hashlib
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    CollectionStatus, Filter, FieldCondition, MatchValue
)
# Используем легкую реализацию text splitter без langchain
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    # Fallback на легкую реализацию без зависимостей
    try:
        from services.helpers.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        # Если и это не работает, пробуем добавить путь
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from services.helpers.text_splitter import RecursiveCharacterTextSplitter
# Используем API эмбеддинги через qdrant_helper (OpenAI text-embedding-3-small)
# from langchain_huggingface import HuggingFaceEmbeddings
import uuid
import re
from collections import defaultdict

from whitelist import WhitelistManager

# Загружаем переменные окружения из .env файла
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent.parent
    load_dotenv(project_root / ".env")
except ImportError:
    pass  # python-dotenv не установлен, используем только системные переменные окружения

logger = logging.getLogger(__name__)

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank-bm25 не установлен. BM25 поиск недоступен. Установите: pip install rank-bm25")


class QdrantLoader:
    """Класс для загрузки и управления документами в Qdrant (Singleton)"""
    
    _instance: Optional['QdrantLoader'] = None
    _lock = None
    
    def __new__(
        cls,
        collection_name: str = "hr2137_bot_knowledge_base",
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        force_new: bool = False
    ):
        """
        Singleton паттерн - возвращает существующий экземпляр или создает новый.
        
        Args:
            force_new: Если True, создает новый экземпляр (для тестирования)
        """
        if cls._instance is None or force_new:
            if cls._lock is None:
                import threading
                cls._lock = threading.Lock()
            
            with cls._lock:
                if cls._instance is None or force_new:
                    instance = super(QdrantLoader, cls).__new__(cls)
                    instance._initialized = False
                    if not force_new:
                        cls._instance = instance
                    return instance
        return cls._instance
    
    def __init__(
        self,
        collection_name: str = "hr2137_bot_knowledge_base",
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        force_new: bool = False
    ):
        # Если уже инициализирован - не инициализируем снова
        if hasattr(self, '_initialized') and self._initialized:
            return
        self.collection_name = collection_name
        
        # Определяем URL Qdrant (та же логика, что в qdrant_helper.py)
        # Приоритет: 1) QDRANT_HOST, 2) RAILWAY_SERVICE_QDRANT_URL, 3) переданный qdrant_url, 4) QDRANT_URL, 5) private domain, 6) localhost
        qdrant_host = os.getenv("QDRANT_HOST")
        if qdrant_host:
                # Приоритет 2: QDRANT_HOST из конфига или переменных окружения
                # Определяем, является ли домен публичным (Railway public domain)
                is_public_domain = (
                    ".up.railway.app" in qdrant_host or
                    ".railway.app" in qdrant_host or
                    qdrant_host.startswith("https://")
                )
                
                if is_public_domain:
                    # Публичный домен Railway - используем HTTPS без порта
                    if qdrant_host.startswith("https://"):
                        self.qdrant_url = qdrant_host
                    elif qdrant_host.startswith("http://"):
                        self.qdrant_url = qdrant_host.replace("http://", "https://")
                    else:
                        self.qdrant_url = f"https://{qdrant_host}"
                    logger.info(f"🔧 Используется публичный Railway Qdrant: {self.qdrant_url}")
                else:
                    # Приватный домен Railway - используем HTTP с портом
                    qdrant_port = os.getenv("QDRANT_PORT", "6333")
                    self.qdrant_url = f"http://{qdrant_host}:{qdrant_port}"
                    logger.info(f"🔧 Используется приватный Railway Qdrant: {self.qdrant_url}")
        # Приоритет 2: RAILWAY_SERVICE_QDRANT_URL (автоматическая переменная Railway, если QDRANT_HOST не установлен)
        elif railway_service_qdrant_url := os.getenv("RAILWAY_SERVICE_QDRANT_URL"):
            # Автоматическая переменная Railway
            if railway_service_qdrant_url.startswith("https://"):
                self.qdrant_url = railway_service_qdrant_url
            else:
                self.qdrant_url = f"https://{railway_service_qdrant_url}"
            logger.info(f"🔧 Используется Railway Qdrant из RAILWAY_SERVICE_QDRANT_URL: {self.qdrant_url}")
        elif os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"):
                # Приоритет 3: В Railway, но QDRANT_HOST не установлен - пробуем private domain
                qdrant_port = os.getenv("QDRANT_PORT", "6333")
                self.qdrant_url = f"http://qdrant.railway.internal:{qdrant_port}"
                logger.info(f"⚠️ QDRANT_HOST не установлен, пробуем Railway private domain: {self.qdrant_url}")
        else:
                # Приоритет 4: Локальная разработка
                self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
                if self.qdrant_url == "http://localhost:6333":
                    logger.info(f"🔧 Используется локальный Qdrant: {self.qdrant_url}")
                else:
                    logger.info(f"🔧 Используется Qdrant URL: {self.qdrant_url}")
        
        # API ключ больше не используется для Railway Qdrant
        self.qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY", "")
        
        # Создаем клиент Qdrant
        is_public = self.qdrant_url.startswith("https://")
        timeout_seconds = 30.0 if is_public else 10.0
        
        client_kwargs = {"url": self.qdrant_url, "timeout": timeout_seconds}
        # API ключ используется только для старых Qdrant Cloud подключений
        if self.qdrant_api_key and not qdrant_host:
            client_kwargs["api_key"] = self.qdrant_api_key
            logger.info(f"Используется Qdrant Cloud с API ключом: {self.qdrant_url}")
        
        self.client = QdrantClient(**client_kwargs)
        
        # Инициализация embeddings через API (как в qdrant_helper)
        # Используем асинхронную функцию напрямую, как в Telegram боте
        try:
            from services.rag.qdrant_helper import generate_embedding_async, EMBEDDING_DIMENSION
            self._qdrant_embedding_async = generate_embedding_async
            # Используем размерность из конфигурации
            self.embedding_dim = EMBEDDING_DIMENSION
            logger.info(f"Используется API для эмбеддингов (размерность: {self.embedding_dim})")
        except ImportError:
            logger.error("Не удалось импортировать функции из qdrant_helper")
            self.embedding_dim = 1536
            self._qdrant_embedding_async = None
        
        # Инициализация text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Whitelist менеджер
        self.whitelist = WhitelistManager()
        
        # BM25 индекс (будет построен при необходимости)
        self.bm25_index: Optional[BM25Okapi] = None
        self.bm25_documents: List[List[str]] = []  # Токенизированные документы для BM25
        self.bm25_doc_map: Dict[int, Dict[str, Any]] = {}  # Маппинг индекса BM25 к документам Qdrant
        
        # Флаг необходимости перестроения BM25 индекса
        self._bm25_needs_rebuild = True
        
        # Создаем коллекцию если не существует
        self._ensure_collection()
        
        # Помечаем как инициализированный (для singleton)
        self._initialized = True
    
    def _ensure_collection(self) -> None:
        """Создает коллекцию если она не существует"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection {self.collection_name} created")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring collection: {str(e)}")
            raise
    
    def load_document(
        self,
        text: str,
        metadata: Dict[str, Any],
        filter_by_whitelist: bool = True
    ) -> int:
        """
        Загружает документ в Qdrant.
        
        Args:
            text: Текст документа
            metadata: Метаданные (должен содержать source_url)
            filter_by_whitelist: Фильтровать по whitelist
        
        Returns:
            Количество загруженных чанков
        """
        source_url = metadata.get("source_url") or metadata.get("url", "")
        
        # Проверка whitelist
        if filter_by_whitelist and not self.whitelist.is_allowed(source_url):
            logger.warning(f"Document filtered by whitelist: {source_url}")
            return 0
        
        # Разбиваем на чанки
        chunks = self.text_splitter.split_text(text)
        logger.info(f"Split document into {len(chunks)} chunks")
        
        # Генерируем embeddings через API (асинхронно, как в Telegram боте)
        if self._qdrant_embedding_async is None:
            logger.error("Embedding функция не доступна")
            return 0
        
        embeddings_data = []
        
        # Генерируем эмбеддинги асинхронно (как в Telegram боте)
        async def generate_all_embeddings():
            tasks = [self._qdrant_embedding_async(chunk) for chunk in chunks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        # Запускаем асинхронную генерацию
        try:
            # Проверяем, есть ли уже запущенный event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Если loop уже запущен, создаем новый в потоке
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, generate_all_embeddings())
                        embeddings_results = future.result(timeout=300)  # 5 минут таймаут
                else:
                    embeddings_results = loop.run_until_complete(generate_all_embeddings())
            except RuntimeError:
                # Нет event loop, создаем новый
                embeddings_results = asyncio.run(generate_all_embeddings())
            
            # Обрабатываем результаты
            for i, (chunk, embedding_result) in enumerate(zip(chunks, embeddings_results)):
                if isinstance(embedding_result, Exception):
                    logger.warning(f"Не удалось сгенерировать эмбеддинг для чанка {i}: {embedding_result}")
                elif embedding_result:
                    embeddings_data.append((i, chunk, embedding_result))
                else:
                    logger.warning(f"Не удалось сгенерировать эмбеддинг для чанка {i}")
        except Exception as e:
            logger.error(f"Ошибка при генерации эмбеддингов: {e}")
            return 0
        
        if not embeddings_data:
            logger.error("Не удалось сгенерировать ни одного эмбеддинга")
            return 0
        
        # Подготавливаем точки для вставки
        points = []
        for orig_idx, chunk, embedding in embeddings_data:
            # Используем хеш от текста чанка для стабильного ID
            point_id_str = f"{source_url}_{i}_{hashlib.md5(chunk.encode()).hexdigest()}"
            point_id = int(hashlib.md5(point_id_str.encode()).hexdigest()[:8], 16)
            point_metadata = {
                **metadata,
                "chunk_index": orig_idx,
                "text": chunk,
                "source_url": source_url
            }
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=point_metadata
                )
            )
        
        # Вставляем в Qdrant
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Inserted {len(points)} points into {self.collection_name}")
            
            # Помечаем BM25 индекс для перестроения
            self._bm25_needs_rebuild = True
            
            return len(points)
        except Exception as e:
            logger.error(f"Error inserting points: {str(e)}")
            raise
    
    def load_from_file(
        self,
        file_path: str,
        source_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Загружает документ из файла.
        Поддерживает текстовые файлы и PDF.
        
        Args:
            file_path: Путь к файлу
            source_url: URL источника
            metadata: Дополнительные метаданные
        
        Returns:
            Количество загруженных чанков
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Определяем тип файла по расширению
        file_ext = file_path.suffix.lower()
        
        if file_ext == '.pdf':
            # Читаем PDF файл
            try:
                import PyPDF2
            except ImportError:
                raise ImportError("PyPDF2 не установлен. Установите: pip install PyPDF2")
            
            text = ""
            try:
                with open(file_path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page_num, page in enumerate(pdf_reader.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text += f"\n\n--- Страница {page_num + 1} ---\n\n"
                                text += page_text
                        except Exception as e:
                            logger.warning(f"Ошибка при чтении страницы {page_num + 1}: {str(e)}")
                            continue
            except Exception as e:
                logger.error(f"Ошибка при чтении PDF файла: {str(e)}")
                raise
        else:
            # Читаем текстовый файл
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                # Пробуем другие кодировки
                for encoding in ['cp1251', 'latin-1', 'iso-8859-1']:
                    try:
                        with open(file_path, "r", encoding=encoding) as f:
                            text = f.read()
                            break
                    except (UnicodeDecodeError, LookupError):
                        continue
                else:
                    raise ValueError(f"Не удалось декодировать файл {file_path} с доступными кодировками")
        
        if not text.strip():
            logger.warning(f"Файл {file_path} пуст или не содержит текста")
            return 0
        
        doc_metadata = {
            "source_url": source_url,
            "file_name": file_path.name,
            "file_type": file_ext,
            **(metadata or {})
        }
        
        return self.load_document(text, doc_metadata)
    
    def _tokenize(self, text: str) -> List[str]:
        """Токенизация текста для BM25 (русский + английский)"""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        return words
    
    def _build_bm25_index(self) -> None:
        """Строит BM25 индекс из всех документов в Qdrant"""
        if not BM25_AVAILABLE:
            return
        
        try:
            logger.info("Building BM25 index from Qdrant documents...")
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            points = scroll_result[0]
            
            if not points:
                return
            
            self.bm25_documents = []
            self.bm25_doc_map = {}
            
            for idx, point in enumerate(points):
                text = point.payload.get("text", "")
                if not text:
                    continue
                tokens = self._tokenize(text)
                if tokens:
                    self.bm25_documents.append(tokens)
                    self.bm25_doc_map[idx] = {
                        "text": text,
                        "source_url": point.payload.get("source_url", ""),
                        "payload": point.payload
                    }
            
            if self.bm25_documents:
                self.bm25_index = BM25Okapi(self.bm25_documents)
                logger.info(f"BM25 index built with {len(self.bm25_documents)} documents")
                
        except Exception as e:
            logger.error(f"Error building BM25 index: {str(e)}")
            self.bm25_index = None
    
    def _bm25_search(self, query: str, top_k: int = 5, filter_by_whitelist: bool = True) -> List[Dict[str, Any]]:
        """Выполняет BM25 поиск"""
        if not BM25_AVAILABLE:
            return []
        
        if self._bm25_needs_rebuild or not self.bm25_index:
            self._build_bm25_index()
            self._bm25_needs_rebuild = False
        
        if not self.bm25_index:
            return []
        
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        scores = self.bm25_index.get_scores(query_tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k * 2]
        
        documents = []
        for idx in top_indices:
            if scores[idx] <= 0:
                continue
            doc_data = self.bm25_doc_map.get(idx)
            if not doc_data:
                continue
            
            if filter_by_whitelist:
                source_url = doc_data.get("source_url", "")
                if not self.whitelist.is_allowed(source_url):
                    continue
            
            import math
            normalized_score = 1 / (1 + math.exp(-scores[idx] / 10)) if scores[idx] > 0 else 0
            
            doc = {
                "text": doc_data.get("text", ""),
                "source_url": doc_data.get("source_url", ""),
                "score": normalized_score,
                "bm25_raw_score": float(scores[idx]),
                "search_method": "bm25",
                **{k: v for k, v in doc_data.get("payload", {}).items() 
                   if k not in ["text", "source_url"]}
            }
            documents.append(doc)
        
        return documents[:top_k]
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.7,
        filter_by_whitelist: bool = True,
        search_strategy: str = "hybrid",
        dense_weight: float = 0.4,
        bm25_weight: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Поиск с поддержкой BM25 и hybrid search.
        
        Args:
            query: Поисковый запрос
            top_k: Количество результатов
            score_threshold: Минимальный score
            filter_by_whitelist: Фильтровать по whitelist
            search_strategy: "dense", "bm25", или "hybrid"
            dense_weight: Вес для dense search (для hybrid)
            bm25_weight: Вес для BM25 search (для hybrid)
        """
        if search_strategy == "bm25":
            return self._bm25_search(query, top_k, filter_by_whitelist)
        
        # Dense search - генерируем эмбеддинг запроса
        if self._qdrant_embedding_async is None:
            logger.error("Embedding функция не доступна")
            return []
        
        # Генерируем эмбеддинг асинхронно
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self._qdrant_embedding_async(query))
                        query_embedding = future.result(timeout=30)
                else:
                    query_embedding = loop.run_until_complete(self._qdrant_embedding_async(query))
            except RuntimeError:
                query_embedding = asyncio.run(self._qdrant_embedding_async(query))
        except Exception as e:
            logger.error(f"Ошибка при генерации эмбеддинга для запроса: {e}")
            return []
        if not query_embedding:
            logger.error("Не удалось сгенерировать эмбеддинг запроса")
            return []
        search_filter = None
        if filter_by_whitelist:
            allowed_urls = self.whitelist.get_allowed_urls()
            if allowed_urls:
                conditions = [FieldCondition(key="source_url", match=MatchValue(value=url)) for url in allowed_urls]
                if conditions:
                    search_filter = Filter(must=[conditions[0]])
        
        dense_results = []
        try:
            # Используем query_points для совместимости с in-memory и remote Qdrant
            # Для in-memory используем простой вектор напрямую
            try:
                # Пробуем простой вектор (работает для in-memory и многих версий remote)
                query_points = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_embedding,  # Простой вектор
                    limit=top_k * 2 if search_strategy == "hybrid" else top_k,
                    score_threshold=score_threshold
                )
                
                # Фильтруем результаты по whitelist если нужно
                for point in query_points.points:
                    if point.score < score_threshold:
                        continue
                    
                    source_url = point.payload.get("source_url", "")
                    if filter_by_whitelist and not self.whitelist.is_allowed(source_url):
                        continue
                    
                    doc = {
                        "text": point.payload.get("text", ""),
                        "source_url": source_url,
                        "score": point.score,
                        "search_method": "dense",
                        **{k: v for k, v in point.payload.items() if k not in ["text", "source_url"]}
                    }
                    dense_results.append(doc)
                    
            except (TypeError, AttributeError, ValueError) as e:
                # Если прямой вектор не работает, логируем ошибку
                logger.error(f"Error in dense search with direct vector: {str(e)}")
                logger.warning("Falling back to empty results. Check Qdrant client configuration.")
                dense_results = []
        
        except Exception as e:
            logger.error(f"Error in dense search: {str(e)}")
        
        if filter_by_whitelist:
            dense_results = self.whitelist.filter_sources(dense_results)
        
        if search_strategy == "dense":
            return dense_results[:top_k]
        
        if search_strategy == "hybrid":
            return self._hybrid_search(query, dense_results, top_k, score_threshold, filter_by_whitelist, dense_weight, bm25_weight)
        
        return dense_results[:top_k]
    
    def _hybrid_search(
        self, query: str, dense_results: List[Dict[str, Any]], top_k: int,
        score_threshold: float, filter_by_whitelist: bool, dense_weight: float, bm25_weight: float
    ) -> List[Dict[str, Any]]:
        """Комбинирует результаты BM25 и Dense search"""
        bm25_results = self._bm25_search(query, top_k * 2, filter_by_whitelist)
        
        if not bm25_results:
            return dense_results[:top_k]
        
        def normalize_scores(results):
            if not results:
                return []
            scores = [r["score"] for r in results]
            max_score, min_score = max(scores) if scores else 1.0, min(scores) if scores else 0.0
            score_range = max_score - min_score if max_score != min_score else 1.0
            for r in results:
                r["normalized_score"] = (r["score"] - min_score) / score_range if score_range > 0 else 0.5
            return results
        
        dense_norm = normalize_scores(dense_results.copy())
        bm25_norm = normalize_scores(bm25_results.copy())
        combined_scores = {}
        
        for doc in dense_norm:
            text_key = doc["text"][:200]
            combined_scores[text_key] = {**doc, "hybrid_score": doc["normalized_score"] * dense_weight, "dense_score": doc["normalized_score"], "bm25_score": 0.0}
        
        for doc in bm25_norm:
            text_key = doc["text"][:200]
            bm25_norm_score = doc["normalized_score"]
            if text_key in combined_scores:
                combined_scores[text_key]["hybrid_score"] += bm25_norm_score * bm25_weight
                combined_scores[text_key]["bm25_score"] = bm25_norm_score
            else:
                combined_scores[text_key] = {**doc, "hybrid_score": bm25_norm_score * bm25_weight, "dense_score": 0.0, "bm25_score": bm25_norm_score}
        
        combined_list = sorted(combined_scores.values(), key=lambda x: x["hybrid_score"], reverse=True)
        filtered = [doc for doc in combined_list if doc["hybrid_score"] >= score_threshold]
        
        for doc in filtered:
            doc["score"] = doc["hybrid_score"]
            doc["search_method"] = "hybrid"
        
        return filtered[:top_k]
    
    def delete_collection(self) -> None:
        """Удаляет коллекцию"""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Collection {self.collection_name} deleted")
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Возвращает информацию о коллекции"""
        try:
            info = self.client.get_collection(self.collection_name)
            # Исправлено: используем только существующие атрибуты CollectionInfo
            result = {
                "name": self.collection_name,
                "points_count": getattr(info, 'points_count', 0),
                "status": str(getattr(info, 'status', 'unknown'))
            }
            
            # vectors_count может не существовать в некоторых версиях
            if hasattr(info, 'vectors_count'):
                result["vectors_count"] = info.vectors_count
            else:
                # Приблизительно равняется points_count для большинства случаев
                result["vectors_count"] = result["points_count"]
            
            return result
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {
                "name": self.collection_name,
                "points_count": 0,
                "vectors_count": 0,
                "status": "error"
            }

