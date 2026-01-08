# ✅ WEEEK API: Финальная рабочая версия

## 🎯 Что было исправлено

### ❌ Проблемы ДО:
```
1. Использовал /pm/projects → 404 Not Found
2. Требовал workspace_id от пользователя
3. HTML ошибки вместо JSON
```

### ✅ Решение ПОСЛЕ:
```
1. Используем /tm/projects → 200 OK, работает!
2. Bearer token автоматически дает доступ к workspace
3. Чистый JSON ответ с проектами
```

---

## 📋 Правильные endpoints (из твоего working code)

| Операция | Endpoint | Метод | Работает? |
|----------|----------|-------|-----------|
| Workspace info | `/ws` | GET | ✅ |
| Список проектов | `/tm/projects` | GET | ✅ |
| Создать проект | `/tm/projects` | POST | ✅ |
| Один проект | `/tm/projects/{id}` | GET | ✅ |
| Список задач | `/tm/tasks` | GET | ✅ |
| Создать задачу | `/tm/tasks` | POST | ✅ |
| Одна задача | `/tm/tasks/{id}` | GET | ✅ |
| Обновить задачу | `/tm/tasks/{id}` | PUT | ✅ |

---

## 🔧 Код (weeek_helper.py)

### get_workspace_info()

```python
async def get_workspace_info() -> Optional[Dict]:
    """
    Получить информацию о workspace
    API: GET /ws
    """
    url = f"{WEEEK_API_URL}/ws"
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            result = await response.json()
            return result.get("workspace")
```

**Response:**
```json
{
  "workspace": {
    "id": 857376,
    "title": "Обучение",
    "isPersonal": false,
    "logo": null
  }
}
```

---

### get_projects()

```python
async def get_projects() -> List[Dict]:
    """
    Получить список проектов
    API: GET /tm/projects
    """
    url = f"{WEEEK_API_URL}/tm/projects"
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            result = await response.json()
            return result.get("projects", [])
```

**Response:**
```json
{
  "success": true,
  "projects": [
    {
      "id": 1,
      "title": "Проект",
      "description": "",
      "color": "#E650FF",
      "isPrivate": false,
      "logoLink": null,
      "team": [...]
    }
  ]
}
```

---

### create_task()

```python
async def create_task(project_id, title, description=""):
    """
    Создать задачу
    API: POST /tm/tasks
    """
    url = f"{WEEEK_API_URL}/tm/tasks"
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}
    
    data = {
        "name": title,           # ← "name" не "title" в request!
        "description": description,
        "projectId": int(project_id),
        "type": "action"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            result = await response.json()
            return result.get("task")
```

**Response:**
```json
{
  "success": true,
  "task": {
    "id": 13,
    "title": null,           ← может быть null!
    "description": "<p>Описание</p>",
    "projectId": 1,
    "type": "action",
    "priority": null,
    "isCompleted": false
  }
}
```

---

## 📱 Команды Telegram бота

### 1. Информация о workspace

```bash
/weeek_info
```

**Result:**
```
📊 WEEEK Workspace Info

🆔 ID: 857376
📝 Название: Обучение
👤 Персональный: Нет

✅ Используйте команды WEEEK:
• /weeek_projects - список проектов
• /weeek_create_project [название] - создать проект
```

---

### 2. Список проектов

```bash
/weeek_projects
```

**Result:**
```
📋 Проекты в WEEEK (всего: 2)

1. Семейный бюджет (учебный проект School21)
   ID: 2 • #3AC648

2. Проект
   ID: 1 • #E650FF
```

---

### 3. Создать проект

```bash
/weeek_create_project HR Консалтинг 2025
```

**Result:**
```
✅ Проект создан в WEEEK!

📁 Название: HR Консалтинг 2025
🆔 ID: 3

Теперь можете добавить задачи:
/weeek_task HR Консалтинг 2025 | Первая задача
```

---

### 4. Создать задачу

```bash
/weeek_task Проект | Согласовать КП с клиентом
```

**Result:**
```
✅ Задача создана в WEEEK!

📁 Проект: Проект
📝 Задача: Согласовать КП с клиентом
```

---

### 5. Обновить задачу (интерактивно)

```bash
/weeek_update
→ Выбрать проект
→ Выбрать задачу
→ Изменить название/описание/приоритет/тип
```

---

## 🔑 Ключевые изменения

### 1. Endpoints

**ДО (НЕ работало):**
```python
GET /pm/projects  → 404
GET /ws/projects  → 404
```

**ПОСЛЕ (работает):**
```python
GET /tm/projects  → 200 OK ✅
GET /ws           → 200 OK ✅
```

---

### 2. Workspace ID

**ДО:**
```python
# Требовал от пользователя
workspace_id = UserWeeekWorkspace.get(user_id)
params = {"workspaceId": workspace_id}
```

**ПОСЛЕ:**
```python
# Bearer token автоматически дает доступ
# workspace_id НЕ нужен!
headers = {"Authorization": f"Bearer {API_TOKEN}"}
```

---

### 3. Поля объектов

**ДО:**
```python
project.get("name")    # ← Не работало
```

**ПОСЛЕ:**
```python
project.get("title")   # ← Правильное поле!
```

---

### 4. Create Task format

**ДО (НЕ работало):**
```python
data = {
    "title": "Task",           # ← Неправильное поле
    "locations": [{"projectId": 1}]  # ← Ненужная обертка
}
```

**ПОСЛЕ (работает):**
```python
data = {
    "name": "Task",            # ← Правильное поле!
    "projectId": 1,            # ← Напрямую
    "description": "...",
    "type": "action"
}
```

---

## 📊 Bearer Token

**Всегда используется:**
```python
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}
```

**В .env:**
```env
WEEEEK_TOKEN=e9b78361-0705-408a-af49-ca4300b5cf1b
WEEEK_API_URL=https://api.weeek.net/public/v1
```

---

## ✅ Результаты

### Было:
```
❌ Проектов не найдено или WEEEK недоступен
❌ 404 Not Found
❌ <!DOCTYPE html>...
```

### Стало:
```
✅ 200 OK
✅ JSON с проектами
✅ Workspace ID: 857376
✅ Проектов: 2
```

---

## 🎉 Итого

**Что работает:**
- ✅ `/weeek_info` - информация о workspace
- ✅ `/weeek_projects` - список проектов (из `/tm/projects`)
- ✅ `/weeek_create_project` - создание проекта
- ✅ `/weeek_task` - создание задачи (с `name` полем)
- ✅ `/weeek_update` - обновление задачи (интерактивно)
- ✅ `/weeek_tasks` - список задач проекта

**Bearer token автоматически:**
- ✅ Дает доступ к workspace 857376
- ✅ Показывает все проекты workspace
- ✅ Workspace ID НЕ нужен от пользователя

---

## 📚 Документация

- **WEEEK_WORKING_EXAMPLES.md** - Working Python examples
- **WEEEK_FINAL_WORKING.md** - Этот файл (финальная версия)
- **WEEEK_TELEGRAM_CRUD.md** - Full CRUD через Telegram

---

**🎉 WEEEK API полностью работает! Используем твой working code с `/tm/projects` и Bearer token!**
