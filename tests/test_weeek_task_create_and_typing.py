"""
Тесты создания задачи WEEEK: API POST /tm/tasks, ответ в Telegram «Задача создана», typing при кнопке.

Проверяет:
1. create_task вызывает POST https://api.weeek.net/public/v1/tm/tasks
2. При успешном создании Telegram отвечает текстом с подтверждением «Задача создана»
3. При нажатии кнопки «Создать задачу» отправляется ChatAction.TYPING
4. При создании задачи из сообщения (reply) отправляется ChatAction.TYPING
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, Chat, User
from telegram.constants import ChatAction

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ===================== 1. POST /tm/tasks используется =====================

def _make_aiohttp_post_mock(response_status=200, response_json=None):
    if response_json is None:
        response_json = {"task": {"id": "123", "name": "Test"}}
    mock_response = AsyncMock()
    mock_response.status = response_status
    mock_response.text = AsyncMock(return_value='{"task": {"id": "123", "name": "Test"}}')
    mock_response.json = AsyncMock(return_value=response_json)
    post_cm = MagicMock()
    post_cm.__aenter__ = AsyncMock(return_value=mock_response)
    post_cm.__aexit__ = AsyncMock(return_value=None)
    return post_cm, mock_response


@pytest.mark.asyncio
async def test_weeek_create_task_uses_post_tm_tasks():
    """create_task выполняет POST на https://api.weeek.net/public/v1/tm/tasks"""
    from services.helpers import weeek_helper

    with patch.dict('os.environ', {'WEEEEK_TOKEN': 'test-token'}, clear=False):
        with patch('aiohttp.ClientSession') as mock_session_class:
            post_cm, _ = _make_aiohttp_post_mock()
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = AsyncMock(return_value=post_cm)
            mock_session_class.return_value = mock_session

            task = await weeek_helper.create_task(
                project_id="1",
                title="Test task",
                description="Created from test"
            )

            assert task is not None
            assert task.get("id") == "123"
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            url = call_args[0][0]
            assert "/tm/tasks" in url, "URL должен содержать /tm/tasks"
            assert "api.weeek.net" in url or "weeek.net" in url, "Должен использоваться Weeek API"


@pytest.mark.asyncio
async def test_weeek_create_task_request_body():
    """Тело запроса create_task содержит name, projectId, type"""
    from services.helpers import weeek_helper

    with patch.dict('os.environ', {'WEEEEK_TOKEN': 'test-token'}, clear=False):
        with patch('aiohttp.ClientSession') as mock_session_class:
            post_cm, _ = _make_aiohttp_post_mock(response_json={"task": {"id": "456", "name": "My task"}})
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = AsyncMock(return_value=post_cm)
            mock_session_class.return_value = mock_session

            await weeek_helper.create_task(
                project_id="42",
                title="My task",
                description="Desc",
                task_type="action"
            )

            call_kwargs = mock_session.post.call_args
            body = call_kwargs[1].get("json")
            assert body is not None, "Запрос должен содержать JSON body"
            assert body.get("projectId") == 42
            assert body.get("name") == "My task"
            assert body.get("type") == "action"


# ===================== 2. Telegram подтверждает «Задача создана» =====================

@pytest.mark.asyncio
async def test_telegram_confirms_task_created_on_success():
    """При успешном создании задачи бот отвечает текстом с «Задача создана» / WEEEK"""
    from telegram_bot.handlers.messages.reply_handler import reply

    mock_update = MagicMock(spec=Update)
    mock_update.effective_chat = MagicMock()
    mock_update.effective_chat.id = 12345
    mock_update.message = MagicMock()
    mock_update.message.text = "Название новой задачи"
    mock_update.message.reply_text = AsyncMock()
    mock_update.message.from_user = MagicMock()
    mock_update.message.from_user.id = 1

    mock_context = MagicMock()
    mock_context.user_data = {
        "waiting_for_task_name": True,
        "selected_project_id": "99",
        "task_date": None,
        "task_time": None,
    }
    mock_context.bot.send_chat_action = AsyncMock()

    with patch('services.helpers.weeek_helper.create_task', new_callable=AsyncMock) as mock_create, \
         patch('services.helpers.weeek_helper.get_project', new_callable=AsyncMock) as mock_get_project:
        mock_create.return_value = {"id": "task_123", "name": "Название новой задачи"}
        mock_get_project.return_value = {"id": "99", "title": "Тестовый проект"}

        await reply(mock_update, mock_context)

        assert mock_update.message.reply_text.called
        calls = [str(c) for c in mock_update.message.reply_text.call_args_list]
        full_text = " ".join(calls)
        reply_content = mock_update.message.reply_text.call_args_list[-1][0][0]
        assert "Задача создана" in reply_content or "WEEEK" in reply_content, \
            "Ответ должен содержать подтверждение создания задачи"


