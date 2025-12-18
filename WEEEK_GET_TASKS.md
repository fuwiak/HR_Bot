# 📋 WEEEK: Получение задач

## Описание

Полная реализация метода `GET /tm/tasks` для получения задач из WEEEK с поддержкой всех параметров фильтрации.

---

## Функция `get_tasks()`

### Сигнатура

```python
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
) -> Dict[str, any]
```

### Параметры

| Параметр | Тип | Описание |
|----------|-----|----------|
| `day` | str | Дата в формате `dd.mm.yyyy` |
| `user_id` | str | ID пользователя (исполнителя) |
| `project_id` | int | ID проекта для фильтрации |
| `completed` | bool | `True` - только завершенные, `False` - только активные |
| `board_id` | int | ID доски |
| `board_column_id` | int | ID колонки доски |
| `task_type` | str | Тип задачи: `action`, `meet`, `call` |
| `priority` | int | 0=Low, 1=Medium, 2=High, 3=Hold |
| `tags` | List[str] | Список ID тегов |
| `search` | str | Текст для поиска в названии и описании |
| `per_page` | int | Количество задач на страницу (default: 50) |
| `offset` | int | Смещение для пагинации (default: 0) |
| `sort_by` | str | Сортировка: `name`, `type`, `priority`, `duration`, `overdue`, `created`, `date` |
| `start_date` | str | Начальная дата `dd.mm.yyyy` (требуется с `end_date`) |
| `end_date` | str | Конечная дата `dd.mm.yyyy` (требуется с `start_date`) |
| `all_tasks` | bool | Показать все включая удаленные (игнорирует `completed`) |

### Возвращает

```python
{
    "success": True,
    "tasks": [...],  # Список задач
    "hasMore": False  # Есть ли еще задачи
}
```

---

## Примеры использования

### 1. Все задачи проекта

```python
from weeek_helper import get_tasks
import asyncio

result = asyncio.run(get_tasks(project_id=123))

print(f"Задач: {len(result['tasks'])}")
for task in result['tasks']:
    print(f"- {task.get('title')}")
```

### 2. Только активные задачи

```python
result = asyncio.run(get_tasks(
    project_id=123,
    completed=False
))
```

### 3. Задачи с высоким приоритетом

```python
result = asyncio.run(get_tasks(
    project_id=123,
    priority=2  # High
))
```

### 4. Задачи на конкретную дату

```python
result = asyncio.run(get_tasks(
    day="25.12.2025"
))
```

### 5. Задачи за период

```python
result = asyncio.run(get_tasks(
    start_date="01.12.2025",
    end_date="31.12.2025"
))
```

### 6. Поиск задач по тексту

```python
result = asyncio.run(get_tasks(
    search="согласовать КП"
))
```

### 7. Задачи конкретного пользователя

```python
result = asyncio.run(get_tasks(
    user_id="user_123",
    completed=False
))
```

### 8. Задачи типа "встреча"

```python
result = asyncio.run(get_tasks(
    task_type="meet"
))
```

### 9. Пагинация

```python
# Первая страница
page1 = asyncio.run(get_tasks(
    project_id=123,
    per_page=20,
    offset=0
))

# Вторая страница
if page1["hasMore"]:
    page2 = asyncio.run(get_tasks(
        project_id=123,
        per_page=20,
        offset=20
    ))
```

### 10. Сортировка

```python
# По приоритету (убывание)
result = asyncio.run(get_tasks(
    project_id=123,
    sort_by="-priority"
))

# По дате создания (возрастание)
result = asyncio.run(get_tasks(
    project_id=123,
    sort_by="created"
))
```

---

## Обновлен `get_project_deadlines()`

### До:

```python
# Старая реализация с примерным API
async def get_project_deadlines(days_ahead=7):
    url = f"{WEEEK_API_URL}/tasks"  # Неправильный endpoint
    # ...
```

### После:

```python
# Использует правильный get_tasks()
async def get_project_deadlines(days_ahead=7):
    start_date = datetime.now().strftime("%d.%m.%Y")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%d.%m.%Y")
    
    result = await get_tasks(
        completed=False,
        start_date=start_date,
        end_date=end_date,
        per_page=100
    )
    
    return result["tasks"]
```

---

## Использование в боте

### Команда `/status`

```python
async def status_command(update, context):
    from weeek_helper import get_project_deadlines
    
    tasks = await get_project_deadlines(days_ahead=7)
    
    text = f"📋 Задачи на ближайшие 7 дней:\n\n"
    for task in tasks:
        text += f"• {task['name']}\n"
        text += f"  Дедлайн: {task['due_date']}\n\n"
    
    await update.message.reply_text(text)
```

### Просмотр задач проекта

```python
result = await get_tasks(project_id=project_id, completed=False)

text = f"📋 Активные задачи проекта:\n\n"
for task in result["tasks"]:
    title = task.get("title", "Без названия")
    priority_emoji = ["🟢", "🟡", "🔴", "⏸"][task.get("priority", 0)]
    text += f"{priority_emoji} {title}\n"
```

---

## Формат ответа API

### Успешный ответ

```json
{
  "success": true,
  "tasks": [
    {
      "id": "task_123",
      "title": "Согласовать КП",
      "description": "Описание задачи",
      "projectId": 123,
      "userId": "user_456",
      "type": "action",
      "priority": 1,
      "completed": false,
      "day": "25.12.2025",
      "dueDate": "2025-12-25",
      "startDate": "2025-12-20",
      "duration": 120,
      "tags": ["tag1", "tag2"],
      "boardId": 10,
      "boardColumnId": 20,
      "created": "2025-12-18T10:00:00Z"
    }
  ],
  "hasMore": false
}
```

### Ошибка

```json
{
  "success": false,
  "error": "Error message"
}
```

---

## Логирование

```
📤 [WEEEK] Запрос задач с параметрами: {'projectId': 123, 'completed': 'false', 'perPage': 50}
✅ [WEEEK] Получено задач: 15, hasMore: false
```

---

## Обработка ошибок

```python
result = await get_tasks(project_id=123)

if not result["success"]:
    print("Ошибка получения задач")
    return

tasks = result["tasks"]
has_more = result["hasMore"]

if has_more:
    # Есть еще задачи, можно загрузить следующую страницу
    pass
```

---

## Типы данных

### Priority

```
0 = Low (🟢)
1 = Medium (🟡)
2 = High (🔴)
3 = Hold (⏸)
```

### Type

```
"action" = Обычная задача
"meet" = Встреча
"call" = Звонок
```

### Sort By

```
"name" - по названию (A-Z)
"-name" - по названию (Z-A)
"priority" - по приоритету (возрастание)
"-priority" - по приоритету (убывание)
"date" - по дате
"created" - по дате создания
"overdue" - по просрочке
```

---

## Итого

✅ **Полная реализация** GET /tm/tasks со всеми параметрами  
✅ **Фильтрация** по проекту, пользователю, статусу, приоритету  
✅ **Поиск** по тексту в названии и описании  
✅ **Пагинация** с поддержкой hasMore  
✅ **Сортировка** по различным полям  
✅ **Даты** в правильном формате dd.mm.yyyy  
✅ **Логирование** для отладки  
✅ **Обработка ошибок** с возвратом структуры  

**Получение задач из WEEEK полностью работает! 🎉**
