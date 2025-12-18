"""
WEEEK Integration Module
Интеграция с WEEEK API для управления проектами и задачами
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
WEEEK_API_KEY = os.getenv("WEEEEK_TOKEN") or os.getenv("WEEEK_API_KEY")
WEEEK_API_URL = os.getenv("WEEEK_API_URL", "https://api.weeek.net/public/v1")
WEEEK_WORKSPACE_ID = os.getenv("WEEEK_WORKSPACE_ID")

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
    Получить список всех проектов в workspace
    
    Returns:
        Список словарей с данными проектов
    """
    if not WEEEK_API_KEY or not WEEEK_WORKSPACE_ID:
        log.error("❌ WEEEK_API_KEY или WEEEK_WORKSPACE_ID не установлены")
        return []
    
    url = f"{WEEEK_API_URL}/workspaces/{WEEEK_WORKSPACE_ID}/projects"
    headers = get_headers()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [WEEEK] Ошибка получения списка проектов: {response.status} - {error_text}")
                    return []
                
                result = await response.json()
                projects = result if isinstance(result, list) else result.get("projects", [])
                log.info(f"✅ [WEEEK] Получено проектов: {len(projects)}")
                return projects
    except Exception as e:
        log.error(f"❌ [WEEEK] Ошибка получения списка проектов: {e}")
        return []

# ===================== TASK OPERATIONS =====================

async def create_task(
    project_id: str,
    title: str,
    description: str = "",
    due_date: Optional[str] = None,
    assignee_id: Optional[str] = None,
    name: Optional[str] = None  # Для обратной совместимости
) -> Optional[Dict]:
    """
    Создать задачу в проекте
    
    Args:
        project_id: ID проекта
        title: Название задачи (или name для обратной совместимости)
        description: Описание задачи
        due_date: Дата дедлайна (ISO format)
        assignee_id: ID исполнителя
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
        log.error("❌ Не указано название задачи (title или name)")
        return None
    
    url = f"{WEEEK_API_URL}/projects/{project_id}/tasks"
    headers = get_headers()
    
    data = {
        "title": task_title,
        "description": description
    }
    
    if due_date:
        data["due_date"] = due_date
    if assignee_id:
        data["assignee_id"] = assignee_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [WEEEK] Ошибка создания задачи: {response.status} - {error_text}")
                    return None
                
                result = await response.json()
                log.info(f"✅ [WEEEK] Задача создана: {task_title} в проекте {project_id}")
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

