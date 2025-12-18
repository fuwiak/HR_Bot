"""
Полные интеграционные тесты всей системы
Проверяет работу всех компонентов вместе через Telegram бота
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Импорты для тестирования
import app
from scenario_workflows import (
    process_hrtime_order,
    process_lead_email,
    process_telegram_lead
)


class TestFullSystemIntegration:
    """Класс для полных интеграционных тестов"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_hrtime_to_telegram(self):
        """End-to-end тест: HR Time заказ → обработка → уведомление в Telegram"""
        
        mock_telegram_bot = AsyncMock()
        mock_telegram_bot.send_message = AsyncMock(return_value=Mock(id=1))
        
        order_data = {
            "id": "e2e_order_1",
            "title": "Подбор IT-рекрутера",
            "description": "Требуется опытный IT-рекрутер. Бюджет 150000. Срок 3 недели.",
            "budget": 150000,
            "deadline": "2026-01-20",
            "client": {
                "name": "Мария Сидорова",
                "email": "maria@tech.com",
                "phone": "+79009876543"
            }
        }
        
        with patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '999999'}), \
             patch('scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
             patch('scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
             patch('scenario_workflows.generate_proposal', new_callable=AsyncMock) as mock_proposal, \
             patch('scenario_workflows.send_proposal', new_callable=AsyncMock) as mock_send_proposal, \
             patch('scenario_workflows.send_email', new_callable=AsyncMock) as mock_email, \
             patch('scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project, \
             patch('scenario_workflows.create_task', new_callable=AsyncMock) as mock_task, \
             patch('scenario_workflows.get_rag_chain') as mock_rag:
            
            # Настройка моков
            mock_classify.return_value = {"category": "подбор", "confidence": 0.92}
            mock_validate.return_value = {"score": 0.88, "status": "warm"}
            mock_proposal.return_value = "КП по подбору IT-рекрутера..."
            mock_send_proposal.return_value = True
            mock_email.return_value = True
            mock_create_project.return_value = {"id": "project_e2e_1"}
            mock_task.return_value = {"id": "task_e2e_1"}
            mock_rag.return_value = None
            
            # Выполняем полный workflow
            result = await process_hrtime_order("e2e_order_1", order_data=order_data)
            
            # Отправляем уведомление консультанту (симуляция)
            if result.get("notification_text"):
                await mock_telegram_bot.send_message(
                    chat_id=999999,
                    text=result["notification_text"],
                    parse_mode="Markdown"
                )
            
            # Проверки
            assert result["success"] is True
            assert result["proposal_sent"] is True
            assert result["weeek_project_created"] is True
            assert mock_telegram_bot.send_message.called
            
            print("✅ End-to-end тест HR Time → Telegram пройден")
    
    @pytest.mark.asyncio
    async def test_end_to_end_email_to_telegram_approval(self):
        """End-to-end тест: Email → обработка → подтверждение в Telegram → отправка"""
        
        mock_telegram_bot = AsyncMock()
        mock_telegram_bot.send_message = AsyncMock(return_value=Mock(id=2))
        
        email_data = {
            "subject": "Запрос на консультацию по подбору",
            "body": "Здравствуйте! Нужна помощь с подбором персонала для нашей компании.",
            "from": "client@business.com",
            "to": "a-novoselova07@yandex.ru"
        }
        
        with patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '999999'}), \
             patch('scenario_workflows.classify_email', new_callable=AsyncMock) as mock_classify_email, \
             patch('scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
             patch('scenario_workflows.generate_proposal', new_callable=AsyncMock) as mock_proposal, \
             patch('scenario_workflows.send_email', new_callable=AsyncMock) as mock_send_email, \
             patch('scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project, \
             patch('scenario_workflows.get_rag_chain') as mock_rag:
            
            mock_classify_email.return_value = "new_lead"
            mock_classify.return_value = {"category": "подбор", "confidence": 0.85}
            mock_proposal.return_value = "Предложение по подбору персонала..."
            mock_send_email.return_value = True
            mock_create_project.return_value = {"id": "project_e2e_2"}
            mock_rag.return_value = None
            
            # Обрабатываем письмо (с подтверждением)
            result = await process_lead_email(
                email_data,
                require_approval=True,
                telegram_bot=mock_telegram_bot
            )
            
            # Симулируем подтверждение консультанта (он "одобряет" отправку)
            # В реальности это будет через callback от inline кнопки
            if result.get("draft_proposal") and result.get("requires_approval"):
                # Консультант одобрил - отправляем
                result["approved"] = True
                await mock_send_email(
                    to_email=email_data["from"],
                    subject=f"Re: {email_data['subject']}",
                    body=result["draft_proposal"],
                    is_html=False
                )
                result["email_sent"] = True
            
            # Проверки
            assert result["success"] is True
            assert result.get("approval_requested", False) is True
            assert mock_telegram_bot.send_message.called  # Запрос на подтверждение
            
            print("✅ End-to-end тест Email → Telegram Approval → Send пройден")
    
    @pytest.mark.asyncio
    async def test_end_to_end_telegram_lead_to_weeek(self):
        """End-to-end тест: Telegram сообщение → обработка → проект в WEEEK → уведомление"""
        
        mock_telegram_bot = AsyncMock()
        mock_telegram_bot.send_message = AsyncMock(return_value=Mock(id=3))
        
        with patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '999999'}), \
             patch('scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
             patch('scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
             patch('scenario_workflows.create_project', new_callable=AsyncMock) as mock_create_project, \
             patch('scenario_workflows.get_rag_chain') as mock_rag:
            
            mock_classify.return_value = {"category": "автоматизация", "confidence": 0.9}
            mock_validate.return_value = {"score": 0.82, "status": "warm"}
            mock_create_project.return_value = {"id": "project_e2e_3", "name": "Тест — Telegram запрос"}
            
            mock_rag_instance = Mock()
            mock_rag_instance.query = AsyncMock(return_value={
                "answer": "Релевантная информация об автоматизации HR..."
            })
            mock_rag.return_value = mock_rag_instance
            
            # Обрабатываем Telegram лид
            result = await process_telegram_lead(
                user_message="Нужна автоматизация HR-процессов в нашей компании",
                user_id=55555,
                user_name="Алексей",
                telegram_bot=mock_telegram_bot
            )
            
            # Проверки
            assert result["success"] is True
            assert result["validation"]["score"] > 0.6
            assert result["weeek_project_created"] is True
            assert "weeek_project_id" in result
            assert mock_telegram_bot.send_message.called  # Уведомление консультанта
            
            print("✅ End-to-end тест Telegram → WEEEK → Notification пройден")
    
    @pytest.mark.asyncio
    async def test_all_scenarios_async_compatibility(self):
        """Тест: проверка что все сценарии работают асинхронно и не блокируют друг друга"""
        
        mock_telegram_bot = AsyncMock()
        mock_telegram_bot.send_message = AsyncMock(return_value=Mock(id=4))
        
        # Запускаем все сценарии параллельно
        with patch('scenario_workflows.classify_request', new_callable=AsyncMock) as mock_classify, \
             patch('scenario_workflows.validate_lead', new_callable=AsyncMock) as mock_validate, \
             patch('scenario_workflows.generate_proposal', new_callable=AsyncMock) as mock_proposal, \
             patch('scenario_workflows.send_proposal', new_callable=AsyncMock) as mock_send_proposal, \
             patch('scenario_workflows.send_email', new_callable=AsyncMock) as mock_email, \
             patch('scenario_workflows.create_project', new_callable=AsyncMock) as mock_project, \
             patch('scenario_workflows.create_task', new_callable=AsyncMock) as mock_task, \
             patch('scenario_workflows.classify_email', new_callable=AsyncMock) as mock_classify_email, \
             patch('scenario_workflows.get_project_deadlines', new_callable=AsyncMock) as mock_deadlines, \
             patch('scenario_workflows.get_rag_chain') as mock_rag, \
             patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '999999'}):
            
            # Настройка моков
            mock_classify.return_value = {"category": "подбор", "confidence": 0.8}
            mock_validate.return_value = {"score": 0.75, "status": "warm"}
            mock_proposal.return_value = "КП..."
            mock_send_proposal.return_value = True
            mock_email.return_value = True
            mock_project.return_value = {"id": "project_async"}
            mock_task.return_value = {"id": "task_async"}
            mock_classify_email.return_value = "new_lead"
            mock_deadlines.return_value = []
            mock_rag.return_value = None
            
            # Запускаем все сценарии параллельно
            start_time = datetime.now()
            
            tasks = [
                # Сценарий 1
                process_hrtime_order("async_order_1", order_data={
                    "id": "async_order_1",
                    "title": "Тест 1",
                    "description": "Описание",
                    "client": {"name": "Клиент", "email": "test@test.com"}
                }),
                # Сценарий 2
                process_lead_email({
                    "subject": "Тест 2",
                    "body": "Тело",
                    "from": "test2@test.com"
                }, require_approval=False, telegram_bot=mock_telegram_bot),
                # Сценарий 3
                process_telegram_lead(
                    "Тест 3",
                    user_id=111,
                    user_name="User",
                    telegram_bot=mock_telegram_bot
                )
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Проверяем, что все выполнилось без ошибок
            assert len(results) == 3
            assert all(not isinstance(r, Exception) for r in results)
            assert all(r.get("success") for r in results if isinstance(r, dict))
            
            print(f"✅ Все сценарии выполнены параллельно за {duration:.2f} секунд")
            print(f"   Среднее время: {duration/3:.2f} секунд на сценарий")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

