"""
Тесты для меню WEEK в Telegram боте
Проверяет работу всех функций меню с фейковыми данными
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, CallbackQuery, User, Message, Chat
from telegram.ext import ContextTypes

# Импортируем функции для тестирования
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from telegram_bot.handlers.commands.weeek import (
    show_weeek_projects,
    show_weeek_create_task_menu,
    show_weeek_project_details,
    show_weeek_tasks_for_update,
    show_weeek_task_edit_menu,
    handle_weeek_complete_task,
    handle_weeek_delete_task
)
from telegram_bot.handlers.menu.callback_router import button_callback
from telegram_bot.handlers.commands.basic import status_command


# Фейковые данные для тестов
FAKE_PROJECTS = [
    {
        "id": "1",
        "title": "Проект HR Консалтинг",
        "name": "Проект HR Консалтинг",
        "color": "#FF5733",
        "isPrivate": False,
        "description": "Проект по HR консалтингу"
    },
    {
        "id": "2",
        "title": "Подбор персонала",
        "name": "Подбор персонала",
        "color": "#33FF57",
        "isPrivate": False,
        "description": "Проект по подбору персонала"
    },
    {
        "id": "3",
        "title": "Автоматизация HR",
        "name": "Автоматизация HR",
        "color": "#3357FF",
        "isPrivate": True,
        "description": "Проект по автоматизации HR процессов"
    }
]

FAKE_TASKS = [
    {
        "id": "101",
        "title": "Согласовать КП с клиентом",
        "name": "Согласовать КП с клиентом",
        "projectId": "1",
        "isCompleted": False,
        "priority": 2,
        "dueDate": "15.01.2026",
        "day": "15.01.2026"
    },
    {
        "id": "102",
        "title": "Провести интервью с кандидатами",
        "name": "Провести интервью с кандидатами",
        "projectId": "1",
        "isCompleted": False,
        "priority": 1,
        "dueDate": "16.01.2026",
        "day": "16.01.2026"
    },
    {
        "id": "103",
        "title": "Подготовить отчет",
        "name": "Подготовить отчет",
        "projectId": "1",
        "isCompleted": True,
        "priority": 0,
        "dueDate": "10.01.2026",
        "day": "10.01.2026"
    }
]

FAKE_DEADLINES = [
    {
        "id": "101",
        "name": "Согласовать КП с клиентом",
        "title": "Согласовать КП с клиентом",
        "project_id": "1",
        "due_date": "15.01.2026",
        "status": "Активна"
    },
    {
        "id": "102",
        "name": "Провести интервью с кандидатами",
        "title": "Провести интервью с кандидатами",
        "project_id": "1",
        "due_date": "16.01.2026",
        "status": "Активна"
    }
]


@pytest.fixture
def mock_query():
    """Создает мок CallbackQuery"""
    query = MagicMock(spec=CallbackQuery)
    query.data = "test"
    query.edit_message_text = AsyncMock()
    query.answer = AsyncMock()
    query.message = MagicMock()
    return query


@pytest.fixture
def mock_context():
    """Создает мок Context"""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    return context


@pytest.mark.asyncio
async def test_show_weeek_projects_success(mock_query):
    """Тест успешного отображения списка проектов"""
    mock_query.data = "weeek_list_projects"
    
    with patch('services.helpers.weeek_helper.get_projects', new_callable=AsyncMock) as mock_get_projects:
        mock_get_projects.return_value = FAKE_PROJECTS
        
        await show_weeek_projects(mock_query)
        
        # Проверяем, что функция была вызвана
        mock_get_projects.assert_called_once()
        
        # Проверяем, что edit_message_text был вызван
        assert mock_query.edit_message_text.called
        
        # Проверяем содержимое сообщения
        call_args = mock_query.edit_message_text.call_args
        text = call_args[0][0]
        reply_markup = call_args[1].get('reply_markup')
        assert "Проекты в WEEEK" in text
        assert "3" in text  # Количество проектов
        # Проверяем, что кнопки созданы (названия проектов в кнопках)
        assert reply_markup is not None
        assert len(reply_markup.inline_keyboard) > 0


@pytest.mark.asyncio
async def test_show_weeek_projects_empty(mock_query):
    """Тест отображения при отсутствии проектов"""
    mock_query.data = "weeek_list_projects"
    
    with patch('services.helpers.weeek_helper.get_projects', new_callable=AsyncMock) as mock_get_projects:
        mock_get_projects.return_value = []
        
        await show_weeek_projects(mock_query)
        
        assert mock_query.edit_message_text.called
        call_args = mock_query.edit_message_text.call_args
        text = call_args[0][0]
        assert "Проектов не найдено" in text or "WEEEK недоступен" in text


@pytest.mark.asyncio
async def test_show_weeek_create_task_menu_success(mock_query):
    """Тест успешного отображения меню создания задачи"""
    mock_query.data = "weeek_create_task_menu"
    
    with patch('services.helpers.weeek_helper.get_projects', new_callable=AsyncMock) as mock_get_projects:
        mock_get_projects.return_value = FAKE_PROJECTS
        
        await show_weeek_create_task_menu(mock_query)
        
        mock_get_projects.assert_called_once()
        assert mock_query.edit_message_text.called
        
        call_args = mock_query.edit_message_text.call_args
        text = call_args[0][0]
        assert "Создание задачи" in text
        assert "Выберите проект" in text


@pytest.mark.asyncio
async def test_show_weeek_project_details_success(mock_query, mock_context):
    """Тест успешного отображения деталей проекта"""
    mock_query.data = "weeek_view_project_1"
    
    with patch('services.helpers.weeek_helper.get_project', new_callable=AsyncMock) as mock_get_project, \
         patch('services.helpers.weeek_helper.get_tasks', new_callable=AsyncMock) as mock_get_tasks:
        
        mock_get_project.return_value = FAKE_PROJECTS[0]
        mock_get_tasks.return_value = {
            "success": True,
            "tasks": FAKE_TASKS[:2],
            "hasMore": False
        }
        
        await show_weeek_project_details(mock_query, mock_context)
        
        mock_get_project.assert_called_once_with("1")
        assert mock_query.edit_message_text.called
        
        call_args = mock_query.edit_message_text.call_args
        text = call_args[0][0]
        assert "Проект HR Консалтинг" in text
        assert "Активных задач" in text


@pytest.mark.asyncio
async def test_show_weeek_tasks_for_update_success(mock_query, mock_context):
    """Тест успешного отображения задач для обновления"""
    mock_query.data = "weeek_update_select_project_1"
    
    with patch('services.helpers.weeek_helper.get_project', new_callable=AsyncMock) as mock_get_project, \
         patch('services.helpers.weeek_helper.get_tasks', new_callable=AsyncMock) as mock_get_tasks:
        
        mock_get_project.return_value = FAKE_PROJECTS[0]
        mock_get_tasks.return_value = {
            "success": True,
            "tasks": FAKE_TASKS,
            "hasMore": False
        }
        
        await show_weeek_tasks_for_update(mock_query, mock_context)
        
        assert mock_query.edit_message_text.called
        call_args = mock_query.edit_message_text.call_args
        text = call_args[0][0]
        reply_markup = call_args[1].get('reply_markup')
        assert "Задачи" in text
        assert "Проект HR Консалтинг" in text
        # Проверяем, что кнопки с задачами созданы
        assert reply_markup is not None
        assert len(reply_markup.inline_keyboard) > 0


@pytest.mark.asyncio
async def test_show_weeek_task_edit_menu_success(mock_query, mock_context):
    """Тест успешного отображения меню редактирования задачи"""
    mock_query.data = "weeek_edit_task_101"
    
    with patch('services.helpers.weeek_helper.get_task', new_callable=AsyncMock) as mock_get_task:
        mock_get_task.return_value = FAKE_TASKS[0]
        
        await show_weeek_task_edit_menu(mock_query, mock_context)
        
        mock_get_task.assert_called_once_with("101")
        assert mock_query.edit_message_text.called
        
        call_args = mock_query.edit_message_text.call_args
        text = call_args[0][0]
        assert "Согласовать КП" in text
        assert "Статус" in text


@pytest.mark.asyncio
async def test_handle_weeek_complete_task(mock_query, mock_context):
    """Тест завершения задачи"""
    mock_query.data = "weeek_complete_101"
    
    with patch('services.helpers.weeek_helper.get_task', new_callable=AsyncMock) as mock_get_task, \
         patch('services.helpers.weeek_helper.complete_task', new_callable=AsyncMock) as mock_complete_task, \
         patch('telegram_bot.handlers.commands.weeek.show_weeek_task_edit_menu', new_callable=AsyncMock) as mock_show_menu:
        
        task = FAKE_TASKS[0].copy()
        task["isCompleted"] = False
        mock_get_task.return_value = task
        mock_complete_task.return_value = True
        
        await handle_weeek_complete_task(mock_query, mock_context)
        
        mock_get_task.assert_called_once_with("101")
        mock_complete_task.assert_called_once_with("101")
        mock_query.answer.assert_called_once()
        mock_show_menu.assert_called_once()


@pytest.mark.asyncio
async def test_handle_weeek_delete_task(mock_query, mock_context):
    """Тест удаления задачи"""
    mock_query.data = "weeek_delete_101"
    
    with patch('services.helpers.weeek_helper.delete_task', new_callable=AsyncMock) as mock_delete_task:
        mock_delete_task.return_value = True
        
        await handle_weeek_delete_task(mock_query, mock_context)
        
        mock_delete_task.assert_called_once_with("101")
        assert mock_query.edit_message_text.called
        
        call_args = mock_query.edit_message_text.call_args
        text = call_args[0][0]
        assert "Задача удалена" in text


@pytest.mark.asyncio
async def test_status_command_with_deadlines():
    """Тест команды /status с фейковыми дедлайнами"""
    mock_update = MagicMock(spec=Update)
    mock_update.message.reply_text = AsyncMock()
    mock_context = MagicMock()
    
    with patch('services.helpers.weeek_helper.get_project_deadlines', new_callable=AsyncMock) as mock_deadlines:
        mock_deadlines.return_value = FAKE_DEADLINES
        
        await status_command(mock_update, mock_context)
        
        mock_deadlines.assert_called_once_with(days_ahead=7)
        assert mock_update.message.reply_text.called
        
        call_args = mock_update.message.reply_text.call_args
        text = call_args[0][0]
        assert "Статус проектов" in text
        assert "Согласовать КП" in text


@pytest.mark.asyncio
async def test_menu_projects_callback(mock_query, mock_context):
    """Тест обработки callback для меню проектов"""
    mock_query.data = "menu_projects"
    
    # Создаем мок для Update
    mock_update = MagicMock(spec=Update)
    mock_update.callback_query = mock_query
    
    await button_callback(mock_update, mock_context)
    
    assert mock_query.edit_message_text.called
    call_args = mock_query.edit_message_text.call_args
    text = call_args[0][0]
    assert "Управление проектами" in text
    assert "WEEEK" in text
    assert "Мои проекты" in text
    assert "Создать задачу" in text
    assert "Статус" in text
    assert "Суммаризация" in text


@pytest.mark.asyncio
async def test_status_callback_with_fake_data(mock_query, mock_context):
    """Тест обработки callback для статуса с фейковыми данными"""
    mock_query.data = "status"
    
    mock_update = MagicMock(spec=Update)
    mock_update.callback_query = mock_query
    
    with patch('services.helpers.weeek_helper.get_project_deadlines', new_callable=AsyncMock) as mock_deadlines:
        mock_deadlines.return_value = FAKE_DEADLINES
        
        await button_callback(mock_update, mock_context)
        
        mock_deadlines.assert_called_once_with(days_ahead=7)
        assert mock_query.edit_message_text.called
        
        call_args = mock_query.edit_message_text.call_args
        text = call_args[0][0]
        assert "Статус проектов" in text
        assert "Согласовать КП" in text or "Провести интервью" in text


@pytest.mark.asyncio
async def test_summary_menu_callback(mock_query, mock_context):
    """Тест обработки callback для меню суммаризации"""
    mock_query.data = "summary_menu"
    
    mock_update = MagicMock(spec=Update)
    mock_update.callback_query = mock_query
    
    with patch('services.helpers.weeek_helper.get_projects', new_callable=AsyncMock) as mock_get_projects:
        mock_get_projects.return_value = FAKE_PROJECTS
        
        await button_callback(mock_update, mock_context)
        
        mock_get_projects.assert_called_once()
        assert mock_query.edit_message_text.called
        
        call_args = mock_query.edit_message_text.call_args
        text = call_args[0][0]
        assert "Суммаризация проекта" in text
        assert "Выберите проект" in text


@pytest.mark.asyncio
async def test_summary_project_callback(mock_query, mock_context):
    """Тест обработки callback для суммаризации конкретного проекта"""
    mock_query.data = "summary_project_1"
    
    mock_update = MagicMock(spec=Update)
    mock_update.callback_query = mock_query
    
    with patch('services.helpers.weeek_helper.get_project', new_callable=AsyncMock) as mock_get_project, \
         patch('services.helpers.weeek_helper.get_tasks', new_callable=AsyncMock) as mock_get_tasks:
        
        mock_get_project.return_value = FAKE_PROJECTS[0]
        mock_get_tasks.return_value = {
            "success": True,
            "tasks": FAKE_TASKS,
            "hasMore": False
        }
        
        await button_callback(mock_update, mock_context)
        
        mock_get_project.assert_called_once_with("1")
        assert mock_query.edit_message_text.called
        
        call_args = mock_query.edit_message_text.call_args
        text = call_args[0][0]
        assert "Суммаризация проекта" in text
        assert "Проект HR Консалтинг" in text
        assert "Статистика" in text
        assert "Всего задач" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
