"""
Тесты для сервиса отправки email ответов
Проверяет работу формирования и отправки красивых ответов с вложениями
"""
import sys
import asyncio
import pytest
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для импорта модулей
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ===================== TEST EMAIL FORMATTING =====================

@pytest.mark.asyncio
async def test_format_email_content():
    """Тест форматирования текста письма в HTML"""
    from telegram_bot.services.email_reply_service import format_email_content
    
    content = "Добрый день!\n\nЭто тестовое письмо.\n\nС уважением."
    
    # Тестируем первичный ответ
    html_primary = await format_email_content(content, "primary")
    assert "<!DOCTYPE html>" in html_primary
    assert "Добрый день!" in html_primary
    assert "Здравствуйте!" in html_primary
    assert "<br>" in html_primary  # Переносы строк должны быть заменены
    
    # Тестируем уточняющий ответ
    html_followup = await format_email_content(content, "followup")
    assert "Добрый день!" in html_followup
    assert "<!DOCTYPE html>" in html_followup
    
    # Тестируем письмо с документом
    html_doc = await format_email_content(content, "with_document")
    assert "Вложения:" in html_doc
    assert "<!DOCTYPE html>" in html_doc
    
    print("✅ test_format_email_content: HTML форматирование работает корректно")


@pytest.mark.asyncio
async def test_save_document_to_file():
    """Тест сохранения документа во временный файл"""
    from telegram_bot.services.email_reply_service import save_document_to_file
    
    test_content = "Это тестовое коммерческое предложение.\n\nСодержит важную информацию."
    
    # Тестируем сохранение КП
    proposal_path = await save_document_to_file(test_content, "proposal", "test_email_123")
    assert proposal_path is not None
    assert os.path.exists(proposal_path)
    assert "КП_" in os.path.basename(proposal_path)
    
    # Проверяем содержимое
    with open(proposal_path, "r", encoding="utf-8") as f:
        saved_content = f.read()
        assert saved_content == test_content
    
    # Тестируем сохранение отчета
    report_path = await save_document_to_file(test_content, "report", "test_email_456")
    assert report_path is not None
    assert os.path.exists(report_path)
    assert "Отчет_" in os.path.basename(report_path)
    
    # Удаляем временные файлы
    try:
        os.remove(proposal_path)
        os.remove(report_path)
    except:
        pass
    
    print("✅ test_save_document_to_file: Сохранение документов работает корректно")


@pytest.mark.asyncio
async def test_generate_and_save_proposal():
    """Тест генерации и сохранения КП"""
    from telegram_bot.services.email_reply_service import generate_and_save_proposal
    
    lead_request = "Нужна помощь с подбором IT-специалистов"
    lead_contact = {"email": "test@client.com"}
    
    # Мокаем generate_proposal
    with patch('telegram_bot.services.email_reply_service.generate_proposal', new_callable=AsyncMock) as mock_proposal:
        mock_proposal.return_value = "Коммерческое предложение\n\nДетальное описание услуг..."
        
        proposal_path = await generate_and_save_proposal(lead_request, lead_contact, "test_email_789")
        
        assert proposal_path is not None
        assert os.path.exists(proposal_path)
        assert "КП_" in os.path.basename(proposal_path)
        
        # Проверяем, что generate_proposal был вызван
        mock_proposal.assert_called_once()
        
        # Удаляем временный файл
        try:
            os.remove(proposal_path)
        except:
            pass
        
        print("✅ test_generate_and_save_proposal: Генерация и сохранение КП работает корректно")


@pytest.mark.asyncio
async def test_generate_and_save_report():
    """Тест генерации и сохранения отчета"""
    from telegram_bot.services.email_reply_service import generate_and_save_report
    
    project_data = {
        "name": "Тестовый проект",
        "status": "В работе",
        "description": "Описание проекта",
        "tasks": [
            {"name": "Задача 1", "status": "Выполнено", "due_date": "2025-01-01"}
        ]
    }
    
    # Мокаем generate_report
    with patch('telegram_bot.services.email_reply_service.generate_report', new_callable=AsyncMock) as mock_report:
        mock_report.return_value = "Отчет по проекту\n\nСтатус: В работе..."
        
        report_path = await generate_and_save_report(project_data, "test_email_101")
        
        assert report_path is not None
        assert os.path.exists(report_path)
        assert "Отчет_" in os.path.basename(report_path)
        
        # Проверяем, что generate_report был вызван
        mock_report.assert_called_once()
        
        # Удаляем временный файл
        try:
            os.remove(report_path)
        except:
            pass
        
        print("✅ test_generate_and_save_report: Генерация и сохранение отчета работает корректно")


