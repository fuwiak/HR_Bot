"""
Тесты для автоматического мониторинга почты
Проверяет работу уведомлений и действий с письмами
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

# ===================== TEST EMAIL CHECK =====================

@pytest.mark.asyncio
async def test_check_new_emails():
    """Тест проверки новых писем"""
    from email_helper import check_new_emails
    
    # Мокаем IMAP подключение
    with patch('email_helper.imaplib.IMAP4_SSL') as mock_imap:
        # Настраиваем мок
        mock_imap_instance = MagicMock()
        mock_imap.return_value = mock_imap_instance
        
        # Мокаем ответы IMAP
        mock_imap_instance.login.return_value = ('OK',)
        mock_imap_instance.select.return_value = ('OK', [b'1'])
        mock_imap_instance.search.return_value = ('OK', [b'1 2 3'])
        
        # Мокаем fetch для получения письма
        mock_email = Mock()
        mock_email.__getitem__ = Mock(return_value="test@example.com")
        mock_email.get_payload.return_value = b"Test email body"
        mock_email.is_multipart.return_value = False
        
        mock_imap_instance.fetch.return_value = ('OK', [(None, b'email data')])
        
        # Мокаем парсинг email
        with patch('email_helper.email.message_from_bytes', return_value=mock_email):
            emails = await check_new_emails(since_days=1, limit=5)
            
            assert isinstance(emails, list)
            print(f"✅ test_check_new_emails: Получено {len(emails)} писем")

# ===================== TEST EMAIL NOTIFICATION =====================

@pytest.mark.asyncio
async def test_send_email_notification():
    """Тест отправки уведомления о письме"""
    from telegram_bot.app import send_email_notification, email_cache
    
    # Очищаем кэш
    email_cache.clear()
    
    # Создаем тестовое письмо
    test_email = {
        "id": "test_email_123",
        "from": "client@company.com",
        "subject": "Запрос на стратегическую сессию",
        "body": "Добрый день, нужна помощь с проведением стратегической сессии для 15 человек 26 декабря.",
        "date": "19 Dec 2025 15:46:00 +0300"
    }
    
    # Мокаем бота
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()
    
    # Отправляем уведомление
    await send_email_notification(mock_bot, test_email)
    
    # Проверяем, что сообщение отправлено
    assert mock_bot.send_message.called
    call_args = mock_bot.send_message.call_args
    
    # Проверяем параметры
    assert call_args.kwargs['chat_id'] == 5305427956  # ADMIN_USER_ID
    assert 'Новое письмо' in call_args.kwargs['text']
    assert 'client@company.com' in call_args.kwargs['text']
    assert 'Запрос на стратегическую сессию' in call_args.kwargs['text']
    
    # Проверяем наличие кнопок
    assert call_args.kwargs['reply_markup'] is not None
    
    # Проверяем, что письмо сохранено в кэш
    assert test_email["id"] in email_cache
    
    print("✅ test_send_email_notification: Уведомление отправлено корректно")

# ===================== TEST EMAIL ACTIONS =====================

@pytest.mark.asyncio
async def test_handle_email_reply():
    """Тест подготовки ответа на письмо"""
    from telegram_bot.app import handle_email_reply, email_cache
    from telegram import CallbackQuery, Message, User, Chat
    
    # Подготавливаем тестовые данные
    test_email = {
        "id": "test_email_456",
        "from": "client@company.com",
        "subject": "Запрос на консультацию",
        "body": "Нужна помощь с подбором персонала"
    }
    email_cache["test_email_456"] = test_email
    
    # Создаем мок query
    mock_query = Mock(spec=CallbackQuery)
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()
    
    # Мокаем generate_proposal
    with patch('app.generate_proposal', new_callable=AsyncMock) as mock_proposal:
        mock_proposal.return_value = "Добрый день! Благодарим за обращение..."
        
        await handle_email_reply(mock_query, "test_email_456")
        
        # Проверяем, что ответ был вызван
        assert mock_query.answer.called
        assert mock_query.edit_message_text.called
        
        # Проверяем содержимое ответа
        call_args = mock_query.edit_message_text.call_args
        assert 'Черновик ответа' in call_args.kwargs['text']
        assert 'client@company.com' in call_args.kwargs['text']
        
        print("✅ test_handle_email_reply: Ответ подготовлен корректно")

@pytest.mark.asyncio
async def test_handle_email_proposal():
    """Тест создания КП из письма"""
    from telegram_bot.app import handle_email_proposal, email_cache
    
    # Подготавливаем тестовые данные
    test_email = {
        "id": "test_email_789",
        "from": "client@company.com",
        "subject": "Запрос на стратегическую сессию",
        "body": "Нужна стратегическая сессия для 15 человек 26 декабря"
    }
    email_cache["test_email_789"] = test_email
    
    # Создаем мок query
    mock_query = Mock(spec=CallbackQuery)
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()
    mock_query.message = Mock()
    mock_query.message.reply_text = AsyncMock()
    
    # Мокаем generate_proposal
    with patch('app.generate_proposal', new_callable=AsyncMock) as mock_proposal:
        mock_proposal.return_value = "Коммерческое предложение\n\nСтратегическая сессия..."
        
        await handle_email_proposal(mock_query, "test_email_789")
        
        # Проверяем, что КП было создано
        assert mock_query.answer.called
        assert mock_query.edit_message_text.called
        
        call_args = mock_query.edit_message_text.call_args
        assert 'Коммерческое предложение' in call_args.kwargs['text']
        
        print("✅ test_handle_email_proposal: КП создано корректно")

@pytest.mark.asyncio
async def test_handle_email_task():
    """Тест создания задачи в WEEEK из письма"""
    from telegram_bot.app import handle_email_task, email_cache
    
    # Подготавливаем тестовые данные
    test_email = {
        "id": "test_email_task",
        "from": "client@company.com",
        "subject": "Запрос на консультацию",
        "body": "Нужна помощь"
    }
    email_cache["test_email_task"] = test_email
    
    # Создаем мок query
    mock_query = Mock(spec=CallbackQuery)
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()
    
    # Мокаем get_projects
    with patch('app.get_projects', new_callable=AsyncMock) as mock_projects:
        mock_projects.return_value = [
            {"id": 1, "title": "Проект 1"},
            {"id": 2, "title": "Проект 2"}
        ]
        
        await handle_email_task(mock_query, "test_email_task")
        
        # Проверяем, что показано меню выбора проекта
        assert mock_query.edit_message_text.called
        call_args = mock_query.edit_message_text.call_args
        assert 'Создать задачу в WEEEK' in call_args.kwargs['text']
        assert call_args.kwargs['reply_markup'] is not None
        
        print("✅ test_handle_email_task: Меню выбора проекта показано")

@pytest.mark.asyncio
async def test_handle_email_create_task():
    """Тест создания задачи в WEEEK"""
    from telegram_bot.app import handle_email_create_task, email_cache
    
    # Подготавливаем тестовые данные
    test_email = {
        "id": "test_email_create",
        "from": "client@company.com",
        "subject": "Запрос на консультацию",
        "body": "Нужна помощь с подбором персонала"
    }
    email_cache["test_email_create"] = test_email
    
    # Создаем мок query
    mock_query = Mock(spec=CallbackQuery)
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()
    
    # Мокаем WEEEK функции
    with patch('app.create_task', new_callable=AsyncMock) as mock_create_task, \
         patch('app.get_project', new_callable=AsyncMock) as mock_get_project:
        
        mock_create_task.return_value = {"id": 15, "name": "Ответить на: Запрос"}
        mock_get_project.return_value = {"id": 1, "title": "Проект 1"}
        
        await handle_email_create_task(mock_query, "test_email_create", 1)
        
        # Проверяем, что задача создана
        assert mock_query.answer.called
        assert mock_query.edit_message_text.called
        
        call_args = mock_query.edit_message_text.call_args
        assert 'Задача создана в WEEEK' in call_args.kwargs['text']
        
        print("✅ test_handle_email_create_task: Задача создана корректно")

# ===================== TEST EMAIL MONITOR TASK =====================

@pytest.mark.asyncio
async def test_email_monitor_task():
    """Тест фоновой задачи мониторинга почты"""
    from telegram_bot.app import email_monitor_task, processed_email_ids, send_email_notification
    
    # Очищаем список обработанных писем
    processed_email_ids.clear()
    
    # Мокаем бота
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()
    
    # Мокаем check_new_emails
    test_emails = [
        {
            "id": "email_1",
            "from": "client1@company.com",
            "subject": "Запрос 1",
            "body": "Тело письма 1",
            "date": datetime.now().strftime("%d %b %Y %H:%M:%S")
        },
        {
            "id": "email_2",
            "from": "client2@company.com",
            "subject": "Запрос 2",
            "body": "Тело письма 2",
            "date": datetime.now().strftime("%d %b %Y %H:%M:%S")
        }
    ]
    
    with patch('app.check_new_emails', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = test_emails
        
        # Мокаем send_email_notification
        with patch('app.send_email_notification', new_callable=AsyncMock) as mock_notify:
            # Запускаем задачу на короткое время
            task = asyncio.create_task(email_monitor_task(mock_bot))
            
            # Ждем немного
            await asyncio.sleep(0.1)
            
            # Отменяем задачу
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Проверяем, что check_new_emails был вызван
            assert mock_check.called
            
            # Проверяем, что письма добавлены в processed_email_ids
            assert "email_1" in processed_email_ids or mock_notify.called
            
            print("✅ test_email_monitor_task: Фоновая задача работает корректно")

# ===================== TEST EMAIL CHECK COMMAND =====================

@pytest.mark.asyncio
async def test_email_check_command():
    """Тест команды /email_check"""
    from telegram_bot.app import email_check_command, processed_email_ids
    
    # Очищаем список обработанных
    processed_email_ids.clear()
    
    # Создаем мок update
    mock_update = Mock()
    mock_update.message = Mock()
    mock_update.message.reply_text = AsyncMock()
    
    # Мокаем check_new_emails
    test_emails = [
        {
            "id": "new_email_1",
            "from": "new@client.com",
            "subject": "Новое письмо",
            "body": "Тело нового письма",
            "date": datetime.now().strftime("%d %b %Y %H:%M:%S")
        }
    ]
    
    with patch('app.check_new_emails', new_callable=AsyncMock) as mock_check, \
         patch('app.send_email_notification', new_callable=AsyncMock) as mock_notify, \
         patch('app.app') as mock_app:
        
        mock_check.return_value = test_emails
        mock_app.bot = AsyncMock()
        
        await email_check_command(mock_update, Mock())
        
        # Проверяем, что команда выполнилась
        assert mock_update.message.reply_text.called
        
        # Проверяем, что новые письма обработаны
        assert "new_email_1" in processed_email_ids
        
        print("✅ test_email_check_command: Команда работает корректно")

# ===================== INTEGRATION TEST =====================

@pytest.mark.asyncio
async def test_email_workflow_integration():
    """Интеграционный тест полного workflow обработки письма"""
    from telegram_bot.app import (
        email_check_command,
        handle_email_reply,
        handle_email_proposal,
        handle_email_task,
        email_cache,
        processed_email_ids
    )
    
    # Очищаем данные
    email_cache.clear()
    processed_email_ids.clear()
    
    # 1. Создаем тестовое письмо
    test_email = {
        "id": "integration_test_email",
        "from": "test@client.com",
        "subject": "Тестовый запрос",
        "body": "Это тестовое письмо для проверки workflow",
        "date": datetime.now().strftime("%d %b %Y %H:%M:%S")
    }
    
    # 2. Мокаем все зависимости
    mock_update = Mock()
    mock_update.message = Mock()
    mock_update.message.reply_text = AsyncMock()
    
    mock_query = Mock(spec=CallbackQuery)
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()
    mock_query.message = Mock()
    mock_query.message.reply_text = AsyncMock()
    
    with patch('app.check_new_emails', new_callable=AsyncMock) as mock_check, \
         patch('app.send_email_notification', new_callable=AsyncMock) as mock_notify, \
         patch('app.generate_proposal', new_callable=AsyncMock) as mock_proposal, \
         patch('app.get_projects', new_callable=AsyncMock) as mock_projects, \
         patch('app.app') as mock_app:
        
        mock_check.return_value = [test_email]
        mock_proposal.return_value = "Тестовый ответ"
        mock_projects.return_value = [{"id": 1, "title": "Тестовый проект"}]
        mock_app.bot = AsyncMock()
        
        # 3. Проверяем почту
        await email_check_command(mock_update, Mock())
        
        # 4. Проверяем, что письмо в кэше
        assert test_email["id"] in email_cache
        
        # 5. Тестируем подготовку ответа
        await handle_email_reply(mock_query, test_email["id"])
        assert mock_query.edit_message_text.called
        
        # 6. Тестируем создание КП
        await handle_email_proposal(mock_query, test_email["id"])
        assert mock_query.edit_message_text.called
        
        # 7. Тестируем создание задачи
        await handle_email_task(mock_query, test_email["id"])
        assert mock_query.edit_message_text.called
        
        print("✅ test_email_workflow_integration: Полный workflow работает корректно")

# ===================== RUN ALL TESTS =====================

async def run_all_tests():
    """Запуск всех тестов"""
    print("="*70)
    print("🧪 ТЕСТИРОВАНИЕ АВТОМАТИЧЕСКОГО МОНИТОРИНГА ПОЧТЫ")
    print("="*70)
    
    tests = [
        ("Проверка новых писем", test_check_new_emails),
        ("Отправка уведомлений", test_send_email_notification),
        ("Подготовка ответа", test_handle_email_reply),
        ("Создание КП", test_handle_email_proposal),
        ("Создание задачи", test_handle_email_task),
        ("Создание задачи в WEEEK", test_handle_email_create_task),
        ("Фоновая задача", test_email_monitor_task),
        ("Команда /email_check", test_email_check_command),
        ("Интеграционный тест", test_email_workflow_integration),
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
        print("✅ Автоматический мониторинг почты работает корректно!")
    else:
        print(f"\n⚠️ Некоторые тесты не прошли ({failed} ошибок)")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
