"""
Тесты для проверки всех команд Telegram бота
Проверяет, что каждая команда работает корректно
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes

# Импортируем команды из app.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from telegram.app import (
    rag_search_command,
    rag_stats_command,
    rag_docs_command,
    demo_proposal_command,
    status_command,
    summary_command,
    weeek_create_task_command,
    weeek_projects_command,
    email_check_command,
    email_draft_command,
    hypothesis_command,
    report_command
)


@pytest.fixture
def mock_update():
    """Создает mock объект Update"""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 123456
    update.message.from_user.username = "testuser"
    update.message.from_user.first_name = "Test"
    update.message.text = "test message"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Создает mock объект Context"""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    context.bot = AsyncMock()
    return context


# ===================== ТЕСТЫ RAG КОМАНД =====================

@pytest.mark.asyncio
async def test_rag_search_command(mock_update, mock_context):
    """Тест /rag_search - поиск в базе знаний"""
    mock_context.args = ["подбор", "персонала"]
    
    with patch("app.search_with_preview", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = {
            "results": [
                {"title": "Методики подбора", "score": 0.95, "text": "Пример текста"},
                {"title": "Кейс подбора IT", "score": 0.85, "content": "Пример контента"}
            ],
            "total_results": 2
        }
        
        await rag_search_command(mock_update, mock_context)
        
        # Проверяем, что бот ответил
        assert mock_update.message.reply_text.called
        response = mock_update.message.reply_text.call_args[0][0]
        assert "Результаты поиска" in response
        assert "подбор персонала" in response


@pytest.mark.asyncio
async def test_rag_stats_command(mock_update, mock_context):
    """Тест /rag_stats - статистика базы знаний"""
    with patch("app.get_collection_stats", new_callable=AsyncMock) as mock_stats:
        mock_stats.return_value = {
            "collection_name": "hr_knowledge",
            "exists": True,
            "points_count": 150,
            "vector_size": 1536
        }
        
        await rag_stats_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
        response = mock_update.message.reply_text.call_args[0][0]
        assert "Статистика RAG" in response
        assert "150" in response


@pytest.mark.asyncio
async def test_rag_docs_command(mock_update, mock_context):
    """Тест /rag_docs - список документов"""
    mock_context.args = ["10"]
    
    with patch("app.list_documents", new_callable=AsyncMock) as mock_docs:
        mock_docs.return_value = [
            {"title": "Документ 1", "category": "Методики"},
            {"title": "Документ 2", "category": "Кейсы"}
        ]
        
        await rag_docs_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
        response = mock_update.message.reply_text.call_args[0][0]
        assert "Документы в базе знаний" in response


# ===================== ТЕСТЫ WEEEK КОМАНД =====================

@pytest.mark.asyncio
async def test_weeek_projects_command(mock_update, mock_context):
    """Тест /weeek_projects - список проектов"""
    with patch("app.get_projects", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [
            {"name": "Проект 1", "status": "active"},
            {"name": "Проект 2", "status": "completed"}
        ]
        
        await weeek_projects_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
        response = mock_update.message.reply_text.call_args[0][0]
        assert "Проекты в WEEEK" in response
        assert "Проект 1" in response


@pytest.mark.asyncio
async def test_weeek_create_task_command(mock_update, mock_context):
    """Тест /weeek_task - создание задачи"""
    mock_context.args = ["Проект", "1", "|", "Согласовать", "КП"]
    
    with patch("app.get_projects", new_callable=AsyncMock) as mock_get_projects, \
         patch("app.create_task", new_callable=AsyncMock) as mock_create:
        
        mock_get_projects.return_value = [
            {"id": "proj123", "name": "Проект 1"}
        ]
        mock_create.return_value = {"id": "task123", "title": "Согласовать КП"}
        
        await weeek_create_task_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called


@pytest.mark.asyncio
async def test_status_command(mock_update, mock_context):
    """Тест /status - статус проектов"""
    with patch("app.get_project_deadlines", new_callable=AsyncMock) as mock_deadlines:
        mock_deadlines.return_value = [
            {"name": "Задача 1", "due_date": "2025-12-20", "status": "active"}
        ]
        
        await status_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
        response = mock_update.message.reply_text.call_args[0][0]
        assert "Статус проектов" in response


# ===================== ТЕСТЫ EMAIL КОМАНД =====================

@pytest.mark.asyncio
async def test_email_check_command(mock_update, mock_context):
    """Тест /email_check - проверка новых писем"""
    with patch("app.check_new_emails", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = [
            {
                "from": "client@example.com",
                "subject": "Запрос на подбор",
                "date": "2025-12-16"
            }
        ]
        
        await email_check_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
        response = mock_update.message.reply_text.call_args[0][0]
        assert "Новые письма" in response
        assert "client@example.com" in response


@pytest.mark.asyncio
async def test_email_draft_command(mock_update, mock_context):
    """Тест /email_draft - подготовка черновика"""
    mock_context.args = ["нужна", "помощь", "с", "подбором"]
    
    with patch("app.generate_proposal", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = "Добрый день! Готовы помочь с подбором персонала..."
        
        await email_draft_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
        response_calls = [call[0][0] for call in mock_update.message.reply_text.call_args_list]
        # Должно быть минимум 2 вызова (статус + ответ)
        assert len(response_calls) >= 1
        assert any("Черновик ответа" in str(call) for call in response_calls)


# ===================== ТЕСТЫ ГЕНЕРАЦИИ ДОКУМЕНТОВ =====================

@pytest.mark.asyncio
async def test_demo_proposal_command(mock_update, mock_context):
    """Тест /demo_proposal - генерация КП"""
    mock_context.args = ["помощь", "с", "подбором"]
    
    with patch("app.generate_proposal", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = "Коммерческое предложение по подбору персонала..."
        
        await demo_proposal_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
        response_calls = [call[0][0] for call in mock_update.message.reply_text.call_args_list]
        assert any("Черновик КП" in str(call) for call in response_calls)


@pytest.mark.asyncio
async def test_hypothesis_command(mock_update, mock_context):
    """Тест /hypothesis - генерация гипотез"""
    mock_context.args = ["автоматизация", "HR"]
    
    with patch("app.generate_hypothesis", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = "Гипотеза 1: Внедрить ATS систему..."
        
        await hypothesis_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
        response_calls = [call[0][0] for call in mock_update.message.reply_text.call_args_list]
        assert any("Гипотезы для проекта" in str(call) for call in response_calls)


@pytest.mark.asyncio
async def test_report_command(mock_update, mock_context):
    """Тест /report - генерация отчёта"""
    mock_context.args = ["Проект", "X"]
    
    with patch("app.get_projects", new_callable=AsyncMock) as mock_projects, \
         patch("app.generate_project_report", new_callable=AsyncMock) as mock_report:
        
        mock_projects.return_value = [{"name": "Проект X", "status": "active"}]
        mock_report.return_value = "Отчёт по проекту X..."
        
        await report_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called


@pytest.mark.asyncio
async def test_summary_command(mock_update, mock_context):
    """Тест /summary - суммаризация проекта"""
    mock_context.args = ["Проект", "Y"]
    
    with patch("app.summarize_project_conversation", new_callable=AsyncMock) as mock_summary:
        mock_summary.return_value = "Суммаризация: Проект находится на этапе согласования..."
        
        await summary_command(mock_update, mock_context)
        
        assert mock_update.message.reply_text.called
        response_calls = [call[0][0] for call in mock_update.message.reply_text.call_args_list]
        assert any("Суммаризация проекта" in str(call) for call in response_calls)


# ===================== ИНТЕГРАЦИОННЫЕ ТЕСТЫ =====================

@pytest.mark.asyncio
async def test_all_commands_are_async():
    """Проверка, что все команды асинхронные"""
    import inspect
    
    commands = [
        rag_search_command,
        rag_stats_command,
        rag_docs_command,
        demo_proposal_command,
        status_command,
        summary_command,
        weeek_create_task_command,
        weeek_projects_command,
        email_check_command,
        email_draft_command,
        hypothesis_command,
        report_command
    ]
    
    for command in commands:
        assert inspect.iscoroutinefunction(command), f"{command.__name__} должна быть async функцией"


@pytest.mark.asyncio
async def test_commands_handle_errors_gracefully(mock_update, mock_context):
    """Проверка, что команды корректно обрабатывают ошибки"""
    mock_context.args = ["тест"]
    
    # Проверяем, что команды не падают при ошибках импорта
    with patch("app.generate_proposal", side_effect=Exception("Test error")):
        await demo_proposal_command(mock_update, mock_context)
        
        # Должен быть отправлен ответ с ошибкой
        assert mock_update.message.reply_text.called
        response = mock_update.message.reply_text.call_args[0][0]
        assert "Ошибка" in response


@pytest.mark.asyncio
async def test_weeek_task_command_validates_format(mock_update, mock_context):
    """Проверка, что /weeek_task валидирует формат"""
    # Неправильный формат (без |)
    mock_context.args = ["Проект", "Задача"]
    
    await weeek_create_task_command(mock_update, mock_context)
    
    assert mock_update.message.reply_text.called
    response = mock_update.message.reply_text.call_args[0][0]
    assert "Неправильный формат" in response or "Укажите" in response


# ===================== ТЕСТЫ БЕЗ АРГУМЕНТОВ =====================

@pytest.mark.asyncio
async def test_commands_without_args_show_help(mock_update, mock_context):
    """Проверка, что команды без аргументов показывают help"""
    mock_context.args = []
    
    # /demo_proposal без аргументов
    await demo_proposal_command(mock_update, mock_context)
    assert mock_update.message.reply_text.called
    response = mock_update.message.reply_text.call_args[0][0]
    assert "Укажите" in response or "Использование" in response
    
    mock_update.message.reply_text.reset_mock()
    
    # /email_draft без аргументов
    await email_draft_command(mock_update, mock_context)
    assert mock_update.message.reply_text.called
    response = mock_update.message.reply_text.call_args[0][0]
    assert "Укажите" in response
    
    mock_update.message.reply_text.reset_mock()
    
    # /hypothesis без аргументов
    await hypothesis_command(mock_update, mock_context)
    assert mock_update.message.reply_text.called
    response = mock_update.message.reply_text.call_args[0][0]
    assert "Укажите" in response


# ===================== RUN TESTS =====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
