"""
Тесты для функций суммаризации и генерации отчетов
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from services.helpers.summary_helper import (
    summarize_project_conversation,
    generate_report,
    summarize_long_text
)


@pytest.mark.asyncio
async def test_summarize_project_conversation():
    """Тест суммаризации переписки по проекту"""
    
    conversations = [
        {"role": "user", "content": "Нужен подбор персонала", "timestamp": "2025-01-01"},
        {"role": "assistant", "content": "Предлагаю следующие этапы...", "timestamp": "2025-01-01"},
        {"role": "user", "content": "Согласен, начинаем", "timestamp": "2025-01-02"}
    ]
    
    with patch('services.helpers.summary_helper.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = """
        Ключевые договоренности:
        - Подбор персонала
        - Согласованы этапы работ
        
        Следующий шаг: Начать подбор
        """
        
        result = await summarize_project_conversation(
            conversations=conversations,
            project_name="Проект подбора"
        )
        
        assert len(result) > 0
        assert "договоренност" in result.lower() or "следующий" in result.lower()
        mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_summarize_project_conversation_empty():
    """Тест суммаризации пустой переписки"""
    
    with patch('services.helpers.summary_helper.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Нет данных для суммаризации"
        
        result = await summarize_project_conversation(
            conversations=[],
            project_name="Пустой проект"
        )
        
        assert len(result) > 0
        mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_generate_report():
    """Тест генерации отчета по проекту"""
    
    project_data = {
        "name": "Проект подбора",
        "status": "in_progress",
        "description": "Подбор HR-менеджера",
        "tasks": [
            {"name": "Согласовать КП", "status": "completed", "due_date": "2025-01-15"},
            {"name": "Провести собеседования", "status": "in_progress", "due_date": "2025-01-20"}
        ]
    }
    
    with patch('services.helpers.summary_helper.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = """
        Отчет по проекту:
        1. Описание: Подбор HR-менеджера
        2. Выполненные этапы: Согласование КП
        3. Текущий статус: В работе
        4. Ближайшие задачи: Собеседования
        """
        
        result = await generate_report(project_data)
        
        assert len(result) > 0
        assert "отчет" in result.lower() or "проект" in result.lower()
        mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_generate_report_minimal_data():
    """Тест генерации отчета с минимальными данными"""
    
    project_data = {
        "name": "Проект",
        "status": "new",
        "tasks": []
    }
    
    with patch('services.helpers.summary_helper.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Отчет по проекту Проект"
        
        result = await generate_report(project_data)
        
        assert len(result) > 0
        mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_summarize_long_text():
    """Тест суммаризации длинного текста"""
    
    long_text = "Это очень длинный текст. " * 100  # ~3000 символов
    
    with patch('services.helpers.summary_helper.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Краткая выжимка длинного текста"
        
        result = await summarize_long_text(long_text, max_length=500)
        
        assert len(result) <= 500
        assert len(result) > 0
        mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_summarize_long_text_short():
    """Тест суммаризации короткого текста (не требует суммаризации)"""
    
    short_text = "Короткий текст"
    
    with patch('services.helpers.summary_helper.generate_with_fallback', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = short_text
        
        result = await summarize_long_text(short_text, max_length=500)
        
        # Для короткого текста может вернуться как есть или суммаризация
        assert len(result) > 0
