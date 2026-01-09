"""
Комплексный тест полного workflow обработки лида с HR Time
Проверяет все 6 шагов согласно требованиям
"""
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для импорта модулей
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Импорты для тестирования
from services.agents.scenario_workflows import process_hrtime_order
from services.services.hrtime_order_parser import HRTimeOrderParser
from services.services.hrtime_lead_validator import HRTimeLeadValidator


@pytest.mark.asyncio
async def test_full_hrtime_lead_workflow_all_steps():
    """
    Комплексный тест полного workflow обработки лида с HR Time
    Проверяет все 6 шагов:
    1. Парсинг данных заказа
    2. RAG + Классификация
    3. Валидация с уточняющими вопросами
    4. Действия для теплого лида (отклик, КП, WEEEK)
    5. Создание проекта в WEEEK
    6. Уведомление консультанта в Telegram
    """
    
    # ===================== ПОДГОТОВКА ДАННЫХ =====================
    
    # Мок данных заказа из HR Time
    mock_order_data = {
        "id": "order_test_123",
        "title": "Подбор IT-специалиста",
        "description": """
        Требуется опытный Python-разработчик для работы над проектом автоматизации HR-процессов.
        Обязательные требования:
        - Опыт работы с Python 3+ лет
        - Знание FastAPI, PostgreSQL
        - Опыт работы с LLM и RAG системами
        
        Бюджет: 200000 рублей
        Срок: до 15 января 2026 года
        
        Контакты:
        Клиент: Петр Петров
        Email: petr@company.com
        Телефон: +7 900 123 45 67
        """,
        "budget": "200000 руб",
        "deadline": "2026-01-15",
        "client": {
            "name": "Петр Петров",
            "email": "petr@company.com",
            "phone": "+7 900 123 45 67"
        },
        "source": "telegram_channel"
    }
    
    # Мок Telegram бота для уведомлений
    mock_telegram_bot = AsyncMock()
    mock_telegram_bot.send_message = AsyncMock(return_value=Mock(id=1))
    
    # ===================== МОКИ ДЛЯ ВСЕХ ЗАВИСИМОСТЕЙ =====================
    
    # Патчим создание экземпляров парсера и валидатора
    with patch('services.agents.scenario_workflows.HRTIME_AVAILABLE', True), \
         patch('services.agents.scenario_workflows.PARSER_AVAILABLE', True), \
         patch('services.agents.scenario_workflows.VALIDATOR_AVAILABLE', True), \
         patch('services.agents.scenario_workflows.WEEEK_AVAILABLE', True), \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag_chain, \
         patch('services.agents.scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate_base, \
         patch('services.agents.scenario_workflows.generate_proposal', new_callable=AsyncMock) as mock_generate_proposal, \
         patch('services.agents.scenario_workflows.send_proposal', new_callable=AsyncMock) as mock_send_proposal, \
         patch('services.agents.scenario_workflows.send_email', new_callable=AsyncMock) as mock_send_email, \
         patch('services.agents.scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project, \
         patch('services.agents.scenario_workflows.create_task', new_callable=AsyncMock) as mock_create_task, \
         patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '123456789'}):
        
        # ===================== ШАГ 1: МОК ПАРСИНГА =====================
        
        # Мок парсера заказа через LLM
        mock_parsed_result = {
            "order_id": "order_test_123",
            "parsed": {
                "requirements": "Требуется опытный Python-разработчик для работы над проектом автоматизации HR-процессов. Обязательные требования: опыт работы с Python 3+ лет, знание FastAPI, PostgreSQL, опыт работы с LLM и RAG системами.",
                "budget": {
                    "amount": 200000.0,
                    "currency": "RUB",
                    "text": "200000 рублей"
                },
                "deadline": {
                    "date": "2026-01-15",
                    "text": "до 15 января 2026 года"
                },
                "contacts": {
                    "full_name": "Петр Петров",
                    "phone": "+7 900 123 45 67",
                    "email": "petr@company.com"
                },
                "raw_data": mock_order_data
            },
            "success": True,
            "error": None
        }
        
        # Патчим создание парсера и валидатора
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_order = AsyncMock(return_value=mock_parsed_result)
        
        mock_validation_result = {
            "validation": {
                "score": 0.85,
                "status": "warm",
                "reason": "Четкое ТЗ, указан бюджет и сроки",
                "criteria": {
                    "clarity": 0.9,
                    "budget": 0.8,
                    "relevance": 0.85
                }
            },
            "needs_clarification": False,
            "questions": [],
            "missing_info": [],
            "can_ask_questions": False
        }
        
        mock_validator_instance = MagicMock()
        mock_validator_instance.validate_lead_with_questions = AsyncMock(return_value=mock_validation_result)
        mock_validator_instance.ask_clarification_questions = AsyncMock(return_value={
            "success": False,
            "method": "none",
            "error": "Placeholder - не реализовано"
        })
        
        # Патчим импорты в scenario_workflows напрямую
        import services.agents.scenario_workflows as sw_module
        original_parser = getattr(sw_module, 'HRTimeOrderParser', None)
        original_validator = getattr(sw_module, 'HRTimeLeadValidator', None)
        
        # Устанавливаем классы в модуль
        sw_module.HRTimeOrderParser = lambda: mock_parser_instance
        sw_module.HRTimeLeadValidator = lambda: mock_validator_instance
        
        try:
            
            # ===================== ШАГ 2: МОК RAG + КЛАССИФИКАЦИЯ =====================
            
            # Мок RAG chain
            mock_rag_instance = MagicMock()
            mock_rag_instance.query = AsyncMock(return_value={
                "answer": "Релевантная информация о подборе IT-специалистов: средняя зарплата Python-разработчика 150-250k, требования к опыту обычно 3+ лет...",
                "sources": ["hr_knowledge_base", "pricing_guide"],
                "context_count": 5
            })
            mock_rag_chain.return_value = mock_rag_instance
            
            # Мок классификации
            mock_classify.return_value = {
                "category": "подбор ИТ-специалиста",
                "confidence": 0.95,
                "keywords": ["Python", "разработчик", "IT", "программист"]
            }
            
            # Базовый мок валидации (для fallback)
            mock_validate_base.return_value = {
                "score": 0.85,
                "status": "warm",
                "reason": "Четкое ТЗ, указан бюджет и сроки"
            }
            
            # ===================== ШАГ 4: МОК ДЕЙСТВИЙ ДЛЯ ТЕПЛОГО ЛИДА =====================
            
            # Мок генерации КП
            mock_generate_proposal.return_value = """
            Здравствуйте, Петр!
            
            Благодарим за обращение по заказу "Подбор IT-специалиста".
            
            Мы проанализировали вашу задачу и готовы предложить следующее решение:
            
            1. Поиск и отбор кандидатов: 7-10 дней
            2. Проведение технических интервью: 3-5 дней
            3. Предоставление финальных кандидатов: 2-3 дня
            
            Предварительная стоимость: 200000 рублей
            Срок выполнения: до 15 января 2026 года
            
            Готовы обсудить детали и ответить на ваши вопросы.
            
            С уважением,
            Анастасия Новосёлова
            """
            
            # Мок отправки отклика на HR Time
            mock_send_proposal.return_value = True
            
            # Мок отправки КП по email
            mock_send_email.return_value = True
            
            # ===================== ШАГ 5: МОК WEEEK =====================
            
            # Мок создания проекта в WEEEK
            mock_create_project.return_value = {
                "id": "weeek_project_123",
                "title": "Подбор IT-специалиста — HR Time",
                "description": "Заказ с HR Time\n\nТребуется опытный Python-разработчик..."
            }
            
            # Мок создания задачи в WEEEK
            mock_create_task.return_value = {
                "id": "weeek_task_123",
                "name": "Согласовать КП",
                "project_id": "weeek_project_123"
            }
            
            # ===================== ВЫПОЛНЕНИЕ ТЕСТА =====================
            
            result = await process_hrtime_order("order_test_123", order_data=mock_order_data)
            
            # ===================== ПРОВЕРКИ =====================
            
            # Общая проверка успешности
            assert result["success"] is True, "Workflow должен завершиться успешно"
            assert result["order_id"] == "order_test_123", "ID заказа должен совпадать"
            
            # ШАГ 1: Проверка парсинга
            assert "parsed_order" in result, "Должен быть результат парсинга"
            assert result["parsed_order"]["success"] is True, "Парсинг должен быть успешным"
            parsed = result["parsed_order"]["parsed"]
            assert parsed["contacts"]["full_name"] == "Петр Петров", "Должно быть извлечено ФИО"
            assert parsed["contacts"]["email"] == "petr@company.com", "Должен быть извлечен email"
            assert parsed["contacts"]["phone"] == "+7 900 123 45 67", "Должен быть извлечен телефон"
            assert parsed["budget"]["amount"] == 200000.0, "Должен быть извлечен бюджет"
            assert parsed["deadline"]["date"] == "2026-01-15", "Должна быть извлечена дата дедлайна"
            assert len(parsed["requirements"]) > 0, "Должен быть извлечен текст ТЗ"
            
            # Проверка вызова парсера (может быть вызван несколько раз)
            assert mock_parser_instance.parse_order.called, "Парсер должен быть вызван"
            
            # ШАГ 2: Проверка RAG + Классификации
            assert "classification" in result, "Должна быть выполнена классификация"
            assert result["classification"]["category"] == "подбор ИТ-специалиста", "Категория должна быть определена"
            assert result["classification"]["confidence"] > 0.8, "Уверенность классификации должна быть высокой"
            
            # Проверка вызова RAG
            mock_rag_instance.query.assert_called()
            
            # Проверка вызова классификации
            mock_classify.assert_called()
            
            # ШАГ 3: Проверка валидации
            assert "validation" in result, "Должна быть выполнена валидация"
            assert result["validation"]["score"] > 0.6, "Score должен быть выше порога теплого лида"
            assert result["validation"]["status"] == "warm", "Статус должен быть 'warm'"
            
            # Проверка вызова валидатора
            mock_validator_instance.validate_lead_with_questions.assert_called()
            
            # ШАГ 4: Проверка действий для теплого лида
            assert result["proposal_sent"] is True, "Отклик должен быть отправлен на HR Time"
            assert mock_send_proposal.called, "Должен быть вызван send_proposal"
            
            # Проверка отправки КП по email
            assert mock_send_email.called, "КП должно быть отправлено по email"
            email_call_args = mock_send_email.call_args
            assert email_call_args[1]["to_email"] == "petr@company.com", "Email должен быть отправлен клиенту"
            assert "Коммерческое предложение" in email_call_args[1]["subject"], "Тема должна содержать 'Коммерческое предложение'"
            
            # Проверка генерации КП
            mock_generate_proposal.assert_called()
            
            # ШАГ 5: Проверка создания проекта в WEEEK
            assert result["weeek_project_created"] is True, "Проект должен быть создан в WEEEK"
            assert "weeek_project_id" in result, "Должен быть ID проекта в WEEEK"
            assert result["weeek_project_id"] == "weeek_project_123", "ID проекта должен совпадать"
            
            # Проверка вызова создания проекта (может быть вызван несколько раз)
            assert mock_create_project.called, "Проект должен быть создан"
            project_call_args = mock_create_project.call_args
            assert "Подбор IT-специалиста — HR Time" in project_call_args[1]["name"], "Название проекта должно содержать название заказа"
            
            # Проверка создания задачи "Согласовать КП" (может быть вызван несколько раз)
            assert mock_create_task.called, "Задача должна быть создана"
            task_call_args = mock_create_task.call_args
            assert task_call_args[1]["title"] == "Согласовать КП", "Должна быть создана задача 'Согласовать КП'"
            assert task_call_args[1]["project_id"] == "weeek_project_123", "Задача должна быть в созданном проекте"
            
            # ШАГ 6: Проверка уведомления консультанта
            assert "notification_text" in result, "Должен быть подготовлен текст уведомления"
            assert result["notification_sent"] is True, "Уведомление должно быть помечено как отправленное"
            
            notification_text = result["notification_text"]
            assert "Новый теплый лид с HR Time" in notification_text, "Уведомление должно содержать заголовок"
            assert "Подбор IT-специалиста" in notification_text, "Уведомление должно содержать название заказа"
            assert "Петр Петров" in notification_text, "Уведомление должно содержать имя клиента"
            assert "petr@company.com" in notification_text, "Уведомление должно содержать email клиента"
            assert "Отклик и черновик КП отправлены" in notification_text, "Уведомление должно подтверждать отправку"
            assert "Проект создан в WEEEK" in notification_text, "Уведомление должно подтверждать создание проекта"
            assert "Требует вашего ознакомления с КП" in notification_text, "Уведомление должно содержать требование ознакомления"
            
            # Проверка источника данных (канал или API)
            assert "@HRTime_bot" in notification_text or "HR Time API" in notification_text, "Уведомление должно указывать источник"
            
            print("\n✅ Все 6 шагов workflow успешно проверены:")
            print("  1. ✅ Парсинг данных заказа (ТЗ, бюджет, сроки, контакты)")
            print("  2. ✅ RAG + Классификация (категория: подбор ИТ-специалиста)")
            print("  3. ✅ Валидация лида (score: 0.85, status: warm)")
            print("  4. ✅ Действия для теплого лида (отклик на HR Time, КП по email)")
            print("  5. ✅ Создание проекта в WEEEK с задачей 'Согласовать КП'")
            print("  6. ✅ Уведомление консультанта в Telegram")
        finally:
            # Восстанавливаем оригинальные классы
            if original_parser is not None:
                sw_module.HRTimeOrderParser = original_parser
            if original_validator is not None:
                sw_module.HRTimeLeadValidator = original_validator
        
        # Базовый мок валидации (для fallback)
        mock_validate_base.return_value = {
            "score": 0.85,
            "status": "warm",
            "reason": "Четкое ТЗ, указан бюджет и сроки"
        }
        
        # ===================== ШАГ 4: МОК ДЕЙСТВИЙ ДЛЯ ТЕПЛОГО ЛИДА =====================
        
        # Мок генерации КП
        mock_generate_proposal.return_value = """
        Здравствуйте, Петр!
        
        Благодарим за обращение по заказу "Подбор IT-специалиста".
        
        Мы проанализировали вашу задачу и готовы предложить следующее решение:
        
        1. Поиск и отбор кандидатов: 7-10 дней
        2. Проведение технических интервью: 3-5 дней
        3. Предоставление финальных кандидатов: 2-3 дня
        
        Предварительная стоимость: 200000 рублей
        Срок выполнения: до 15 января 2026 года
        
        Готовы обсудить детали и ответить на ваши вопросы.
        
        С уважением,
        Анастасия Новосёлова
        """
        
        # Мок отправки отклика на HR Time
        mock_send_proposal.return_value = True
        
        # Мок отправки КП по email
        mock_send_email.return_value = True
        
        # ===================== ШАГ 5: МОК WEEEK =====================
        
        # Мок создания проекта в WEEEK
        mock_create_project.return_value = {
            "id": "weeek_project_123",
            "title": "Подбор IT-специалиста — HR Time",
            "description": "Заказ с HR Time\n\nТребуется опытный Python-разработчик..."
        }
        
        # Мок создания задачи в WEEEK
        mock_create_task.return_value = {
            "id": "weeek_task_123",
            "name": "Согласовать КП",
            "project_id": "weeek_project_123"
        }
        
        # ===================== ВЫПОЛНЕНИЕ ТЕСТА =====================
        
        result = await process_hrtime_order("order_test_123", order_data=mock_order_data)
        
        # ===================== ПРОВЕРКИ =====================
        
        # Общая проверка успешности
        assert result["success"] is True, "Workflow должен завершиться успешно"
        assert result["order_id"] == "order_test_123", "ID заказа должен совпадать"
        
        # ШАГ 1: Проверка парсинга
        assert "parsed_order" in result, "Должен быть результат парсинга"
        assert result["parsed_order"]["success"] is True, "Парсинг должен быть успешным"
        parsed = result["parsed_order"]["parsed"]
        assert parsed["contacts"]["full_name"] == "Петр Петров", "Должно быть извлечено ФИО"
        assert parsed["contacts"]["email"] == "petr@company.com", "Должен быть извлечен email"
        assert parsed["contacts"]["phone"] == "+7 900 123 45 67", "Должен быть извлечен телефон"
        assert parsed["budget"]["amount"] == 200000.0, "Должен быть извлечен бюджет"
        assert parsed["deadline"]["date"] == "2026-01-15", "Должна быть извлечена дата дедлайна"
        assert len(parsed["requirements"]) > 0, "Должен быть извлечен текст ТЗ"
        
        # Проверка вызова парсера (может быть вызван несколько раз)
        assert mock_parser_instance.parse_order.called, "Парсер должен быть вызван"
        
        # ШАГ 2: Проверка RAG + Классификации
        assert "classification" in result, "Должна быть выполнена классификация"
        assert result["classification"]["category"] == "подбор ИТ-специалиста", "Категория должна быть определена"
        assert result["classification"]["confidence"] > 0.8, "Уверенность классификации должна быть высокой"
        
        # Проверка вызова RAG
        mock_rag_instance.query.assert_called()
        
        # Проверка вызова классификации
        mock_classify.assert_called()
        
        # ШАГ 3: Проверка валидации
        assert "validation" in result, "Должна быть выполнена валидация"
        assert result["validation"]["score"] > 0.6, "Score должен быть выше порога теплого лида"
        assert result["validation"]["status"] == "warm", "Статус должен быть 'warm'"
        
        # Проверка вызова валидатора
        mock_validator_instance.validate_lead_with_questions.assert_called()
        
        # ШАГ 4: Проверка действий для теплого лида
        assert result["proposal_sent"] is True, "Отклик должен быть отправлен на HR Time"
        assert mock_send_proposal.called, "Должен быть вызван send_proposal"
        
        # Проверка отправки КП по email
        assert mock_send_email.called, "КП должно быть отправлено по email"
        email_call_args = mock_send_email.call_args
        assert email_call_args[1]["to_email"] == "petr@company.com", "Email должен быть отправлен клиенту"
        assert "Коммерческое предложение" in email_call_args[1]["subject"], "Тема должна содержать 'Коммерческое предложение'"
        
        # Проверка генерации КП
        mock_generate_proposal.assert_called()
        
        # ШАГ 5: Проверка создания проекта в WEEEK
        assert result["weeek_project_created"] is True, "Проект должен быть создан в WEEEK"
        assert "weeek_project_id" in result, "Должен быть ID проекта в WEEEK"
        assert result["weeek_project_id"] == "weeek_project_123", "ID проекта должен совпадать"
        
        # Проверка вызова создания проекта (может быть вызван несколько раз)
        assert mock_create_project.called, "Проект должен быть создан"
        project_call_args = mock_create_project.call_args
        assert "Подбор IT-специалиста — HR Time" in project_call_args[1]["name"], "Название проекта должно содержать название заказа"
        
        # Проверка создания задачи "Согласовать КП" (может быть вызван несколько раз)
        assert mock_create_task.called, "Задача должна быть создана"
        task_call_args = mock_create_task.call_args
        assert task_call_args[1]["title"] == "Согласовать КП", "Должна быть создана задача 'Согласовать КП'"
        assert task_call_args[1]["project_id"] == "weeek_project_123", "Задача должна быть в созданном проекте"
        
        # ШАГ 6: Проверка уведомления консультанта
        assert "notification_text" in result, "Должен быть подготовлен текст уведомления"
        assert result["notification_sent"] is True, "Уведомление должно быть помечено как отправленное"
        
        notification_text = result["notification_text"]
        assert "Новый теплый лид с HR Time" in notification_text, "Уведомление должно содержать заголовок"
        assert "Подбор IT-специалиста" in notification_text, "Уведомление должно содержать название заказа"
        assert "Петр Петров" in notification_text, "Уведомление должно содержать имя клиента"
        assert "petr@company.com" in notification_text, "Уведомление должно содержать email клиента"
        assert "Отклик и черновик КП отправлены" in notification_text, "Уведомление должно подтверждать отправку"
        assert "Проект создан в WEEEK" in notification_text, "Уведомление должно подтверждать создание проекта"
        assert "Требует вашего ознакомления с КП" in notification_text, "Уведомление должно содержать требование ознакомления"
        
        # Проверка источника данных (канал или API)
        assert "@HRTime_bot" in notification_text or "HR Time API" in notification_text, "Уведомление должно указывать источник"
        
        print("\n✅ Все 6 шагов workflow успешно проверены:")
        print("  1. ✅ Парсинг данных заказа (ТЗ, бюджет, сроки, контакты)")
        print("  2. ✅ RAG + Классификация (категория: подбор ИТ-специалиста)")
        print("  3. ✅ Валидация лида (score: 0.85, status: warm)")
        print("  4. ✅ Действия для теплого лида (отклик на HR Time, КП по email)")
        print("  5. ✅ Создание проекта в WEEEK с задачей 'Согласовать КП'")
        print("  6. ✅ Уведомление консультанта в Telegram")