# ===================== 3. Typing при нажатии кнопки «Создать задачу» =====================

@pytest.mark.asyncio
async def test_typing_sent_when_create_task_button_pressed():
    """При нажатии кнопки «Создать задачу» (weeek_create_task_menu) отправляется action typing"""
    from telegram_bot.handlers.menu.callback_router import button_callback

    mock_query = MagicMock()
    mock_query.data = "weeek_create_task_menu"
    mock_query.message = MagicMock()
    mock_query.message.chat = MagicMock()
    mock_query.message.chat.id = 999
    mock_query.edit_message_text = AsyncMock()
    mock_query.answer = AsyncMock()

    mock_update = MagicMock(spec=Update)
    mock_update.callback_query = mock_query

    mock_context = MagicMock()
    mock_context.user_data = {}
    mock_context.bot.send_chat_action = AsyncMock()

    with patch('services.helpers.weeek_helper.get_projects', new_callable=AsyncMock) as mock_get_projects:
        mock_get_projects.return_value = [
            {"id": "1", "title": "Проект 1", "name": "Проект 1"},
        ]

        await button_callback(mock_update, mock_context)

        mock_context.bot.send_chat_action.assert_called_once()
        call_args = mock_context.bot.send_chat_action.call_args
        assert call_args[1]["chat_id"] == 999
        assert call_args[1]["action"] == ChatAction.TYPING


# ===================== 4. Typing при создании задачи из сообщения (reply) =====================

@pytest.mark.asyncio
async def test_typing_sent_when_creating_task_from_reply():
    """При создании задачи по тексту (waiting_for_task_name) перед созданием отправляется typing"""
    from telegram_bot.handlers.messages.reply_handler import reply

    mock_update = MagicMock(spec=Update)
    mock_update.effective_chat = MagicMock()
    mock_update.effective_chat.id = 11111
    mock_update.message = MagicMock()
    mock_update.message.text = "Сделать отчёт"
    mock_update.message.reply_text = AsyncMock()
    mock_update.message.from_user = MagicMock()
    mock_update.message.from_user.id = 2

    mock_context = MagicMock()
    mock_context.user_data = {
        "waiting_for_task_name": True,
        "selected_project_id": "10",
        "task_date": None,
        "task_time": None,
    }
    mock_context.bot.send_chat_action = AsyncMock()

    with patch('services.helpers.weeek_helper.create_task', new_callable=AsyncMock) as mock_create, \
         patch('services.helpers.weeek_helper.get_project', new_callable=AsyncMock) as mock_get_project, \
         patch('telegram_bot.handlers.messages.reply_handler.get_recent_history') as mock_history:
        mock_create.return_value = {"id": "t1", "name": "Сделать отчёт"}
        mock_get_project.return_value = {"id": "10", "title": "Проект"}
        mock_history.return_value = []

        await reply(mock_update, mock_context)

        mock_context.bot.send_chat_action.assert_called()
        call_args_list = mock_context.bot.send_chat_action.call_args_list
        typing_calls = [c for c in call_args_list if c[1].get("action") == ChatAction.TYPING]
        assert len(typing_calls) >= 1, "Должен быть вызван send_chat_action с action TYPING при создании задачи"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
