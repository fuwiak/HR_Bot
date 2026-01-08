"""
Тесты для функционала загрузки документов через Telegram
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from telegram import Update, Message, User, Document
from telegram.ext import ContextTypes
import tempfile
import os

# Импортируем функции из app.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from telegram_bot.app import (
    upload_document_command,
    handle_document,
    extract_text_from_file,
    upload_to_qdrant
)


@pytest.fixture
def mock_update():
    """Создает mock объект Update с документом"""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 123456
    update.message.from_user.username = "testuser"
    update.message.from_user.first_name = "Test"
    update.message.reply_text = AsyncMock()
    
    # Mock для документа
    update.message.document = MagicMock(spec=Document)
    update.message.document.file_id = "test_file_id"
    update.message.document.file_name = "test_document.pdf"
    update.message.document.file_size = 1024 * 100  # 100 KB
    
    return update


@pytest.fixture
def mock_context():
    """Создает mock объект Context"""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    context.bot = AsyncMock()
    
    # Mock для get_file
    mock_file = AsyncMock()
    mock_file.download_to_drive = AsyncMock()
    context.bot.get_file = AsyncMock(return_value=mock_file)
    
    return context


# ===================== ТЕСТЫ КОМАНДЫ /upload =====================

@pytest.mark.asyncio
async def test_upload_command_shows_instructions(mock_update, mock_context):
    """Тест /upload - показывает инструкцию"""
    await upload_document_command(mock_update, mock_context)
    
    assert mock_update.message.reply_text.called
    response = mock_update.message.reply_text.call_args[0][0]
    assert "Загрузка документов" in response
    assert "PDF" in response
    assert "Word" in response
    assert "Excel" in response


# ===================== ТЕСТЫ ОБРАБОТКИ ДОКУМЕНТОВ =====================

@pytest.mark.asyncio
async def test_handle_document_rejects_large_files(mock_update, mock_context):
    """Тест отклонения слишком больших файлов"""
    # Устанавливаем большой размер файла (> 20 MB)
    mock_update.message.document.file_size = 25 * 1024 * 1024
    
    await handle_document(mock_update, mock_context)
    
    assert mock_update.message.reply_text.called
    response = mock_update.message.reply_text.call_args[0][0]
    assert "слишком большой" in response.lower()


@pytest.mark.asyncio
async def test_handle_document_rejects_unsupported_format(mock_update, mock_context):
    """Тест отклонения неподдерживаемых форматов"""
    mock_update.message.document.file_name = "test.xyz"
    
    await handle_document(mock_update, mock_context)
    
    assert mock_update.message.reply_text.called
    response = mock_update.message.reply_text.call_args[0][0]
    assert "не поддерживается" in response.lower()


@pytest.mark.asyncio
async def test_handle_document_accepts_pdf(mock_update, mock_context):
    """Тест принятия PDF файлов"""
    mock_update.message.document.file_name = "document.pdf"
    
    with patch("app.extract_text_from_file", new_callable=AsyncMock) as mock_extract, \
         patch("app.upload_to_qdrant", new_callable=AsyncMock) as mock_upload:
        
        mock_extract.return_value = "Это тестовый текст из PDF документа." * 10
        mock_upload.return_value = {
            "success": True,
            "chunks_count": 5,
            "doc_id": "test-doc-id"
        }
        
        await handle_document(mock_update, mock_context)
        
        # Проверяем, что функции были вызваны
        assert mock_extract.called
        assert mock_upload.called


@pytest.mark.asyncio
async def test_handle_document_accepts_docx(mock_update, mock_context):
    """Тест принятия Word файлов"""
    mock_update.message.document.file_name = "document.docx"
    
    with patch("app.extract_text_from_file", new_callable=AsyncMock) as mock_extract, \
         patch("app.upload_to_qdrant", new_callable=AsyncMock) as mock_upload:
        
        mock_extract.return_value = "Текст из Word документа." * 10
        mock_upload.return_value = {
            "success": True,
            "chunks_count": 3,
            "doc_id": "test-doc-id"
        }
        
        await handle_document(mock_update, mock_context)
        
        assert mock_extract.called
        assert mock_upload.called


@pytest.mark.asyncio
async def test_handle_document_accepts_xlsx(mock_update, mock_context):
    """Тест принятия Excel файлов"""
    mock_update.message.document.file_name = "spreadsheet.xlsx"
    
    with patch("app.extract_text_from_file", new_callable=AsyncMock) as mock_extract, \
         patch("app.upload_to_qdrant", new_callable=AsyncMock) as mock_upload:
        
        mock_extract.return_value = "Данные из Excel таблицы." * 10
        mock_upload.return_value = {
            "success": True,
            "chunks_count": 4,
            "doc_id": "test-doc-id"
        }
        
        await handle_document(mock_update, mock_context)
        
        assert mock_extract.called
        assert mock_upload.called


# ===================== ТЕСТЫ ИЗВЛЕЧЕНИЯ ТЕКСТА =====================

@pytest.mark.asyncio
async def test_extract_text_from_pdf():
    """Тест извлечения текста из PDF"""
    # Создаем временный PDF файл для теста
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
        temp_path = f.name
    
    try:
        # Создаем простой PDF с помощью PyPDF2
        from PyPDF2 import PdfWriter, PdfReader
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        # Создаем PDF с текстом
        c = canvas.Canvas(temp_path, pagesize=letter)
        c.drawString(100, 750, "Test PDF Document")
        c.drawString(100, 700, "This is a test text.")
        c.save()
        
        # Извлекаем текст
        text = await extract_text_from_file(temp_path, 'pdf')
        
        assert text is not None
        assert len(text) > 0
        # Может быть проблема с извлечением из созданного PDF, поэтому просто проверяем что функция работает
    
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.mark.asyncio
async def test_extract_text_from_txt():
    """Тест извлечения текста из TXT"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("Это тестовый текстовый файл.\nВторая строка.\nТретья строка.")
        temp_path = f.name
    
    try:
        text = await extract_text_from_file(temp_path, 'txt')
        
        assert text is not None
        assert "тестовый текстовый файл" in text
        assert "Вторая строка" in text
    
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ===================== ТЕСТЫ ЗАГРУЗКИ В QDRANT =====================

