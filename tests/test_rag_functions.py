"""
Тесты для RAG функций
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from services.rag.rag_chain import RAGChain


@pytest.mark.asyncio
async def test_rag_chain_query():
    """Тест выполнения RAG запроса"""
    
    with patch('services.rag.rag_chain.QdrantLoader') as mock_qdrant_class:
        mock_qdrant = Mock()
        mock_qdrant.search.return_value = [
            {"text": "Релевантный документ", "source_url": "doc1", "score": 0.9}
        ]
        mock_qdrant_class.return_value = mock_qdrant
        
        rag_chain = RAGChain()
        
        with patch.object(rag_chain, 'qdrant_loader', mock_qdrant):
            result = await rag_chain.query("Подбор персонала", use_rag=True, top_k=5)
            
            assert "answer" in result or "text" in result
            mock_qdrant.search.assert_called_once()


@pytest.mark.asyncio
async def test_rag_chain_query_no_rag():
    """Тест RAG запроса без использования RAG"""
    
    with patch('services.rag.rag_chain.QdrantLoader') as mock_qdrant_class:
        mock_qdrant = Mock()
        mock_qdrant_class.return_value = mock_qdrant
        
        rag_chain = RAGChain()
        
        with patch.object(rag_chain, 'qdrant_loader', mock_qdrant):
            result = await rag_chain.query("Вопрос", use_rag=False)
            
            # При use_rag=False поиск не должен вызываться
            mock_qdrant.search.assert_not_called()


@pytest.mark.asyncio
async def test_rag_chain_singleton():
    """Тест что RAGChain работает как singleton"""
    
    from services.agents.scenario_workflows import get_rag_chain
    
    chain1 = get_rag_chain()
    chain2 = get_rag_chain()
    
    # Оба вызова должны вернуть один и тот же экземпляр
    assert chain1 is chain2 or (chain1 is None and chain2 is None)


@pytest.mark.asyncio
async def test_rag_search_service():
    """Тест функции search_service для поиска услуг"""
    
    with patch('services.rag.qdrant_helper.get_qdrant_client') as mock_client, \
         patch('services.rag.qdrant_helper.generate_embedding') as mock_embedding:
        
        mock_client.return_value = Mock()
        mock_embedding.return_value = [0.1] * 384  # Мок вектора
        
        from services.rag.qdrant_helper import search_service
        
        # Мокируем query_points
        mock_points = Mock()
        mock_points.points = [
            Mock(
                score=0.9,
                payload={
                    "text": "Услуга подбора",
                    "title": "Подбор персонала",
                    "source_type": "service",
                    "price": "50000"
                }
            )
        ]
        
        with patch.object(mock_client.return_value, 'query_points', return_value=mock_points):
            results = search_service("подбор персонала", limit=5)
            
            assert isinstance(results, list)
            if len(results) > 0:
                assert "title" in results[0] or "text" in results[0]
