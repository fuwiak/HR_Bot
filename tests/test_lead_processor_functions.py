"""
Тесты для функций обработки лидов: КП, гипотезы, классификация, валидация
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from services.agents.lead_processor import (
    classify_request,
    validate_lead,
    generate_proposal,
    generate_hypothesis
)


@pytest.mark.asyncio
async def test_classify_request():
    """Тест классификации запроса по категориям"""
    
    with patch('services.agents.lead_processor.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        # Мок ответа LLM в формате JSON
        mock_llm.return_value = '{"category": "подбор", "confidence": 0.9, "keywords": ["рекрутинг", "персонал"]}'
        
        result = await classify_request("Нужен подбор HR-менеджера")
        
        assert result["category"] == "подбор"
        assert result["confidence"] == 0.9
        assert "keywords" in result
        mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_classify_request_fallback():
    """Тест классификации при ошибке LLM"""
    
    with patch('services.agents.lead_processor.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = Exception("LLM недоступен")
        
        result = await classify_request("Запрос")
        
        assert result["category"] == "другое"
        assert result["confidence"] == 0.0


@pytest.mark.asyncio
async def test_validate_lead():
    """Тест валидации лида"""
    
    with patch('services.agents.lead_processor.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = '{"score": 0.85, "status": "warm", "reason": "Четкое ТЗ", "criteria": {"clarity": 0.9, "budget": 0.8}}'
        
        result = await validate_lead("Нужен подбор персонала. Бюджет: 100000 руб.")
        
        assert result["score"] == 0.85
        assert result["status"] == "warm"
        assert "reason" in result
        mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_validate_lead_cold():
    """Тест валидации холодного лида"""
    
    with patch('services.agents.lead_processor.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = '{"score": 0.3, "status": "cold", "reason": "Нечеткое ТЗ"}'
        
        result = await validate_lead("Может быть интересно")
        
        assert result["score"] == 0.3
        assert result["status"] == "cold"


@pytest.mark.asyncio
async def test_generate_proposal():
    """Тест генерации коммерческого предложения"""
    
    with patch('services.agents.lead_processor.search_service') as mock_search, \
         patch('services.agents.lead_processor.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        
        # Мок результатов RAG поиска
        mock_search.return_value = [
            {"title": "Услуга подбора", "text": "Описание услуги", "score": 0.9}
        ]
        
        mock_llm.return_value = """
        Здравствуйте!
        
        Спасибо за обращение. Предлагаем следующие услуги:
        1. Подбор персонала
        2. Консультации
        
        Стоимость: от 50000 руб.
        """
        
        result = await generate_proposal(
            lead_request="Нужен подбор HR-менеджера",
            lead_contact={"name": "Иван", "email": "ivan@test.com"}
        )
        
        assert len(result) > 0
        assert "подбор" in result.lower() or "услуг" in result.lower()
        mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_generate_proposal_with_rag_results():
    """Тест генерации КП с предоставленными RAG результатами"""
    
    rag_results = [
        {"title": "Кейс подбора", "text": "Успешный кейс", "score": 0.95}
    ]
    
    with patch('services.agents.lead_processor.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Коммерческое предложение на основе кейсов..."
        
        result = await generate_proposal(
            lead_request="Подбор персонала",
            lead_contact={"name": "Тест"},
            rag_results=rag_results
        )
        
        assert len(result) > 0
        # search_service не должен вызываться, так как rag_results предоставлены
        mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_generate_hypothesis():
    """Тест генерации консалтинговых гипотез"""
    
    with patch('services.agents.lead_processor.search_service') as mock_search, \
         patch('services.agents.lead_processor.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        
        mock_search.return_value = [
            {"title": "Кейс автоматизации", "text": "Описание кейса", "category": "автоматизация"}
        ]
        
        mock_llm.return_value = """
        Гипотезы:
        1. Основная гипотеза: автоматизация HR процессов
        2. Аналогичные кейсы: успешные внедрения
        3. Риски: необходимость обучения персонала
        """
        
        result = await generate_hypothesis("Автоматизация HR процессов")
        
        assert len(result) > 0
        assert "гипотез" in result.lower() or "автоматизац" in result.lower()
        mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_generate_hypothesis_with_rag():
    """Тест генерации гипотез с предоставленными RAG результатами"""
    
    rag_results = [
        {"title": "Методика", "text": "Описание методики", "category": "консалтинг"}
    ]
    
    with patch('services.agents.lead_processor.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Гипотезы на основе методик..."
        
        result = await generate_hypothesis("Консалтинг", rag_results=rag_results)
        
        assert len(result) > 0
        mock_llm.assert_called_once()