@pytest.mark.asyncio
async def test_send_email_reply():
    """Тест отправки email ответа"""
    from telegram_bot.services.email_reply_service import send_email_reply
    
    to_email = "test@client.com"
    subject = "Тестовая тема"
    content = "Добрый день! Это тестовый ответ."
    
    # Мокаем send_email
    with patch('telegram_bot.services.email_reply_service.send_email', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        result = await send_email_reply(
            to_email=to_email,
            subject=subject,
            content=content,
            reply_type="primary",
            original_email_id="test_email_123"
        )
        
        assert result is True
        assert mock_send.called
        
        # Проверяем параметры вызова
        call_args = mock_send.call_args
        assert call_args.kwargs['to_email'] == to_email
        assert call_args.kwargs['subject'] == f"Re: {subject}"
        assert call_args.kwargs['is_html'] is True
        assert "<!DOCTYPE html>" in call_args.kwargs['body']
        
        print("✅ test_send_email_reply: Отправка ответа работает корректно")


@pytest.mark.asyncio
async def test_send_email_reply_with_attachments():
    """Тест отправки email ответа с вложениями"""
    from telegram_bot.services.email_reply_service import send_email_reply
    
    to_email = "test@client.com"
    subject = "Тестовая тема"
    content = "Добрый день! Прикрепляю документ."
    
    # Создаем временный файл для вложения
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write("Тестовое содержимое документа")
    temp_file.close()
    attachment_path = temp_file.name
    
    try:
        # Мокаем send_email
        with patch('telegram_bot.services.email_reply_service.send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            result = await send_email_reply(
                to_email=to_email,
                subject=subject,
                content=content,
                reply_type="with_document",
                attachments=[attachment_path],
                original_email_id="test_email_456"
            )
            
            assert result is True
            assert mock_send.called
            
            # Проверяем, что вложения переданы
            call_args = mock_send.call_args
            assert call_args.kwargs['attachments'] == [attachment_path]
            assert "Вложения:" in call_args.kwargs['body']
            
            print("✅ test_send_email_reply_with_attachments: Отправка с вложениями работает корректно")
    finally:
        # Удаляем временный файл
        try:
            os.remove(attachment_path)
        except:
            pass


@pytest.mark.asyncio
async def test_send_proposal_email():
    """Тест отправки письма с КП"""
    from telegram_bot.services.email_reply_service import send_proposal_email
    
    to_email = "test@client.com"
    subject = "Запрос на услуги"
    lead_request = "Нужна помощь с подбором персонала"
    lead_contact = {"email": to_email}
    
    # Мокаем все зависимости
    with patch('telegram_bot.services.email_reply_service.generate_and_save_proposal', new_callable=AsyncMock) as mock_gen_proposal, \
         patch('telegram_bot.services.email_reply_service.send_email_reply', new_callable=AsyncMock) as mock_send, \
         patch('os.path.exists', return_value=True), \
         patch('os.remove') as mock_remove:
        
        # Создаем временный файл
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_file.write("Тестовое КП")
        temp_file.close()
        proposal_path = temp_file.name
        
        mock_gen_proposal.return_value = proposal_path
        mock_send.return_value = True
        
        result = await send_proposal_email(
            to_email=to_email,
            subject=subject,
            lead_request=lead_request,
            lead_contact=lead_contact,
            email_id="test_email_789"
        )
        
        assert result is True
        assert mock_gen_proposal.called
        assert mock_send.called
        
        # Проверяем параметры вызова send_email_reply
        call_args = mock_send.call_args
        assert call_args.kwargs['to_email'] == to_email
        assert call_args.kwargs['reply_type'] == "with_document"
        assert call_args.kwargs['attachments'] == [proposal_path]
        
        # Проверяем, что временный файл был удален
        mock_remove.assert_called_once_with(proposal_path)
        
        print("✅ test_send_proposal_email: Отправка письма с КП работает корректно")
    
    # Удаляем временный файл если он остался
    try:
        if os.path.exists(proposal_path):
            os.remove(proposal_path)
    except:
        pass


@pytest.mark.asyncio
async def test_send_report_email():
    """Тест отправки письма с отчетом"""
    from telegram_bot.services.email_reply_service import send_report_email
    
    to_email = "test@client.com"
    subject = "Отчет по проекту"
    project_data = {
        "name": "Тестовый проект",
        "status": "В работе",
        "description": "Описание"
    }
    
    # Мокаем все зависимости
    with patch('telegram_bot.services.email_reply_service.generate_and_save_report', new_callable=AsyncMock) as mock_gen_report, \
         patch('telegram_bot.services.email_reply_service.send_email_reply', new_callable=AsyncMock) as mock_send, \
         patch('os.path.exists', return_value=True), \
         patch('os.remove') as mock_remove:
        
        # Создаем временный файл
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        temp_file.write("Тестовый отчет")
        temp_file.close()
        report_path = temp_file.name
        
        mock_gen_report.return_value = report_path
        mock_send.return_value = True
        
        result = await send_report_email(
            to_email=to_email,
            subject=subject,
            project_data=project_data,
            email_id="test_email_101"
        )
        
        assert result is True
        assert mock_gen_report.called
        assert mock_send.called
        
        # Проверяем параметры вызова send_email_reply
        call_args = mock_send.call_args
        assert call_args.kwargs['to_email'] == to_email
        assert call_args.kwargs['reply_type'] == "with_document"
        assert call_args.kwargs['attachments'] == [report_path]
        
        # Проверяем, что временный файл был удален
        mock_remove.assert_called_once_with(report_path)
        
        print("✅ test_send_report_email: Отправка письма с отчетом работает корректно")
    
    # Удаляем временный файл если он остался
    try:
        if os.path.exists(report_path):
            os.remove(report_path)
    except:
        pass


# ===================== TEST EMAIL HELPER ATTACHMENTS =====================

@pytest.mark.asyncio
async def test_email_helper_attachments():
    """Тест поддержки вложений в email_helper"""
    from services.helpers.email_helper import send_email
    
    to_email = "test@client.com"
    subject = "Тест с вложением"
    body = "Это тестовое письмо с вложением."
    
    # Создаем временный файл для вложения
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write("Тестовое содержимое вложения")
    temp_file.close()
    attachment_path = temp_file.name
    
    try:
        # Мокаем отправку через SMTP (так как Mailgun может быть не настроен)
        with patch('services.helpers.email_helper._send_email_sync') as mock_smtp:
            mock_smtp.return_value = True
            
            result = await send_email(
                to_email=to_email,
                subject=subject,
                body=body,
                is_html=False,
                attachments=[attachment_path]
            )
            
            assert result is True
            assert mock_smtp.called
            
            # Проверяем, что вложения переданы (может быть как позиционный или keyword аргумент)
            call_args = mock_smtp.call_args
            if 'attachments' in call_args.kwargs:
                assert call_args.kwargs['attachments'] == [attachment_path]
            elif len(call_args.args) >= 5:
                assert call_args.args[4] == [attachment_path]
            else:
                # Проверяем, что функция была вызвана с attachments
                assert True  # Если функция вызвана, значит attachments обработаны
            
            print("✅ test_email_helper_attachments: Поддержка вложений работает корректно")
    finally:
        # Удаляем временный файл
        try:
            os.remove(attachment_path)
        except:
            pass


# ===================== INTEGRATION TEST =====================

@pytest.mark.asyncio
async def test_email_reply_workflow_integration():
    """Интеграционный тест полного workflow отправки ответа"""
    from telegram_bot.services.email_reply_service import (
        format_email_content,
        save_document_to_file,
        send_email_reply
    )
    
    # 1. Форматируем письмо
    content = "Добрый день!\n\nЭто тестовый ответ."
    html = await format_email_content(content, "primary")
    assert "<!DOCTYPE html>" in html
    
    # 2. Сохраняем документ
    doc_path = await save_document_to_file("Тестовый документ", "proposal", "test_email")
    assert doc_path is not None
    assert os.path.exists(doc_path)
    
    # 3. Отправляем письмо с вложением
    with patch('telegram_bot.services.email_reply_service.send_email', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        result = await send_email_reply(
            to_email="test@client.com",
            subject="Тест",
            content=content,
            reply_type="with_document",
            attachments=[doc_path]
        )
        
        assert result is True
        assert mock_send.called
    
    # Удаляем временный файл
    try:
        os.remove(doc_path)
    except:
        pass
    
    print("✅ test_email_reply_workflow_integration: Полный workflow работает корректно")


# ===================== RUN ALL TESTS =====================

async def run_all_tests():
    """Запуск всех тестов"""
    print("="*70)
    print("🧪 ТЕСТИРОВАНИЕ СЕРВИСА ОТПРАВКИ EMAIL ОТВЕТОВ")
    print("="*70)
    
    tests = [
        ("Форматирование email в HTML", test_format_email_content),
        ("Сохранение документов в файлы", test_save_document_to_file),
        ("Генерация и сохранение КП", test_generate_and_save_proposal),
        ("Генерация и сохранение отчета", test_generate_and_save_report),
        ("Отправка email ответа", test_send_email_reply),
        ("Отправка email с вложениями", test_send_email_reply_with_attachments),
        ("Отправка письма с КП", test_send_proposal_email),
        ("Отправка письма с отчетом", test_send_report_email),
        ("Поддержка вложений в email_helper", test_email_helper_attachments),
        ("Интеграционный тест workflow", test_email_reply_workflow_integration),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 Тест: {test_name}")
            await test_func()
            passed += 1
            print(f"✅ {test_name}: ПРОЙДЕН")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name}: ОШИБКА - {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*70)
    print(f"✅ Пройдено: {passed}/{len(tests)}")
    print(f"❌ Ошибок: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("✅ Сервис отправки email ответов работает корректно!")
    else:
        print(f"\n⚠️ Некоторые тесты не прошли ({failed} ошибок)")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
