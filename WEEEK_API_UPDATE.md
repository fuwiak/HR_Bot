# 🔄 Обновление WEEEK API

## Проблема

```
❌ [WEEEK] Ошибка получения списка проектов: 404
```

### Причина

Использовались неправильные эндпоинты API. WEEEK API использует другую структуру URL.

---

## Решение

### Обновлены все эндпоинты согласно официальной документации

**API Base URL:** `https://api.weeek.net/public/v1`

### Проекты

**Было (неправильно):**
```
GET /workspaces/{workspace_id}/projects
```

**Стало (правильно):**
```
GET /ws/projects
```

### Задачи

**Было (неправильно):**
```
POST /projects/{project_id}/tasks
```

**Стало (правильно):**
```
POST /tm/tasks
Body: {
  "locations": [{"projectId": 123}],
  "title": "Task name",
  "type": "action"
}
```

---

## Новые функции API

### 1. `get_projects()`
```python
GET /ws/projects

Возвращает: {"success": true, "projects": [...]}
```

### 2. `create_task(project_id, title, ...)`
```python
POST /tm/tasks
Body: {
  "locations": [{"projectId": project_id}],
  "title": title,
  "type": "action",  # or "meet", "call"
  "description": "",
  "priority": 0-3,  # 0=Low, 1=Medium, 2=High, 3=Hold
  "day": "dd.mm.yyyy"
}
```

### 3. `get_tasks(project_id, completed, ...)`
```python
GET /tm/tasks?projectId=123&completed=false

Параметры:
- projectId: фильтр по проекту
- completed: показать завершенные
- startDate: dd.mm.yyyy
- endDate: dd.mm.yyyy
- perPage: количество
```

### 4. `complete_task(task_id)`
```python
POST /tm/tasks/{id}/complete
```

### 5. `uncomplete_task(task_id)`
```python
POST /tm/tasks/{id}/un-complete
```

### 6. `update_task(task_id, **kwargs)`
```python
PUT /tm/tasks/{id}
Body: {
  "title": "",
  "priority": 0-3,
  "type": "action",
  "startDate": "Y-m-d",
  "dueDate": "Y-m-d",
  "duration": 60  # минуты
}
```

### 7. `delete_task(task_id)`
```python
DELETE /tm/tasks/{id}
```

---

## Что изменилось

### weeek_helper.py

**1. Добавлено логирование при инициализации:**
```python
log.info(f"🔧 WEEEK API URL: {WEEEK_API_URL}")
if WEEEK_API_KEY:
    log.info(f"✅ WEEEK API KEY установлен")
```

**2. Обновлен `get_projects()`:**
```python
url = f"{WEEEK_API_URL}/ws/projects"
# Возвращает {"success": true, "projects": [...]}
```

**3. Обновлен `create_task()`:**
```python
url = f"{WEEEK_API_URL}/tm/tasks"
data = {
    "locations": [{"projectId": int(project_id)}],
    "title": task_title,
    "type": task_type  # "action", "meet", "call"
}
```

**4. Добавлена `get_tasks()`:**
```python
async def get_tasks(
    project_id=None,
    completed=None,
    start_date=None,
    end_date=None
)
```

**5. Добавлены функции управления задачами:**
- `complete_task(task_id)`
- `uncomplete_task(task_id)`
- `update_task(task_id, **kwargs)`
- `delete_task(task_id)`

**6. Обновлен `get_project_deadlines()`:**
```python
# Использует новый get_tasks() с правильными датами
start_date = datetime.now().strftime("%d.%m.%Y")
end_date = (datetime.now() + timedelta(days=7)).strftime("%d.%m.%Y")
```

---

## Настройка

### Переменные окружения

```bash
# .env
WEEEEK_TOKEN=your_token_here  # или WEEEK_API_KEY
WEEEK_WORKSPACE_ID=your_workspace_id
```

**Примечание:** `WEEEK_WORKSPACE_ID` больше не используется в URL, но может понадобиться для других операций.

---

## Тестирование

### Проверка подключения

```python
from weeek_helper import get_projects
import asyncio

projects = asyncio.run(get_projects())
print(f"Проектов: {len(projects)}")
for p in projects:
    print(f"- {p.get('name')}")
```

### Создание задачи

```python
from weeek_helper import create_task
import asyncio

task = asyncio.run(create_task(
    project_id="123",
    title="Тестовая задача",
    description="Создано через API",
    priority=1  # Medium
))
print(task)
```

### Получение задач

```python
from weeek_helper import get_tasks
import asyncio

tasks = asyncio.run(get_tasks(project_id=123, completed=False))
print(f"Активных задач: {len(tasks)}")
```

---

## Логирование

При запуске бота вы увидите:

```
🔧 WEEEK API URL: https://api.weeek.net/public/v1
✅ WEEEK API KEY установлен (длина: 36)
✅ WEEEK WORKSPACE ID: 12345
```

При работе с API:

```
📤 [WEEEK] Создаю задачу: Test task в проекте 123
✅ [WEEEK] Задача создана: Test task (ID: 456)
✅ [WEEEK] Получено проектов: 5
✅ [WEEEK] Получено задач: 12
```

---

## Примеры использования в боте

### Список проектов:
```
/menu → 📋 Проекты → 📋 Мои проекты
```

### Создание задачи:
```
/menu → 📋 Проекты → ➕ Создать задачу
→ [Выбрать проект]
→ [Ввести название задачи]
```

### Через команду:
```
/weeek_task [проект] | [задача]
```

---

## Обработка ошибок

### 404 Not Found
```
❌ [WEEEK] Ошибка получения проектов: 404
```
**Решение:** Проверьте WEEEK_API_KEY

### 401 Unauthorized
```
❌ [WEEEK] Ошибка: 401
```
**Решение:** Проверьте токен WEEEEK_TOKEN

### 400 Bad Request
```
❌ [WEEEK] Ошибка создания задачи: 400
```
**Решение:** Проверьте формат данных (projectId должен быть int)

---

## Формат данных

### Dates

**Для фильтров (startDate, endDate):**
```
dd.mm.yyyy (например: 18.12.2025)
```

**Для обновления задач:**
```
Y-m-d (например: 2025-12-18)
```

### Priority

```
0 = Low
1 = Medium
2 = High
3 = Hold
```

### Type

```
"action" = Обычная задача (default)
"meet" = Встреча
"call" = Звонок
```

---

## Итого

✅ **Обновлены все эндпоинты** согласно официальной документации  
✅ **Добавлены новые функции** для управления задачами  
✅ **Улучшено логирование** для отладки  
✅ **Правильный формат данных** для API  
✅ **Обработка ошибок** с детальными сообщениями  
✅ **Совместимость** с существующим кодом  

**WEEEK API интеграция обновлена и работает! 🎉**