@pytest.mark.asyncio
async def test_full_workflow_with_clarification_questions():
    """
    Тест workflow с уточняющими вопросами (когда нужна дополнительная информация)
    """
    
    mock_order_data = {
        "id": "order_test_456",
        "title": "Консультация по HR",
        "description": "Нужна консультация по автоматизации HR-процессов",
        "client": {
            "name": "Иван Иванов",
            "email": "ivan@test.com"
        }
    }
    
    with patch('services.agents.scenario_workflows.HRTIME_AVAILABLE', True), \
         patch('services.agents.scenario_workflows.PARSER_AVAILABLE', True), \
         patch('services.agents.scenario_workflows.VALIDATOR_AVAILABLE', True), \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag, \
         patch('services.agents.scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('services.agents.scenario_workflows.send_message', new_callable=AsyncMock) as mock_send_message:
        
        # Мок парсера
        mock_parser = MagicMock()
        mock_parser.parse_order = AsyncMock(return_value={
            "success": True,
            "parsed": {
                "requirements": "Нужна консультация",
                "budget": {"amount": 0, "text": ""},
                "deadline": {"date": None, "text": ""},
                "contacts": {"full_name": "Иван Иванов", "email": "ivan@test.com", "phone": ""}
            }
        })
        
        # Мок валидатора с уточняющими вопросами
        mock_validator = MagicMock()
        mock_validator.validate_lead_with_questions = AsyncMock(return_value={
            "validation": {"score": 0.5, "status": "cold"},
            "needs_clarification": True,
            "questions": [
                "Какой примерный бюджет на проект?",
                "Какие сроки реализации проекта?"
            ],
            "missing_info": ["бюджет", "сроки"],
            "can_ask_questions": False
        })
        mock_validator.ask_clarification_questions = AsyncMock(return_value={
            "success": False,
            "method": "none",
            "questions_text": "1. Какой примерный бюджет на проект?\n2. Какие сроки реализации проекта?"
        })
        
        # Патчим импорты в scenario_workflows
        import services.agents.scenario_workflows as sw_module
        sw_module.HRTimeOrderParser = lambda: mock_parser
        sw_module.HRTimeLeadValidator = lambda: mock_validator
        
        try:
            mock_rag.return_value = None
            mock_classify.return_value = {"category": "автоматизация", "confidence": 0.7}
            mock_validate.return_value = {"score": 0.5, "status": "cold"}
            
            result = await process_hrtime_order("order_test_456", order_data=mock_order_data)
            
            # Проверка, что валидатор был вызван
            mock_validator.validate_lead_with_questions.assert_called()
            
            # Проверка, что для холодного лида не выполняются действия
            assert result["success"] is True
            assert result["validation"]["score"] < 0.6
            assert result.get("proposal_sent", False) is False
        finally:
            # Восстанавливаем оригинальные классы
            if hasattr(sw_module, 'HRTimeOrderParser'):
                delattr(sw_module, 'HRTimeOrderParser')
            if hasattr(sw_module, 'HRTimeLeadValidator'):
                delattr(sw_module, 'HRTimeLeadValidator')


@pytest.mark.asyncio
async def test_full_workflow_cold_lead_no_actions():
    """
    Тест, что для холодного лида не выполняются действия (шаги 4-6)
    """
    
    mock_order_data = {
        "id": "order_test_789",
        "title": "Общий вопрос",
        "description": "Интересует консалтинг",
        "client": {"name": "Тест", "email": "test@test.com"}
    }
    
    with patch('services.agents.scenario_workflows.HRTIME_AVAILABLE', True), \
         patch('services.agents.scenario_workflows.PARSER_AVAILABLE', True), \
         patch('services.agents.scenario_workflows.get_rag_chain') as mock_rag, \
         patch('services.agents.scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
         patch('services.agents.scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
         patch('services.agents.scenario_workflows.send_proposal', new_callable=AsyncMock) as mock_send_proposal, \
         patch('services.agents.scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project:
        
        mock_parser = MagicMock()
        mock_parser.parse_order = AsyncMock(return_value={
            "success": True,
            "parsed": {
                "requirements": "Интересует консалтинг",
                "budget": {"amount": 0, "text": ""},
                "deadline": {"date": None, "text": ""},
                "contacts": {"full_name": "Тест", "email": "test@test.com", "phone": ""}
            }
        })
        
        # Патчим импорты в scenario_workflows
        import services.agents.scenario_workflows as sw_module
        sw_module.HRTimeOrderParser = lambda: mock_parser
        
        try:
            mock_rag.return_value = None
            mock_classify.return_value = {"category": "другое", "confidence": 0.3}
            mock_validate.return_value = {"score": 0.3, "status": "cold"}
            
            result = await process_hrtime_order("order_test_789", order_data=mock_order_data)
            
            # Проверка, что workflow завершился
            assert result["success"] is True
            
            # Проверка, что для холодного лида НЕ выполняются действия
            assert result["validation"]["score"] < 0.6
            assert result.get("proposal_sent", False) is False
            assert result.get("weeek_project_created", False) is False
            mock_send_proposal.assert_not_called()
            mock_create_project.assert_not_called()
        finally:
            # Восстанавливаем оригинальные классы
            if hasattr(sw_module, 'HRTimeOrderParser'):
                delattr(sw_module, 'HRTimeOrderParser')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