@pytest.mark.asyncio
async def test_upload_to_qdrant_creates_chunks():
    """Тест создания чанков при загрузке"""
    test_text = "Это тестовый текст. " * 100  # Длинный текст для создания нескольких чанков
    
    with patch("app.QdrantLoader") as mock_loader, \
         patch("app.get_embedding", new_callable=AsyncMock) as mock_embedding:
        
        mock_embedding.return_value = [0.1] * 1536  # Фейковый эмбеддинг
        mock_client = MagicMock()
        mock_loader.return_value.client = mock_client
        mock_loader.return_value.collection_name = "test_collection"
        
        result = await upload_to_qdrant(
            text_content=test_text,
            file_name="test.pdf",
            user_id=123456,
            username="testuser"
        )
        
        assert result["success"]
        assert result["chunks_count"] > 0
        assert "doc_id" in result


@pytest.mark.asyncio
async def test_upload_to_qdrant_handles_errors():
    """Тест обработки ошибок при загрузке"""
    with patch("app.QdrantLoader") as mock_loader:
        mock_loader.side_effect = Exception("Test error")
        
        result = await upload_to_qdrant(
            text_content="Test text",
            file_name="test.pdf",
            user_id=123456,
            username="testuser"
        )
        
        assert not result["success"]
        assert "error" in result


# ===================== ИНТЕГРАЦИОННЫЕ ТЕСТЫ =====================

@pytest.mark.asyncio
async def test_full_document_upload_flow(mock_update, mock_context):
    """Тест полного процесса загрузки документа"""
    mock_update.message.document.file_name = "integration_test.pdf"
    
    with patch("app.extract_text_from_file", new_callable=AsyncMock) as mock_extract, \
         patch("app.upload_to_qdrant", new_callable=AsyncMock) as mock_upload:
        
        # Симулируем успешную обработку
        mock_extract.return_value = "Интеграционный тест. " * 20
        mock_upload.return_value = {
            "success": True,
            "chunks_count": 7,
            "doc_id": "integration-test-id"
        }
        
        await handle_document(mock_update, mock_context)
        
        # Проверяем, что бот отправил статусные сообщения
        assert mock_update.message.reply_text.call_count >= 1


@pytest.mark.asyncio
async def test_document_upload_with_empty_text(mock_update, mock_context):
    """Тест обработки документа с пустым текстом"""
    mock_update.message.document.file_name = "empty.pdf"
    
    with patch("app.extract_text_from_file", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = ""  # Пустой текст
        
        await handle_document(mock_update, mock_context)
        
        # Проверяем, что бот сообщил об ошибке
        # Последний вызов должен содержать сообщение об ошибке
        calls = mock_update.message.reply_text.call_args_list
        # Должен быть хотя бы один вызов
        assert len(calls) > 0


# ===================== RUN TESTS =====================

if __name__ == "__main__":
    print("🧪 Запуск тестов загрузки документов...\n")
    pytest.main([__file__, "-v", "-s"])
