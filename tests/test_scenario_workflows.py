"""
Тесты для всех 4 бизнес-сценариев
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

# Импорты модулей для тестирования
from services.agents.scenario_workflows import (
    process_hrtime_order,
    process_lead_email,
    process_telegram_lead,
    check_upcoming_deadlines,
    summarize_project_by_name
)


# ===================== СЦЕНАРИЙ 1: Новый лид с HR Time =====================

@pytest.mark.asyncio
async def test_scenario1_warm_lead_workflow():
    """Тест полного workflow для теплого лида с HR Time"""
    
    # Моки для зависимостей
    mock_order_data = {
        "id": "order_123",
        "title": "Подбор HR-менеджера",
        "description": "Нужен опытный HR-менеджер для работы с персоналом компании. Бюджет: 100000 руб. Срок: 2 недели.",
        "budget": 100000,
        "deadline": "2025-12-30",
        "client": {
            "name": "Иван Иванов",
            "email": "ivan@example.com",
            "phone": "+79001234567"
        }
    }
    
    with patch('services.helpers.hrtime_helper.get_order_details', new_callable=AsyncMock) as mock_get_order, \
         patch('services.agents.lead_processor.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.lead_processor.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('services.agents.lead_processor.generate_proposal', new_callable=AsyncMock) as mock_proposal, \
         patch('services.helpers.hrtime_helper.send_proposal', new_callable=AsyncMock) as mock_send_proposal, \
         patch('services.helpers.email_helper.send_email', new_callable=AsyncMock) as mock_send_email, \
         patch('services.helpers.weeek_helper.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('services.helpers.weeek_helper.create_task', new_callable=AsyncMock) as mock_create_task, \
         patch('services.helpers.weeek_helper.update_project_status', new_callable=AsyncMock) as mock_update_status, \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag:
        
        # Настройка моков
        mock_get_order.return_value = mock_order_data
        mock_classify.return_value = {
            "category": "подбор",
            "confidence": 0.9,
            "keywords": ["HR-менеджер", "подбор персонала"]
        }
        mock_validate.return_value = {
            "score": 0.85,
            "status": "warm",
            "reason": "Четкое ТЗ, есть бюджет и сроки",
            "criteria": {
                "clarity": 0.9,
                "budget": 0.8,
                "relevance": 0.85
            }
        }
        mock_proposal.return_value = "Коммерческое предложение для подбора HR-менеджера..."
        mock_send_proposal.return_value = True
        mock_send_email.return_value = True
        # Важно: ID должен быть строкой или числом, не None
        mock_create_project.return_value = {"id": 123, "name": "Тестовый проект"}
        mock_create_task.return_value = {"id": "task_123", "name": "Согласовать КП"}
        mock_update_status.return_value = True
        
        # Мок RAG chain
        mock_rag_instance = Mock()
        mock_rag_instance.query = AsyncMock(return_value={
            "answer": "Релевантная информация о подборе персонала...",
            "sources": ["source1"],
            "context_count": 3
        })
        mock_rag.return_value = mock_rag_instance
        
        # Выполнение теста
        result = await process_hrtime_order("order_123", order_data=mock_order_data)
        
        # Проверки
        assert result["success"] is True
        assert result["order_id"] == "order_123"
        assert result["validation"]["score"] > 0.6
        assert result["proposal_sent"] is True
        assert result["weeek_project_created"] is True
        assert "notification_text" in result
        
        # Проверка вызовов
        mock_send_proposal.assert_called_once()
        mock_send_email.assert_called_once()
        mock_create_project.assert_called_once()
        mock_create_task.assert_called_once()
        
        # Проверка обновления статуса проекта
        if result.get("weeek_project_created"):
            # update_project_status должен быть вызван
            mock_update_status.assert_called_once()


@pytest.mark.asyncio
async def test_scenario1_cold_lead_no_actions():
    """Тест, что для холодного лида не выполняются действия"""
    
    mock_order_data = {
        "id": "order_456",
        "title": "Общий вопрос",
        "description": "Интересует консалтинг",
        "client": {"name": "Тест", "email": "test@example.com"}
    }
    
    with patch('services.agents.scenario_workflows.get_order_details', new_callable=AsyncMock) as mock_get_order, \
         patch('services.agents.scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('services.agents.scenario_workflows.send_proposal', new_callable=AsyncMock) as mock_send_proposal, \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag:
        
        mock_get_order.return_value = mock_order_data
        mock_classify.return_value = {"category": "другое", "confidence": 0.5}
        mock_validate.return_value = {
            "score": 0.3,
            "status": "cold",
            "reason": "Недостаточно информации"
        }
        mock_rag.return_value = None
        
        result = await process_hrtime_order("order_456", order_data=mock_order_data)
        
        assert result["success"] is True
        assert result["validation"]["score"] < 0.6
        assert result.get("proposal_sent", False) is False
        assert result.get("weeek_project_created", False) is False
        
        # Проверка, что действия не выполнялись
        mock_send_proposal.assert_not_called()


# ===================== СЦЕНАРИЙ 2: Прямое письмо от лида =====================

@pytest.mark.asyncio
async def test_scenario2_email_processing_with_approval():
    """Тест обработки письма с подтверждением консультанта"""
    
    mock_email_data = {
        "subject": "Запрос на консультацию",
        "body": "Нужна помощь с автоматизацией HR-процессов",
        "from": "client@example.com",
        "to": "a-novoselova07@yandex.ru"
    }
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    with patch('services.agents.scenario_workflows.classify_email', new_callable=AsyncMock) as mock_classify_email, \
         patch('services.agents.scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.scenario_workflows.generate_proposal', new_callable=AsyncMock) as mock_proposal, \
         patch('services.agents.scenario_workflows.send_email', new_callable=AsyncMock) as mock_send_email, \
         patch('services.agents.scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag, \
         patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '123456'}):
        
        mock_classify_email.return_value = "new_lead"
        mock_classify.return_value = {"category": "автоматизация", "confidence": 0.9}
        mock_proposal.return_value = "Предложение по автоматизации..."
        mock_send_email.return_value = True
        mock_create_project.return_value = {"id": "project_456"}
        mock_rag.return_value = None
        
        result = await process_lead_email(mock_email_data, require_approval=True, telegram_bot=mock_telegram_bot)
        
        assert result["success"] is True
        assert result["requires_approval"] is True
        assert result.get("approval_requested", False) is True
        
        # Проверка отправки запроса на подтверждение
        mock_telegram_bot.send_message.assert_called()


@pytest.mark.asyncio
async def test_scenario2_email_processing_without_approval():
    """Тест обработки письма без подтверждения (автоотправка)"""
    
    mock_email_data = {
        "subject": "Запрос",
        "body": "Нужна помощь",
        "from": "client@example.com"
    }
    
    with patch('services.agents.scenario_workflows.classify_email', new_callable=AsyncMock) as mock_classify_email, \
         patch('services.agents.scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.scenario_workflows.generate_proposal', new_callable=AsyncMock) as mock_proposal, \
         patch('services.agents.scenario_workflows.send_email', new_callable=AsyncMock) as mock_send_email, \
         patch('services.agents.scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag:
        
        mock_classify_email.return_value = "new_lead"
        mock_classify.return_value = {"category": "бизнес-анализ", "confidence": 0.8}
        mock_proposal.return_value = "Предложение..."
        mock_send_email.return_value = True
        mock_create_project.return_value = {"id": "project_789"}
        mock_rag.return_value = None
        
        result = await process_lead_email(mock_email_data, require_approval=False)
        
        assert result["success"] is True
        assert result["approved"] is True
        assert result["email_sent"] is True
        assert result["weeek_project_created"] is True
        
        mock_send_email.assert_called_once()
        mock_create_project.assert_called_once()


# ===================== СЦЕНАРИЙ 3: Заявка с сайта-визитки (Telegram) =====================

@pytest.mark.asyncio
async def test_scenario3_telegram_lead_warm():
    """Тест обработки теплого Telegram лида"""
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    with patch('services.agents.scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('services.agents.scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag, \
         patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '123456'}):
        
        mock_classify.return_value = {"category": "подбор", "confidence": 0.9}
        mock_validate.return_value = {
            "score": 0.8,
            "status": "warm"
        }
        mock_create_project.return_value = {"id": "project_telegram_123"}
        
        mock_rag_instance = Mock()
        mock_rag_instance.query = AsyncMock(return_value={
            "answer": "Ответ по подбору персонала..."
        })
        mock_rag.return_value = mock_rag_instance
        
        result = await process_telegram_lead(
            user_message="Нужен подбор IT-специалиста",
            user_id=12345,
            user_name="Иван",
            telegram_bot=mock_telegram_bot
        )
        
        assert result["success"] is True
        assert result["validation"]["score"] > 0.6
        assert result["weeek_project_created"] is True
        assert "weeek_project_id" in result
        assert result.get("auto_reply_sent", False) is True
        
        # Проверка автоматического ответа пользователю
        send_message_calls = [call for call in mock_telegram_bot.send_message.call_args_list]
        assert len(send_message_calls) >= 1, "Должен быть отправлен автоматический ответ"
        
        # Проверка уведомления консультанта
        assert any("Новый лид через Telegram" in str(call) for call in send_message_calls) or \
               any("консультант" in str(call).lower() for call in send_message_calls)


@pytest.mark.asyncio
async def test_scenario3_telegram_lead_cold():
    """Тест обработки холодного Telegram лида (без создания проекта)"""
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    with patch('services.agents.scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('services.agents.scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag:
        
        mock_classify.return_value = {"category": "другое", "confidence": 0.3}
        mock_validate.return_value = {
            "score": 0.3,
            "status": "cold"
        }
        mock_rag.return_value = None
        
        result = await process_telegram_lead(
            user_message="Общий вопрос",
            user_id=67890,
            user_name="Петр",
            telegram_bot=mock_telegram_bot
        )
        
        assert result["success"] is True
        assert result["validation"]["score"] < 0.6
        assert result.get("weeek_project_created", False) is False
        assert result.get("auto_reply_sent", False) is True  # Автоответ должен быть отправлен даже для холодного лида
        
        # Проект не должен создаваться
        mock_create_project.assert_not_called()
        
        # Автоматический ответ должен быть отправлен
        mock_telegram_bot.send_message.assert_called()
        call_args = mock_telegram_bot.send_message.call_args
        assert call_args.kwargs.get("chat_id") == 67890, "Ответ должен быть отправлен пользователю"


@pytest.mark.asyncio
async def test_scenario3_auto_reply_content():
    """Тест содержания автоматического ответа на заявку"""
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    with patch('services.agents.scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag:
        
        mock_classify.return_value = {"category": "подбор", "confidence": 0.9}
        mock_validate.return_value = {"score": 0.7, "status": "warm"}
        mock_rag.return_value = None
        
        user_message = "Нужна помощь с подбором персонала"
        user_id = 12345
        user_name = "Анна"
        
        result = await process_telegram_lead(
            user_message=user_message,
            user_id=user_id,
            user_name=user_name,
            telegram_bot=mock_telegram_bot
        )
        
        # Проверяем, что автоответ был отправлен
        assert result.get("auto_reply_sent", False) is True
        
        # Проверяем содержание автоответа
        send_message_calls = mock_telegram_bot.send_message.call_args_list
        auto_reply_call = None
        for call in send_message_calls:
            if call.kwargs.get("chat_id") == user_id:
                auto_reply_call = call
                break
        
        assert auto_reply_call is not None, "Автоответ должен быть отправлен пользователю"
        reply_text = auto_reply_call.kwargs.get("text", "")
        assert "Спасибо" in reply_text or "заявку" in reply_text.lower(), "Ответ должен содержать благодарность"
        assert user_name in reply_text, "Ответ должен содержать имя пользователя"


@pytest.mark.asyncio
async def test_project_status_update_on_creation():
    """Тест автоматического обновления статуса проекта при создании"""
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    with patch('services.agents.lead_processor.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.lead_processor.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('services.helpers.weeek_helper.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('services.helpers.weeek_helper.update_project_status', new_callable=AsyncMock) as mock_update_status, \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag, \
         patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '123456'}):
        
        mock_classify.return_value = {"category": "подбор", "confidence": 0.9}
        mock_validate.return_value = {"score": 0.8, "status": "warm"}
        mock_create_project.return_value = {"id": 123, "name": "Тестовый проект"}
        mock_update_status.return_value = True
        
        mock_rag_instance = Mock()
        mock_rag_instance.query = AsyncMock(return_value={"answer": "..."})
        mock_rag.return_value = mock_rag_instance
        
        result = await process_telegram_lead(
            user_message="Нужен подбор персонала",
            user_id=12345,
            user_name="Иван",
            telegram_bot=mock_telegram_bot
        )
        
        # Проверяем, что проект создан
        assert result.get("weeek_project_created") is True
        project_id = result.get("weeek_project_id")
        assert project_id == 123
        
        # Проверяем, что статус был обновлен
        mock_update_status.assert_called_once_with(str(project_id), "new")


@pytest.mark.asyncio
async def test_project_status_update_hrtime_scenario():
    """Тест обновления статуса проекта в сценарии HR Time"""
    
    mock_order_data = {
        "id": "order_789",
        "title": "Подбор менеджера",
        "description": "Нужен менеджер",
        "budget": 50000,
        "client": {"name": "Тест", "email": "test@test.com"}
    }
    
    with patch('services.helpers.hrtime_helper.get_order_details', new_callable=AsyncMock) as mock_get_order, \
         patch('services.agents.lead_processor.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.lead_processor.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('services.agents.lead_processor.generate_proposal', new_callable=AsyncMock) as mock_proposal, \
         patch('services.helpers.hrtime_helper.send_proposal', new_callable=AsyncMock) as mock_send_proposal, \
         patch('services.helpers.email_helper.send_email', new_callable=AsyncMock) as mock_send_email, \
         patch('services.helpers.weeek_helper.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('services.helpers.weeek_helper.create_task', new_callable=AsyncMock) as mock_create_task, \
         patch('services.helpers.weeek_helper.update_project_status', new_callable=AsyncMock) as mock_update_status, \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag:
        
        mock_get_order.return_value = mock_order_data
        mock_classify.return_value = {"category": "подбор", "confidence": 0.9}
        mock_validate.return_value = {"score": 0.85, "status": "warm"}
        mock_proposal.return_value = "КП текст"
        mock_send_proposal.return_value = True
        mock_send_email.return_value = True
        mock_create_project.return_value = {"id": "project_hrtime_123"}
        mock_create_task.return_value = {"id": "task_123"}
        mock_update_status.return_value = True
        
        mock_rag_instance = Mock()
        mock_rag_instance.query = AsyncMock(return_value={"answer": "..."})
        mock_rag.return_value = mock_rag_instance
        
        result = await process_hrtime_order("order_789", order_data=mock_order_data)
        
        # Проверяем, что проект создан
        assert result.get("weeek_project_created") is True
        project_id = result.get("weeek_project_id")
        
        # Проверяем, что статус был обновлен
        mock_update_status.assert_called_once_with(project_id, "new")


# ===================== СЦЕНАРИЙ 4: Напоминание и суммаризация =====================

@pytest.mark.asyncio
async def test_scenario4_deadline_check():
    """Тест проверки дедлайнов и отправки напоминаний"""
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    # Задачи с дедлайнами на сегодня и завтра
    mock_tasks = [
        {
            "id": "task_1",
            "name": "Согласовать КП",
            "project_id": "project_1",
            "due_date": datetime.now().date().isoformat(),
            "status": "in_progress"
        },
        {
            "id": "task_2",
            "name": "Подготовить отчет",
            "project_id": "project_2",
            "due_date": (datetime.now().date() + timedelta(days=1)).isoformat(),
            "status": "todo"
        }
    ]
    
    with patch('services.agents.scenario_workflows.get_project_deadlines', new_callable=AsyncMock) as mock_get_deadlines, \
         patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '123456'}):
        
        mock_get_deadlines.return_value = mock_tasks
        
        result = await check_upcoming_deadlines(telegram_bot=mock_telegram_bot, days_ahead=1)
        
        # Проверка, что задачи найдены
        assert len(result) > 0
        
        # Проверка отправки напоминания
        mock_telegram_bot.send_message.assert_called()


@pytest.mark.asyncio
async def test_scenario4_no_deadlines():
    """Тест, когда нет задач с дедлайнами"""
    
    mock_telegram_bot = AsyncMock()
    
    with patch('services.agents.scenario_workflows.get_project_deadlines', new_callable=AsyncMock) as mock_get_deadlines:
        mock_get_deadlines.return_value = []
        
        result = await check_upcoming_deadlines(telegram_bot=mock_telegram_bot, days_ahead=1)
        
        assert result == []
        # Напоминание не должно отправляться
        mock_telegram_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_scenario4_project_summary():
    """Тест суммаризации проекта"""
    
    mock_conversations = [
        {
            "role": "user",
            "content": "Нужна помощь с подбором персонала",
            "timestamp": "2025-12-15 10:00:00"
        },
        {
            "role": "assistant",
            "content": "Конечно! Расскажите подробнее о требованиях",
            "timestamp": "2025-12-15 10:01:00"
        },
        {
            "role": "user",
            "content": "Нужен HR-менеджер с опытом работы в IT",
            "timestamp": "2025-12-15 10:05:00"
        }
    ]
    
    with patch('services.agents.scenario_workflows.summarize_project_conversation', new_callable=AsyncMock) as mock_summarize:
        mock_summarize.return_value = "Суммаризация: Клиент запросил подбор HR-менеджера для IT компании..."
        
        result = await summarize_project_by_name(
            project_name="Подбор HR-менеджера",
            conversations=mock_conversations
        )
        
        assert result["success"] is True
        assert result["project_name"] == "Подбор HR-менеджера"
        assert "summary" in result
        assert len(result["summary"]) > 0


# ===================== Интеграционные тесты =====================

@pytest.mark.asyncio
async def test_full_scenario1_integration():
    """Интеграционный тест Сценария 1 (полный цикл)"""
    
    # Используем реальные функции, но мокируем внешние зависимости (API)
    # Это проверяет логику связывания всех шагов
    
    mock_order_data = {
        "id": "order_integration_test",
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
    
    # Мокируем только внешние API, оставляя внутреннюю логику
    with patch('services.agents.scenario_workflows.send_proposal', new_callable=AsyncMock) as mock_send, \
         patch('services.agents.scenario_workflows.send_email', new_callable=AsyncMock) as mock_email, \
         patch('services.agents.scenario_workflows.create_project', new_callable=AsyncMock) as mock_project, \
         patch('services.agents.scenario_workflows.create_task', new_callable=AsyncMock) as mock_task:
        
        mock_send.return_value = True
        mock_email.return_value = True
        mock_project.return_value = {"id": "project_integration"}
        mock_task.return_value = {"id": "task_integration"}
        
        result = await process_hrtime_order("order_integration_test", order_data=mock_order_data)
        
        # Проверка полного цикла
        assert result["success"] is True
        assert "classification" in result
        assert "validation" in result
        
        # Для теплого лида должны выполниться действия
        if result["validation"].get("score", 0) > 0.6:
            assert result["proposal_sent"] is True
            assert result["weeek_project_created"] is True


# ===================== Тест отправки лидов в канал =====================

@pytest.mark.asyncio
async def test_lead_sent_to_channel_hrtime():
    """Тест отправки лида из HR Time в канал HRAI_ANovoselova_Лиды"""
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    mock_order_data = {
        "id": "order_channel_test",
        "title": "Подбор HR-менеджера",
        "description": "Нужен опытный HR-менеджер. Бюджет: 100000 руб.",
        "budget": 100000,
        "client": {
            "name": "Иван Иванов",
            "email": "ivan@example.com",
            "phone": "+79001234567"
        }
    }
    
    with patch('services.helpers.hrtime_helper.get_order_details', new_callable=AsyncMock) as mock_get_order, \
         patch('services.agents.lead_processor.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.lead_processor.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('services.agents.lead_processor.generate_proposal', new_callable=AsyncMock) as mock_proposal, \
         patch('services.helpers.hrtime_helper.send_proposal', new_callable=AsyncMock) as mock_send_proposal, \
         patch('services.helpers.email_helper.send_email', new_callable=AsyncMock) as mock_send_email, \
         patch('services.helpers.weeek_helper.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('services.helpers.weeek_helper.create_task', new_callable=AsyncMock) as mock_create_task, \
         patch('services.helpers.weeek_helper.update_project_status', new_callable=AsyncMock) as mock_update_status, \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag, \
         patch('services.services.hrtime_order_parser.HRTimeOrderParser.parse_order', new_callable=AsyncMock) as mock_parser, \
         patch('services.services.hrtime_lead_validator.HRTimeLeadValidator.validate_lead_with_questions', new_callable=AsyncMock) as mock_validator, \
         patch('services.agents.scenario_workflows.TELEGRAM_LEADS_CHANNEL_ID', '-1001234567890'):
        
        mock_get_order.return_value = mock_order_data
        mock_classify.return_value = {"category": "подбор", "confidence": 0.9}
        mock_validate.return_value = {
            "score": 0.85,
            "status": "warm",
            "reason": "Четкое ТЗ"
        }
        mock_proposal.return_value = "Коммерческое предложение..."
        mock_send_proposal.return_value = True
        mock_send_email.return_value = True
        mock_create_project.return_value = {"id": 123}
        mock_create_task.return_value = {"id": "task_123"}
        mock_update_status.return_value = True
        mock_parser.return_value = {"success": False}  # Отключаем парсер
        mock_validator.return_value = {"validation": mock_validate.return_value, "needs_clarification": False}
        
        mock_rag_instance = Mock()
        mock_rag_instance.query = AsyncMock(return_value={"answer": "..."})
        mock_rag.return_value = mock_rag_instance
        
        # Выполнение теста
        result = await process_hrtime_order("order_channel_test", order_data=mock_order_data, telegram_bot=mock_telegram_bot)
        
        # Проверки
        assert result["success"] is True
        
        # Проверяем, что сообщение было отправлено в канал лидов
        send_message_calls = mock_telegram_bot.send_message.call_args_list
        
        # Должно быть минимум одно сообщение в канал лидов
        channel_calls = [
            call for call in send_message_calls 
            if call.kwargs.get("chat_id") == "-1001234567890"
        ]
        
        assert len(channel_calls) > 0, "Сообщение должно быть отправлено в канал лидов"
        
        # Проверяем содержание сообщения
        channel_message = channel_calls[0].kwargs.get("text", "")
        assert "Новый лид" in channel_message
        assert "Иван Иванов" in channel_message
        assert "ivan@example.com" in channel_message
        assert "подбор" in channel_message.lower()


@pytest.mark.asyncio
async def test_lead_sent_to_channel_telegram():
    """Тест отправки лида из Telegram бота в канал HRAI_ANovoselova_Лиды"""
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    with patch('services.agents.scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('services.agents.scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('services.helpers.weeek_helper.update_project_status', new_callable=AsyncMock) as mock_update_status, \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag, \
         patch('services.agents.scenario_workflows.TELEGRAM_LEADS_CHANNEL_ID', '-1001234567890'), \
         patch('services.agents.scenario_workflows.TELEGRAM_CONSULTANT_CHAT_ID', '123456'):
        
        mock_classify.return_value = {"category": "подбор", "confidence": 0.9}
        mock_validate.return_value = {"score": 0.8, "status": "warm"}
        mock_create_project.return_value = {"id": 456}
        mock_update_status.return_value = True
        
        mock_rag_instance = Mock()
        mock_rag_instance.query = AsyncMock(return_value={"answer": "..."})
        mock_rag.return_value = mock_rag_instance
        
        # Выполнение теста
        result = await process_telegram_lead(
            user_message="Нужен подбор IT-специалиста",
            user_id=12345,
            user_name="Петр",
            telegram_bot=mock_telegram_bot
        )
        
        # Проверки
        assert result["success"] is True
        assert result["validation"]["score"] > 0.6
        
        # Проверяем, что сообщение было отправлено в канал лидов
        send_message_calls = mock_telegram_bot.send_message.call_args_list
        
        channel_calls = [
            call for call in send_message_calls 
            if call.kwargs.get("chat_id") == "-1001234567890"
        ]
        
        assert len(channel_calls) > 0, "Сообщение должно быть отправлено в канал лидов"
        
        # Проверяем содержание сообщения
        channel_message = channel_calls[0].kwargs.get("text", "")
        assert "Новый лид" in channel_message
        assert "Петр" in channel_message
        assert "Telegram бот" in channel_message
        assert "подбор" in channel_message.lower()


@pytest.mark.asyncio
async def test_lead_sent_to_channel_email():
    """Тест отправки лида из Email в канал HRAI_ANovoselova_Лиды"""
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    mock_email_data = {
        "subject": "Запрос на консультацию",
        "body": "Нужна помощь с автоматизацией HR-процессов",
        "from": "client@example.com"
    }
    
    with patch('services.helpers.email_helper.classify_email', new_callable=AsyncMock) as mock_classify_email, \
         patch('services.agents.lead_processor.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.lead_processor.generate_proposal', new_callable=AsyncMock) as mock_proposal, \
         patch('services.helpers.email_helper.send_email', new_callable=AsyncMock) as mock_send_email, \
         patch('services.helpers.weeek_helper.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('services.helpers.weeek_helper.update_project_status', new_callable=AsyncMock) as mock_update_status, \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag, \
         patch('services.agents.scenario_workflows.TELEGRAM_LEADS_CHANNEL_ID', '-1001234567890'):
        
        mock_classify_email.return_value = "new_lead"
        mock_classify.return_value = {"category": "автоматизация", "confidence": 0.9}
        mock_proposal.return_value = "Предложение по автоматизации..."
        mock_send_email.return_value = True
        mock_create_project.return_value = {"id": "project_789"}
        mock_update_status.return_value = True
        mock_rag.return_value = None
        
        # Выполнение теста
        result = await process_lead_email(mock_email_data, require_approval=False, telegram_bot=mock_telegram_bot)
        
        # Проверки
        assert result["success"] is True
        assert result["email_sent"] is True
        
        # Проверяем, что сообщение было отправлено в канал лидов
        send_message_calls = mock_telegram_bot.send_message.call_args_list
        
        channel_calls = [
            call for call in send_message_calls 
            if call.kwargs.get("chat_id") == "-1001234567890"
        ]
        
        assert len(channel_calls) > 0, "Сообщение должно быть отправлено в канал лидов"
        
        # Проверяем содержание сообщения
        channel_message = channel_calls[0].kwargs.get("text", "")
        assert "Новый лид" in channel_message
        assert "client@example.com" in channel_message
        assert "Email" in channel_message


@pytest.mark.asyncio
async def test_cold_lead_sent_to_channel():
    """Тест отправки холодного лида в канал HRAI_ANovoselova_Лиды"""
    
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock()
    
    mock_order_data = {
        "id": "order_cold_test",
        "title": "Общий вопрос",
        "description": "Интересует консалтинг",
        "client": {"name": "Тест", "email": "test@example.com"}
    }
    
    with patch('services.helpers.hrtime_helper.get_order_details', new_callable=AsyncMock) as mock_get_order, \
         patch('services.agents.lead_processor.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.lead_processor.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag, \
         patch('services.services.hrtime_order_parser.HRTimeOrderParser.parse_order', new_callable=AsyncMock) as mock_parser, \
         patch('services.services.hrtime_lead_validator.HRTimeLeadValidator.validate_lead_with_questions', new_callable=AsyncMock) as mock_validator, \
         patch('services.agents.scenario_workflows.TELEGRAM_LEADS_CHANNEL_ID', '-1001234567890'):
        
        mock_get_order.return_value = mock_order_data
        mock_classify.return_value = {"category": "другое", "confidence": 0.5}
        mock_validate.return_value = {
            "score": 0.3,
            "status": "cold",
            "reason": "Недостаточно информации"
        }
        mock_rag.return_value = None
        mock_parser.return_value = {"success": False}  # Отключаем парсер
        mock_validator.return_value = {"validation": mock_validate.return_value, "needs_clarification": False}
        
        # Выполнение теста
        result = await process_hrtime_order("order_cold_test", order_data=mock_order_data, telegram_bot=mock_telegram_bot)
        
        # Проверки
        assert result["success"] is True
        assert result["validation"]["score"] < 0.6
        
        # Проверяем, что холодный лид тоже был отправлен в канал
        send_message_calls = mock_telegram_bot.send_message.call_args_list
        
        channel_calls = [
            call for call in send_message_calls 
            if call.kwargs.get("chat_id") == "-1001234567890"
        ]
        
        assert len(channel_calls) > 0, "Холодный лид тоже должен быть отправлен в канал лидов"
        
        # Проверяем содержание сообщения
        channel_message = channel_calls[0].kwargs.get("text", "")
        assert "Новый лид" in channel_message
        assert "cold" in channel_message.lower() or "0.3" in channel_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


