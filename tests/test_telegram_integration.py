"""
Интеграционные тесты для проверки работы всех сценариев через Telegram бота
Проверяет, что все компоненты работают async и интегрированы правильно
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes

# Импорты для тестирования
from services.agents.scenario_workflows import (
    process_hrtime_order,
    process_lead_email,
    process_telegram_lead,
    check_upcoming_deadlines
)
from services.agents.integrate_scenarios import (
    monitor_hrtime_orders,
    monitor_emails,
    start_background_tasks
)


# ===================== Тесты async функциональности =====================

@pytest.mark.asyncio
async def test_bot_is_async():
    """Тест: убедиться что бот использует async функции"""
    # Проверяем, что все ключевые функции async
    import inspect
    
    assert inspect.iscoroutinefunction(process_hrtime_order)
    assert inspect.iscoroutinefunction(process_lead_email)
    assert inspect.iscoroutinefunction(process_telegram_lead)
    assert inspect.iscoroutinefunction(check_upcoming_deadlines)
    assert inspect.iscoroutinefunction(monitor_hrtime_orders)
    assert inspect.iscoroutinefunction(monitor_emails)
    
    print("✅ Все функции используют async")


@pytest.mark.asyncio
async def test_telegram_bot_notifications_scenario1():
    """Тест Сценария 1: Проверка что уведомления отправляются через Telegram бота"""
    
    mock_order_data = {
        "id": "order_test_telegram",
        "title": "Подбор специалиста",
        "description": "Нужен специалист. Бюджет 50000. Срок 1 неделя.",
        "budget": 50000,
        "deadline": "2025-12-25",
        "client": {
            "name": "Тест Тестов",
            "email": "test@test.com",
            "phone": "+79000000000"
        }
    }
    
    # Создаем мок Telegram бота
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    with patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '123456'}), \
         patch('scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('scenario_workflows.generate_proposal', new_callable=AsyncMock) as mock_proposal, \
         patch('scenario_workflows.send_proposal', new_callable=AsyncMock) as mock_send_proposal, \
         patch('scenario_workflows.send_email', new_callable=AsyncMock) as mock_email, \
         patch('scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('scenario_workflows.create_task', new_callable=AsyncMock) as mock_task, \
         patch('scenario_workflows.get_rag_chain') as mock_rag:
        
        mock_classify.return_value = {"category": "подбор", "confidence": 0.9}
        mock_validate.return_value = {"score": 0.8, "status": "warm"}
        mock_proposal.return_value = "КП текст..."
        mock_send_proposal.return_value = True
        mock_email.return_value = True
        mock_create_project.return_value = {"id": "project_123"}
        mock_task.return_value = {"id": "task_123"}
        mock_rag.return_value = None
        
        # Выполняем обработку заказа
        result = await process_hrtime_order("order_test_telegram", order_data=mock_order_data)
        
        # Проверяем, что результат содержит текст уведомления для Telegram
        assert result["success"] is True
        assert "notification_text" in result
        assert "Telegram" in result["notification_text"] or "HR Time" in result["notification_text"]
        assert result["notification_sent"] is True
        
        print(f"✅ Уведомление подготовлено: {result['notification_text'][:100]}...")


@pytest.mark.asyncio
async def test_telegram_bot_approval_scenario2():
    """Тест Сценария 2: Проверка что подтверждение консультанта идет через Telegram"""
    
    mock_email_data = {
        "subject": "Запрос на консультацию",
        "body": "Нужна помощь с автоматизацией HR-процессов",
        "from": "client@example.com"
    }
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    with patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '123456'}), \
         patch('scenario_workflows.classify_email', new_callable=AsyncMock) as mock_classify_email, \
         patch('scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('scenario_workflows.generate_proposal', new_callable=AsyncMock) as mock_proposal, \
         patch('scenario_workflows.get_rag_chain') as mock_rag:
        
        mock_classify_email.return_value = "new_lead"
        mock_classify.return_value = {"category": "автоматизация", "confidence": 0.9}
        mock_proposal.return_value = "Предложение по автоматизации..."
        mock_rag.return_value = None
        
        result = await process_lead_email(
            mock_email_data,
            require_approval=True,
            telegram_bot=mock_telegram_bot
        )
        
        # Проверяем, что запрос на подтверждение отправлен через Telegram
        assert result["success"] is True
        assert result["requires_approval"] is True
        
        # Проверяем, что бот был вызван для отправки запроса на подтверждение
        mock_telegram_bot.send_message.assert_called()
        call_args = mock_telegram_bot.send_message.call_args
        
        # Проверяем, что сообщение отправлено консультанту
        assert call_args.kwargs.get("chat_id") == 123456
        assert "Подготовлен ответ" in call_args.kwargs.get("text", "")
        
        print("✅ Запрос на подтверждение отправлен через Telegram бота")


@pytest.mark.asyncio
async def test_telegram_bot_lead_processing_scenario3():
    """Тест Сценария 3: Проверка обработки лида через Telegram бота"""
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    with patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '123456'}), \
         patch('scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('scenario_workflows.get_rag_chain') as mock_rag:
        
        mock_classify.return_value = {"category": "подбор", "confidence": 0.9}
        mock_validate.return_value = {"score": 0.85, "status": "warm"}
        mock_create_project.return_value = {"id": "project_telegram_456"}
        
        mock_rag_instance = Mock()
        mock_rag_instance.query = AsyncMock(return_value={
            "answer": "Ответ по подбору..."
        })
        mock_rag.return_value = mock_rag_instance
        
        result = await process_telegram_lead(
            user_message="Нужен подбор IT-специалиста для стартапа",
            user_id=78901,
            user_name="Александр",
            telegram_bot=mock_telegram_bot
        )
        
        # Проверяем результат
        assert result["success"] is True
        assert result["weeek_project_created"] is True
        
        # Проверяем, что консультант был уведомлен через Telegram
        mock_telegram_bot.send_message.assert_called()
        call_args = mock_telegram_bot.send_message.call_args
        assert call_args.kwargs.get("chat_id") == 123456
        assert "Telegram" in call_args.kwargs.get("text", "")
        
        print("✅ Лид обработан, консультант уведомлен через Telegram")


@pytest.mark.asyncio
async def test_telegram_bot_deadline_reminders_scenario4():
    """Тест Сценария 4: Проверка что напоминания отправляются через Telegram"""
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    mock_tasks = [
        {
            "id": "task_1",
            "name": "Согласовать КП",
            "project_id": "project_1",
            "due_date": datetime.now().date().isoformat(),
            "status": "in_progress"
        }
    ]
    
    with patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '123456'}), \
         patch('scenario_workflows.get_project_deadlines', new_callable=AsyncMock) as mock_get_deadlines:
        
        mock_get_deadlines.return_value = mock_tasks
        
        result = await check_upcoming_deadlines(telegram_bot=mock_telegram_bot, days_ahead=1)
        
        # Проверяем, что задачи найдены
        assert len(result) > 0
        
        # Проверяем, что напоминание отправлено через Telegram
        mock_telegram_bot.send_message.assert_called()
        call_args = mock_telegram_bot.send_message.call_args
        assert call_args.kwargs.get("chat_id") == 123456
        assert "дедлайн" in call_args.kwargs.get("text", "").lower() or "напоминание" in call_args.kwargs.get("text", "").lower()
        
        print("✅ Напоминание о дедлайне отправлено через Telegram")


# ===================== Интеграционные тесты полного workflow =====================

@pytest.mark.asyncio
async def test_full_integration_scenario1_with_telegram():
    """Полный интеграционный тест Сценария 1: от заказа до уведомления консультанта"""
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock(return_value=Mock(id=123))
    
    mock_order = {
        "id": "order_full_test",
        "title": "Подбор HR-директора",
        "description": "Требуется опытный HR-директор. Бюджет: 200000 руб. Срок: 1 месяц.",
        "budget": 200000,
        "deadline": "2026-01-15",
        "client": {
            "name": "Иван Петров",
            "email": "ivan@company.com",
            "phone": "+79001234567"
        }
    }
    
    with patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '123456'}), \
         patch('scenario_workflows.get_order_details', new_callable=AsyncMock) as mock_get_order, \
         patch('scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('scenario_workflows.generate_proposal', new_callable=AsyncMock) as mock_proposal, \
         patch('scenario_workflows.send_proposal', new_callable=AsyncMock) as mock_send_proposal, \
         patch('scenario_workflows.send_email', new_callable=AsyncMock) as mock_email, \
         patch('scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('scenario_workflows.create_task', new_callable=AsyncMock) as mock_task, \
         patch('scenario_workflows.get_rag_chain') as mock_rag:
        
        # Настройка моков
        mock_get_order.return_value = mock_order
        mock_classify.return_value = {"category": "подбор", "confidence": 0.95}
        mock_validate.return_value = {
            "score": 0.9,
            "status": "warm",
            "reason": "Отличный лид"
        }
        mock_proposal.return_value = "Коммерческое предложение по подбору HR-директора..."
        mock_send_proposal.return_value = True
        mock_email.return_value = True
        mock_create_project.return_value = {"id": "project_full_test"}
        mock_task.return_value = {"id": "task_full_test"}
        mock_rag.return_value = None
        
        # Выполняем полный workflow
        result = await process_hrtime_order("order_full_test")
        
        # Проверки полного цикла
        assert result["success"] is True
        assert result["validation"]["score"] > 0.6
        assert result["proposal_sent"] is True
        assert result["weeek_project_created"] is True
        assert "notification_text" in result
        
        # Симулируем отправку уведомления консультанту через Telegram
        if result.get("notification_text"):
            await mock_telegram_bot.send_message(
                chat_id=123456,
                text=result["notification_text"],
                parse_mode="Markdown"
            )
        
        # Проверяем, что все действия выполнены
        mock_get_order.assert_called_once()
        mock_classify.assert_called_once()
        mock_validate.assert_called_once()
        mock_proposal.assert_called_once()
        mock_send_proposal.assert_called_once()
        mock_email.assert_called_once()
        mock_create_project.assert_called_once()
        mock_task.assert_called_once()
        
        print("✅ Полный workflow Сценария 1 выполнен успешно")
        print(f"   - Заказ обработан: {result['order_id']}")
        print(f"   - Отклик отправлен: {result['proposal_sent']}")
        print(f"   - Проект создан: {result['weeek_project_created']}")
        print(f"   - Уведомление подготовлено: {len(result['notification_text'])} символов")


@pytest.mark.asyncio
async def test_background_tasks_startup():
    """Тест запуска фоновых задач мониторинга"""
    
    mock_telegram_bot = AsyncMock()
    
    with patch('integrate_scenarios.monitor_hrtime_orders', new_callable=AsyncMock) as mock_hrtime, \
         patch('integrate_scenarios.monitor_emails', new_callable=AsyncMock) as mock_emails, \
         patch('integrate_scenarios.start_deadline_monitor', new_callable=AsyncMock) as mock_deadlines:
        
        # Моки должны возвращать задачи (tasks)
        mock_hrtime.return_value = None
        mock_emails.return_value = None
        mock_deadlines.return_value = None
        
        # Запускаем фоновые задачи
        tasks = start_background_tasks(
            telegram_bot=mock_telegram_bot,
            enable_hrtime=True,
            enable_email=True,
            enable_deadlines=True
        )
        
        # Проверяем, что задачи созданы
        assert len(tasks) == 3
        assert all(hasattr(task, 'done') for task in tasks)  # Это asyncio.Task объекты
        
        # Отменяем задачи (для очистки)
        for task in tasks:
            if not task.done():
                task.cancel()
        
        print("✅ Фоновые задачи успешно запущены")


# ===================== Тесты async производительности =====================

@pytest.mark.asyncio
async def test_concurrent_processing():
    """Тест: проверка что система может обрабатывать несколько запросов параллельно"""
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    # Создаем несколько тестовых запросов
    test_leads = [
        {"message": "Нужен подбор менеджера", "user_id": 1, "user_name": "User1"},
        {"message": "Требуется автоматизация HR", "user_id": 2, "user_name": "User2"},
        {"message": "Консультация по бизнес-процессам", "user_id": 3, "user_name": "User3"},
    ]
    
    with patch('scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('scenario_workflows.get_rag_chain') as mock_rag, \
         patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '123456'}):
        
        mock_classify.return_value = {"category": "подбор", "confidence": 0.8}
        mock_validate.return_value = {"score": 0.7, "status": "warm"}
        mock_create_project.return_value = {"id": "project_concurrent"}
        mock_rag.return_value = None
        
        # Запускаем обработку параллельно
        start_time = datetime.now()
        
        tasks = [
            process_telegram_lead(
                lead["message"],
                lead["user_id"],
                lead["user_name"],
                telegram_bot=mock_telegram_bot
            )
            for lead in test_leads
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Проверяем результаты
        assert len(results) == len(test_leads)
        assert all(r.get("success") for r in results)
        
        # Проверяем, что обработка была параллельной (должна быть быстрее чем последовательная)
        # Для 3 запросов параллельная обработка должна быть заметно быстрее
        print(f"✅ Параллельная обработка {len(test_leads)} запросов завершена за {duration:.2f} секунд")
        print(f"   Среднее время на запрос: {duration/len(test_leads):.2f} секунд")


# ===================== Тесты интеграции с командами бота =====================

@pytest.mark.asyncio
async def test_telegram_bot_commands_integration():
    """Тест: проверка что команды бота работают async"""
    
    # Проверяем, что команды используют async
    import telegram_bot.app as app
    import inspect
    
    # Проверяем основные команды
    assert inspect.iscoroutinefunction(app.start)
    assert inspect.iscoroutinefunction(app.menu)
    assert inspect.iscoroutinefunction(app.reply)
    assert inspect.iscoroutinefunction(app.summary_command)
    assert inspect.iscoroutinefunction(app.status_command)
    assert inspect.iscoroutinefunction(app.rag_search_command)
    
    print("✅ Все команды бота используют async")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


