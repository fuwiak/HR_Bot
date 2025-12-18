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
    lead_id: Optional[str] = None,
    status: str = "new"
) -> Optional[Dict]:
    """
    Создать новый проект в WEEEK
    
    Args:
        name: Название проекта
        description: Описание проекта
        lead_id: ID лида (для связи)
        status: Статус проекта (new, in_progress, completed, rejected)
    
    Returns:
        Словарь с данными созданного проекта или None при ошибке
    """
    if not WEEEK_API_KEY or not WEEEK_WORKSPACE_ID:
        log.error("❌ WEEEK_API_KEY или WEEEK_WORKSPACE_ID не установлены")
        return None
    
    url = f"{WEEEK_API_URL}/projects"
    headers = get_headers()
    
    data = {
        "name": name,
        "description": description,
        "workspace_id": WEEEK_WORKSPACE_ID,
        "status": status
    }
    
    if lead_id:
        data["custom_fields"] = {"lead_id": lead_id}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [WEEEK] Ошибка создания проекта: {response.status} - {error_text}")
                    return None
                
                result = await response.json()
                log.info(f"✅ [WEEEK] Проект создан: {name} (ID: {result.get('id')})")
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
    """Получить информацию о проекте"""
    if not WEEEK_API_KEY:
        return None
    
    url = f"{WEEEK_API_URL}/projects/{project_id}"
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

async def get_projects() -> List[Dict]:
    """
    Получить список всех проектов
    API: GET /ws/projects
    
    Returns:
        Список словарей с данными проектов
    """
    if not WEEEK_API_KEY:
        log.error("❌ WEEEK_API_KEY не установлен")
        return []
    
    url = f"{WEEEK_API_URL}/ws/projects"
    headers = get_headers()
    
    try:
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
                elif isinstance(result, list):
                    projects = result
                else:
                    log.error(f"❌ Неожиданный формат ответа: {type(result)}")
                    return []
                
                log.info(f"✅ [WEEEK] Получено проектов: {len(projects)}")
                return projects
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
    
    # Обязательные поля по документации API
    data = {
        "locations": [
            {
                "projectId": int(project_id)
            }
        ],
        "title": task_title,
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

async def update_task_status(task_id: str, status: str) -> bool:
    """Обновить статус задачи"""
    if not WEEEK_API_KEY:
        return False
    
    url = f"{WEEEK_API_URL}/tasks/{task_id}"
    headers = get_headers()
    
    data = {"status": status}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                return response.status < 400
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка обновления статуса задачи: {e}")
        return False

# ===================== DEADLINES AND REMINDERS =====================

async def get_project_deadlines(days_ahead: int = 7) -> List[Dict]:
    """
    Получить список задач с дедлайнами в ближайшие дни
    
    Args:
        days_ahead: Количество дней вперед для проверки
    
    Returns:
        Список задач с приближающимися дедлайнами
    """
    if not WEEEK_API_KEY or not WEEEK_WORKSPACE_ID:
        return []
    
    # Здесь нужно использовать реальный API endpoint для получения задач
    # Это примерная реализация, нужно адаптировать под реальный API WEEEK
    url = f"{WEEEK_API_URL}/tasks"
    headers = get_headers()
    params = {
        "workspace_id": WEEEK_WORKSPACE_ID,
        "due_date_from": datetime.now().isoformat(),
        "due_date_to": (datetime.now() + timedelta(days=days_ahead)).isoformat()
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    return []
                
                result = await response.json()
                tasks = result.get("tasks", result.get("data", []))
                
                upcoming_tasks = []
                for task in tasks:
                    if task.get("due_date"):
                        upcoming_tasks.append({
                            "id": task.get("id"),
                            "name": task.get("name"),
                            "project_id": task.get("project_id"),
                            "due_date": task.get("due_date"),
                            "status": task.get("status")
                        })
                
                return upcoming_tasks
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка получения дедлайнов: {e}")
        return []

