"""
WEEEK Integration Module
Интеграция с WEEEK API для управления проектами и задачами
API Documentation: https://api.weeek.net/public/v1
"""
import os
import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta

log = logging.getLogger()

# ===================== CONFIGURATION =====================
# Поддерживаем оба варианта для обратной совместимости
WEEEK_API_KEY = os.getenv("WEEEEK_TOKEN") or os.getenv("WEEEK_API_KEY") or os.getenv("WEEEK_TOKEN")
WEEEK_API_URL = os.getenv("WEEEK_API_URL", "https://api.weeek.net/public/v1")
WEEEK_WORKSPACE_ID = os.getenv("WEEEK_WORKSPACE_ID")

log.info(f"🔧 WEEEK API URL: {WEEEK_API_URL}")
if WEEEK_API_KEY:
    log.info(f"✅ WEEEK API KEY установлен (длина: {len(WEEEK_API_KEY)})")
else:
    log.warning("⚠️ WEEEK API KEY не установлен!")
if WEEEK_WORKSPACE_ID:
    log.info(f"✅ WEEEK WORKSPACE ID: {WEEEK_WORKSPACE_ID}")
else:
    log.warning("⚠️ WEEEK WORKSPACE ID не установлен!")

# ===================== HELPER FUNCTIONS =====================

def get_headers() -> Dict[str, str]:
    """Получить заголовки для API запросов"""
    if not WEEEK_API_KEY:
        return {}
    return {
        "Authorization": f"Bearer {WEEEK_API_KEY}",
        "Content-Type": "application/json"
    }

# ===================== PROJECT OPERATIONS =====================

