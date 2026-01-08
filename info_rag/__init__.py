"""
RAG (Retrieval-Augmented Generation) система

Модули:
- rag_chain: Основная RAG цепочка
- rag_evaluator: Оценка качества RAG
- qdrant_loader: Загрузка данных в Qdrant
- load_pdf: Загрузка PDF документов
- load_pricelist: Загрузка прайс-листа
- scraper: Веб-скрапер
"""

try:
    from .rag_chain import RAGChain
    RAG_CHAIN_AVAILABLE = True
except ImportError:
    RAG_CHAIN_AVAILABLE = False

try:
    from .rag_evaluator import RAGEvaluator
    RAG_EVALUATOR_AVAILABLE = True
except ImportError:
    RAG_EVALUATOR_AVAILABLE = False

try:
    from .qdrant_loader import QdrantLoader
    QDRANT_LOADER_AVAILABLE = True
except ImportError:
    QDRANT_LOADER_AVAILABLE = False

__all__ = [
    'RAGChain',
    'RAGEvaluator', 
    'QdrantLoader',
    'RAG_CHAIN_AVAILABLE',
    'RAG_EVALUATOR_AVAILABLE',
    'QDRANT_LOADER_AVAILABLE'
]