async def create_project(
    name: str,
    description: str = "",
    color: Optional[str] = None,
    is_private: bool = False
) -> Optional[Dict]:
    """
    Создать новый проект в WEEEK
    API: POST /tm/projects
    
    Args:
        name: Название проекта (обязательно)
        description: Описание проекта
        color: Цвет проекта (hex, например "#FF5733")
        is_private: Приватный проект (обязательное поле!)
    
    Returns:
        Словарь с данными созданного проекта или None при ошибке
    """
    if not WEEEK_API_KEY:
        log.error("❌ WEEEK_API_KEY не установлен")
        return None
    
    url = f"{WEEEK_API_URL}/tm/projects"
    headers = get_headers()
    
    # Формируем данные по документации API
    # isPrivate - ОБЯЗАТЕЛЬНОЕ ПОЛЕ!
    data = {
        "name": name,
        "isPrivate": is_private
    }
    
    if description:
        data["description"] = description
    if color:
        data["color"] = color
    
    try:
        log.info(f"📤 [WEEEK] Создаю проект: {name}")
        log.debug(f"📤 Данные: {data}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response_text = await response.text()
                
                if response.status >= 400:
                    log.error(f"❌ [WEEEK] Ошибка создания проекта: {response.status}")
                    log.error(f"❌ Response: {response_text[:500]}")
                    return None
                
                result = await response.json() if response_text else {}
                
                # API возвращает {"success": true, "project": {...}}
                if isinstance(result, dict) and "project" in result:
                    project = result["project"]
                    log.info(f"✅ [WEEEK] Проект создан: {name} (ID: {project.get('id')})")
                    return project
                elif isinstance(result, dict) and "id" in result:
                    # Если вернулся сразу проект
                    log.info(f"✅ [WEEEK] Проект создан: {name} (ID: {result.get('id')})")
                    return result
                else:
                    log.warning(f"⚠️ Неожиданный формат ответа: {result}")
                    return result
                
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка создания проекта: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

async def update_project_status(project_id: str, status: str) -> bool:
    """
    Обновить статус проекта
    
    Args:
        project_id: ID проекта
        status: Новый статус (new, in_progress, completed, rejected)
    
    Returns:
        True при успехе, False при ошибке
    """
    if not WEEEK_API_KEY:
        return False
    
    url = f"{WEEEK_API_URL}/projects/{project_id}"
    headers = get_headers()
    
    data = {"status": status}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [WEEEK] Ошибка обновления статуса проекта: {response.status} - {error_text}")
                    return False
                
                log.info(f"✅ [WEEEK] Статус проекта {project_id} обновлен на {status}")
                return True
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка обновления статуса проекта: {e}")
        return False

async def get_project(project_id: str) -> Optional[Dict]:
    """
    Получить информацию о проекте
    API: GET /tm/projects/{id}
    """
    if not WEEEK_API_KEY:
        return None
    
    url = f"{WEEEK_API_URL}/tm/projects/{project_id}"
    headers = get_headers()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    return None
                return await response.json()
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка получения проекта: {e}")
        return None

async def get_workspace_info() -> Optional[Dict]:
    """
    Получить информацию о workspace
    API: GET /ws
    
    Returns:
        Словарь с данными workspace или None
    """
    if not WEEEK_API_KEY:
        log.error("❌ WEEEK_API_KEY не установлен")
        return None
    
    url = f"{WEEEK_API_URL}/ws"
    headers = get_headers()
    
    try:
        log.info(f"📤 [WEEEK] Запрос workspace info: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [WEEEK] Ошибка получения workspace: {response.status}")
                    log.error(f"❌ Response: {error_text[:500]}")
                    return None
                
                result = await response.json()
                
                if isinstance(result, dict) and "workspace" in result:
                    workspace = result["workspace"]
                    log.info(f"✅ [WEEEK] Workspace: {workspace.get('title')} (ID: {workspace.get('id')})")
                    return workspace
                else:
                    log.error(f"❌ Неожиданный формат ответа: {result}")
                    return None
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка получения workspace: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

async def get_projects(workspace_id: Optional[str] = None) -> List[Dict]:
    """
    Получить список всех проектов
    API: GET /tm/projects (НЕ /pm/projects!)
    
    Args:
        workspace_id: ID workspace (опционально, для совместимости)
    
    Returns:
        Список словарей с данными проектов
    """
    if not WEEEK_API_KEY:
        log.error("❌ WEEEK_API_KEY не установлен")
        return []
    
    # ПРАВИЛЬНЫЙ endpoint из твоего working code!
    url = f"{WEEEK_API_URL}/tm/projects"
    headers = get_headers()
    
    try:
        log.info(f"📤 [WEEEK] Запрос проектов: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [WEEEK] Ошибка получения проектов: {response.status}")
                    log.error(f"❌ Response: {error_text[:500]}")
                    return []
                
                result = await response.json()
                
                # API возвращает {"success": true, "projects": [...]}
                if isinstance(result, dict) and "projects" in result:
                    projects = result["projects"]
                    log.info(f"✅ [WEEEK] Получено проектов: {len(projects)}")
                    return projects
                else:
                    log.error(f"❌ Неожиданный формат ответа: {result}")
                    return []
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка получения проектов: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return []

# ===================== TASK OPERATIONS =====================

async def create_task(
    project_id: str,
    title: str,
    description: str = "",
    day: Optional[str] = None,
    user_id: Optional[str] = None,
    priority: Optional[int] = None,
    task_type: str = "action",
    name: Optional[str] = None  # Для обратной совместимости
) -> Optional[Dict]:
    """
    Создать задачу
    API: POST /tm/tasks
    
    Args:
        project_id: ID проекта
        title: Название задачи
        description: Описание задачи
        day: Дата в формате dd.mm.yyyy
        user_id: ID исполнителя
        priority: Приоритет (0=Low, 1=Medium, 2=High, 3=Hold)
        task_type: Тип задачи (action, meet, call)
        name: Альтернативное название (для обратной совместимости)
    
    Returns:
        Словарь с данными созданной задачи или None при ошибке
    """
    if not WEEEK_API_KEY:
        log.error("❌ WEEEK_API_KEY не установлен")
        return None
    
    # Используем title или name для обратной совместимости
    task_title = title or name
    if not task_title:
        log.error("❌ Не указано название задачи")
        return None
    
    url = f"{WEEEK_API_URL}/tm/tasks"
    headers = get_headers()
    
    # По Twojemu working примеру используем prostszy format
    # API wymaga: name, projectId, boardId (opcjonalnie)
    data = {
        "name": task_title,
        "projectId": int(project_id),
        "type": task_type
    }
    
    # Опциональные поля
    if description:
        data["description"] = description
    if day:
        data["day"] = day
    if user_id:
        data["userId"] = user_id
    if priority is not None:
        data["priority"] = priority
    
    try:
        log.info(f"📤 [WEEEK] Создаю задачу: {task_title} в проекте {project_id}")
        log.debug(f"📤 Данные запроса: {data}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response_text = await response.text()
                
                if response.status >= 400:
                    log.error(f"❌ [WEEEK] Ошибка создания задачи: {response.status}")
                    log.error(f"❌ Response: {response_text[:500]}")
                    return None
                
                result = await response.json() if response_text else {}
                
                # API возвращает {"success": true, "task": {...}}
                if isinstance(result, dict) and "task" in result:
                    task = result["task"]
                    log.info(f"✅ [WEEEK] Задача создана: {task_title} (ID: {task.get('id')})")
                    return task
                else:
                    log.warning(f"⚠️ Неожиданный формат ответа, но статус 200")
                    return result
                
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка создания задачи: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

async def update_task(
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[int] = None,
    task_type: Optional[str] = None,
    start_date: Optional[str] = None,
    due_date: Optional[str] = None,
    duration: Optional[int] = None,
    tags: Optional[List[int]] = None
) -> Optional[Dict]:
    """
    Обновить задачу
    API: PUT /tm/tasks/{id}
    
    Args:
        task_id: ID задачи
        title: Новое название (max 255)
        description: Новое описание
        priority: Новый приоритет (0=Low, 1=Medium, 2=High, 3=Hold)
        task_type: Новый тип (action, meet, call)
        start_date: Дата начала (Y-m-d format)
        due_date: Дата окончания (Y-m-d format)
        duration: Оценка времени в минутах
        tags: Список ID тегов
    
    Returns:
        Обновленная задача или None при ошибке
    """
    if not WEEEK_API_KEY:
        log.error("❌ WEEEK_API_KEY не установлен")
        return None
    
    url = f"{WEEEK_API_URL}/tm/tasks/{task_id}"
    headers = get_headers()
    
    # Формируем данные для обновления (только переданные поля)
    data = {}
    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if priority is not None:
        data["priority"] = priority
    if task_type is not None:
        data["type"] = task_type
    if start_date is not None:
        data["startDate"] = start_date
    if due_date is not None:
        data["dueDate"] = due_date
    if duration is not None:
        data["duration"] = duration
    if tags is not None:
        data["tags"] = tags
    
    if not data:
        log.warning("⚠️ Нет данных для обновления")
        return None
    
    try:
        log.info(f"📤 [WEEEK] Обновляю задачу {task_id}: {data}")
        
        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response_text = await response.text()
                
                if response.status >= 400:
                    log.error(f"❌ [WEEEK] Ошибка обновления задачи: {response.status}")
                    log.error(f"❌ Response: {response_text[:500]}")
                    return None
                
                result = await response.json() if response_text else {}
                
                if isinstance(result, dict) and "task" in result:
                    task = result["task"]
                    log.info(f"✅ [WEEEK] Задача обновлена: {task_id}")
                    return task
                else:
                    log.warning(f"⚠️ Неожиданный формат ответа")
                    return result
                
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка обновления задачи: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

async def complete_task(task_id: str) -> bool:
    """
    Отметить задачу как выполненную
    API: POST /tm/tasks/{id}/complete
    """
    if not WEEEK_API_KEY:
        return False
    
    url = f"{WEEEK_API_URL}/tm/tasks/{task_id}/complete"
    headers = get_headers()
    
    try:
        log.info(f"📤 [WEEEK] Завершаю задачу {task_id}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status < 400:
                    log.info(f"✅ [WEEEK] Задача {task_id} завершена")
                    return True
                else:
                    response_text = await response.text()
                    log.error(f"❌ [WEEEK] Ошибка: {response.status} - {response_text[:200]}")
                    return False
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка завершения задачи: {e}")
        return False

async def uncomplete_task(task_id: str) -> bool:
    """
    Отменить завершение задачи
    API: POST /tm/tasks/{id}/un-complete
    """
    if not WEEEK_API_KEY:
        return False
    
    url = f"{WEEEK_API_URL}/tm/tasks/{task_id}/un-complete"
    headers = get_headers()
    
    try:
        log.info(f"📤 [WEEEK] Возобновляю задачу {task_id}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status < 400:
                    log.info(f"✅ [WEEEK] Задача {task_id} возобновлена")
                    return True
                else:
                    response_text = await response.text()
                    log.error(f"❌ [WEEEK] Ошибка: {response.status} - {response_text[:200]}")
                    return False
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка возобновления задачи: {e}")
        return False

async def delete_task(task_id: str) -> bool:
    """
    Удалить задачу
    API: DELETE /tm/tasks/{id}
    """
    if not WEEEK_API_KEY:
        return False
    
    url = f"{WEEEK_API_URL}/tm/tasks/{task_id}"
    headers = get_headers()
    
    try:
        log.info(f"📤 [WEEEK] Удаляю задачу {task_id}")
        
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status < 400:
                    log.info(f"✅ [WEEEK] Задача {task_id} удалена")
                    return True
                else:
                    response_text = await response.text()
                    log.error(f"❌ [WEEEK] Ошибка: {response.status} - {response_text[:200]}")
                    return False
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка удаления задачи: {e}")
        return False

async def get_task(task_id: str) -> Optional[Dict]:
    """
    Получить информацию об одной задаче
    API: GET /tm/tasks/{id}
    """
    if not WEEEK_API_KEY:
        return None
    
    url = f"{WEEEK_API_URL}/tm/tasks/{task_id}"
    headers = get_headers()
    
    try:
        log.info(f"📤 [WEEEK] Получаю задачу {task_id}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    response_text = await response.text()
                    log.error(f"❌ [WEEEK] Ошибка: {response.status} - {response_text[:200]}")
                    return None
                
                result = await response.json()
                
                if isinstance(result, dict) and "task" in result:
                    return result["task"]
                else:
                    return result
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка получения задачи: {e}")
        return None

async def get_tasks(
    day: Optional[str] = None,
    user_id: Optional[str] = None,
    project_id: Optional[int] = None,
    completed: Optional[bool] = None,
    board_id: Optional[int] = None,
    board_column_id: Optional[int] = None,
    task_type: Optional[str] = None,
    priority: Optional[int] = None,
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
    per_page: int = 50,
    offset: int = 0,
    sort_by: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    all_tasks: bool = False
) -> Dict[str, any]:
    """
    Получить задачи из WEEEK
    API: GET /tm/tasks
    
    Args:
        day: Дата в формате dd.mm.yyyy
        user_id: ID пользователя
        project_id: ID проекта
        completed: Показать только завершенные (True/False)
        board_id: ID доски
        board_column_id: ID колонки доски
        task_type: Тип задачи (action, meet, call)
        priority: Приоритет (0=Low, 1=Medium, 2=High, 3=Hold)
        tags: Список ID тегов
        search: Текст для поиска в названии и описании
        per_page: Количество задач на страницу
        offset: Смещение для пагинации
        sort_by: Сортировка (name, type, priority, duration, overdue, created, date)
        start_date: Начальная дата в формате dd.mm.yyyy (требуется с endDate)
        end_date: Конечная дата в формате dd.mm.yyyy (требуется с startDate)
        all_tasks: Показать все задачи включая удаленные и завершенные
    
    Returns:
        Dict с ключами: success, tasks (список), hasMore (bool)
    """
    if not WEEEK_API_KEY:
        log.error("❌ WEEEK_API_KEY не установлен")
        return {"success": False, "tasks": [], "hasMore": False}
    
    url = f"{WEEEK_API_URL}/tm/tasks"
    headers = get_headers()
    
    # Формируем параметры запроса
    params = {
        "perPage": per_page,
        "offset": offset
    }
    
    if day:
        params["day"] = day
    if user_id:
        params["userId"] = user_id
    if project_id:
        params["projectId"] = project_id
    if completed is not None:
        params["completed"] = "true" if completed else "false"  # Преобразуем булево значение в строку
    if board_id:
        params["boardId"] = board_id
    if board_column_id:
        params["boardColumnId"] = board_column_id
    if task_type:
        params["type"] = task_type
    if priority is not None:
        params["priority"] = priority
    if tags:
        params["tags"] = tags
    if search:
        params["search"] = search
    if sort_by:
        params["sortBy"] = sort_by
    if start_date and end_date:
        params["startDate"] = start_date
        params["endDate"] = end_date
    if all_tasks:
        params["all"] = "true"
    
    try:
        log.info(f"📤 [WEEEK] Запрос задач с параметрами: {params}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response_text = await response.text()
                
                if response.status >= 400:
                    log.error(f"❌ [WEEEK] Ошибка получения задач: {response.status}")
                    log.error(f"❌ Response: {response_text[:500]}")
                    return {"success": False, "tasks": [], "hasMore": False}
                
                result = await response.json() if response_text else {}
                
                # API возвращает {"success": true, "tasks": [...], "hasMore": false}
                if isinstance(result, dict):
                    tasks = result.get("tasks", [])
                    has_more = result.get("hasMore", False)
                    log.info(f"✅ [WEEEK] Получено задач: {len(tasks)}, hasMore: {has_more}")
                    return {
                        "success": True,
                        "tasks": tasks,
                        "hasMore": has_more
                    }
                else:
                    log.error(f"❌ Неожиданный формат ответа: {type(result)}")
                    return {"success": False, "tasks": [], "hasMore": False}
                
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка получения задач: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"success": False, "tasks": [], "hasMore": False}

async def get_project_deadlines(days_ahead: int = 7) -> List[Dict]:
    """
    Получить задачи с ближайшими дедлайнами (упрощенная версия)
    Использует get_tasks() с фильтром по датам
    
    Args:
        days_ahead: Количество дней вперед для проверки
    
    Returns:
        Список задач с дедлайнами
    """
    # Вычисляем даты в формате dd.mm.yyyy
    start_date = datetime.now().strftime("%d.%m.%Y")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%d.%m.%Y")
    
    log.info(f"📅 [WEEEK] Получаю задачи с дедлайнами: {start_date} - {end_date}")
    
    result = await get_tasks(
        completed=False,
        start_date=start_date,
        end_date=end_date,
        per_page=100
    )
    
    if result["success"]:
        tasks = result["tasks"]
        log.info(f"✅ [WEEEK] Найдено задач с дедлайнами: {len(tasks)}")
        
        # Форматируем для обратной совместимости
        formatted_tasks = []
        for task in tasks:
            formatted_tasks.append({
                "id": task.get("id"),
                "name": task.get("title", task.get("name", "Без названия")),
                "project_id": task.get("projectId"),
                "due_date": task.get("dueDate", task.get("day")),
                "status": "completed" if task.get("completed") else "active"
            })
        
        return formatted_tasks
    else:
        return []

