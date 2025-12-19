# 🚀 WEEEK API: Working Examples

## ✅ Naprawione endpointy

### Poprzednie (404 error):
```python
❌ GET /ws/projects  → 404 Not Found
❌ POST /projects    → 404 Not Found
```

### Nowe (working):
```python
✅ GET /pm/projects  → Lista projektów
✅ POST /pm/projects → Tworzenie projektu
✅ GET /tm/tasks     → Lista zadań
✅ POST /tm/tasks    → Tworzenie zadania
```

---

## 📋 Przykład 1: Lista zadań

```python
import requests

API_TOKEN = "e9b78361-0705-408a-af49-ca4300b5cf1b"
BASE_URL = "https://api.weeek.net/public/v1"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Получить все задачи
response = requests.get(f"{BASE_URL}/tm/tasks", headers=headers)

if response.status_code == 200:
    result = response.json()
    print(f"Success: {result['success']}")
    print(f"Tasks count: {len(result['tasks'])}")
    for task in result['tasks']:
        print(f"  - {task['id']}: {task.get('title', 'No title')}")
```

---

## 📝 Przykład 2: Utworzenie zadania

### Twój working example:

```python
import requests

API_TOKEN = "e9b78361-0705-408a-af49-ca4300b5cf1b"
BASE_URL = "https://api.weeek.net/public/v1"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# ✅ WORKING FORMAT
task_data = {
    "name": "Новая задача",           # NIE "title"!
    "description": "Описание задачи",
    "projectId": 1,                   # Integer ID projektu
    "boardId": 1                      # Integer ID board (opcjonalnie)
}

response = requests.post(
    f"{BASE_URL}/tm/tasks",
    headers=headers,
    json=task_data
)

if response.status_code == 200:  # API zwraca 200, nie 201!
    result = response.json()
    print(f"✅ Zadanie utworzone!")
    print(f"Task ID: {result['task']['id']}")
    print(f"Title: {result['task']['title']}")  # title w response może być None
```

### Response format:

```json
{
  "success": true,
  "task": {
    "id": 13,
    "parentId": null,
    "title": null,  ← może być null даже если podałeś "name"
    "description": "<p>Описание задачи</p>",
    "type": "action",
    "priority": null,
    "isCompleted": false,
    "projectId": 1,
    "boardId": 1,
    "boardColumnId": 1,
    "locations": [{"projectId": 1, "boardId": 1, "boardColumnId": 1}],
    "createdAt": "2025-12-19T13:07:20Z",
    "tags": [],
    "customFields": []
  }
}
```

---

## 📁 Przykład 3: Lista projektów

```python
import requests

API_TOKEN = "e9b78361-0705-408a-af49-ca4300b5cf1b"
BASE_URL = "https://api.weeek.net/public/v1"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# ✅ PRAWIDŁOWY ENDPOINT
response = requests.get(f"{BASE_URL}/pm/projects", headers=headers)

if response.status_code == 200:
    result = response.json()
    
    if "projects" in result:
        projects = result["projects"]
        print(f"📁 Projektów: {len(projects)}")
        for project in projects:
            print(f"  {project['id']}: {project['name']}")
    else:
        print("Projects list:", result)
```

---

## 🆕 Przykład 4: Utworzenie projektu

```python
import requests

API_TOKEN = "e9b78361-0705-408a-af49-ca4300b5cf1b"
BASE_URL = "https://api.weeek.net/public/v1"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Dane nowego projektu
project_data = {
    "name": "Nowy projekt HR",
    "description": "Projekt dla działu HR",
    "color": "#FF5733",         # Opcjonalnie: kolor projektu
    "isFavorite": False         # Opcjonalnie: dodać do ulubionych
}

response = requests.post(
    f"{BASE_URL}/pm/projects",
    headers=headers,
    json=project_data
)

if response.status_code == 200:
    result = response.json()
    
    if "project" in result:
        project = result["project"]
        print(f"✅ Projekt utworzony!")
        print(f"Project ID: {project['id']}")
        print(f"Name: {project['name']}")
```

---

## 🔄 Przykład 5: Aktualizacja zadania

```python
import requests

API_TOKEN = "e9b78361-0705-408a-af49-ca4300b5cf1b"
BASE_URL = "https://api.weeek.net/public/v1"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

task_id = "13"  # ID zadania do aktualizacji

# Dane do aktualizacji
update_data = {
    "title": "Zaktualizowane название",  # Można użyć "title" w update
    "description": "Nowy opis",
    "priority": 2  # 0=Low, 1=Medium, 2=High, 3=Hold
}

response = requests.put(
    f"{BASE_URL}/tm/tasks/{task_id}",
    headers=headers,
    json=update_data
)

if response.status_code == 200:
    result = response.json()
    print(f"✅ Zadanie zaktualizowane!")
    print(f"Task: {result['task']}")
```

---

## ✅ Przykład 6: Oznaczenie jako completed

```python
import requests

API_TOKEN = "e9b78361-0705-408a-af49-ca4300b5cf1b"
BASE_URL = "https://api.weeek.net/public/v1"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

task_id = "13"

# Zakończ zadanie
response = requests.post(
    f"{BASE_URL}/tm/tasks/{task_id}/complete",
    headers=headers
)

if response.status_code == 200:
    print(f"✅ Zadanie {task_id} zakończone!")
    
# Wznów zadanie
response = requests.post(
    f"{BASE_URL}/tm/tasks/{task_id}/un-complete",
    headers=headers
)

if response.status_code == 200:
    print(f"🔄 Zadanie {task_id} wznowione!")
```

---

## 🗑 Przykład 7: Usunięcie zadania

```python
import requests

API_TOKEN = "e9b78361-0705-408a-af49-ca4300b5cf1b"
BASE_URL = "https://api.weeek.net/public/v1"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

task_id = "13"

response = requests.delete(
    f"{BASE_URL}/tm/tasks/{task_id}",
    headers=headers
)

if response.status_code == 200:
    print(f"🗑 Zadanie {task_id} usunięte!")
```

---

## 🔍 Przykład 8: Filtrowanie zadań

```python
import requests

API_TOKEN = "e9b78361-0705-408a-af49-ca4300b5cf1b"
BASE_URL = "https://api.weeek.net/public/v1"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Tylko aktywne zadania projektu 1
params = {
    "projectId": 1,
    "completed": "false",
    "perPage": 20
}

response = requests.get(
    f"{BASE_URL}/tm/tasks",
    headers=headers,
    params=params
)

if response.status_code == 200:
    result = response.json()
    tasks = result["tasks"]
    print(f"📋 Aktywnych zadań: {len(tasks)}")
    for task in tasks:
        priority_emoji = ["🟢", "🟡", "🔴", "⏸"][task.get("priority", 0)]
        title = task.get("title") or "Bez tytułu"
        print(f"{priority_emoji} {title}")
```

---

## 📊 Telegram Bot - Utworzenie projektu

Dodaj komendę do bota:

```python
async def weeek_create_project_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Komenda /weeek_create_project - utworzenie projektu"""
    if not context.args:
        await update.message.reply_text(
            "❌ Podaj nazwę projektu.\n"
            "Użycie: `/weeek_create_project [nazwa]`\n\n"
            "Przykład: `/weeek_create_project Nowy projekt HR`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from weeek_helper import create_project
        
        project_name = " ".join(context.args)
        
        await update.message.reply_text(f"⏳ Tworzę projekt: {project_name}")
        
        project = await create_project(
            name=project_name,
            description=f"Utworzony przez Telegram bot, użytkownik @{update.message.from_user.username}"
        )
        
        if project:
            project_id = project.get("id")
            await update.message.reply_text(
                f"✅ Projekt utworzony!\n\n"
                f"📁 Nazwa: {project_name}\n"
                f"🆔 ID: {project_id}\n\n"
                f"Użyj `/weeek_task {project_id} | [zadanie]` aby dodać zadanie"
            )
        else:
            await update.message.reply_text("❌ Nie udało się utworzyć projektu")
            
    except Exception as e:
        log.error(f"❌ Błąd tworzenia projektu: {e}")
        await update.message.reply_text(f"❌ Błąd: {str(e)}")
```

Zarejestruj komendę:

```python
app.add_handler(CommandHandler("weeek_create_project", weeek_create_project_command))
```

---

## 🎯 Kluczowe różnice API

### ❌ NIE używaj (stare/błędne):

```python
❌ GET /ws/projects          → 404 Not Found
❌ POST /projects            → 404 Not Found  
❌ "title" w POST /tm/tasks  → może nie działać
❌ "locations" array         → niepotrzebne
```

### ✅ Używaj (working):

```python
✅ GET /pm/projects          → Lista projektów
✅ POST /pm/projects         → Utworzenie projektu
✅ GET /tm/tasks             → Lista zadań
✅ POST /tm/tasks            → Utworzenie zadania
✅ "name" w POST /tm/tasks   → WORKING format
✅ "projectId" integer       → Bezpośrednio w data
```

---

## 📝 Request vs Response format

### CREATE Task Request:
```json
{
  "name": "Task name",        ← używaj "name"
  "description": "Description",
  "projectId": 1,
  "boardId": 1
}
```

### Response:
```json
{
  "success": true,
  "task": {
    "id": 13,
    "title": null,            ← może być null!
    "description": "<p>Description</p>",
    "projectId": 1,
    ...
  }
}
```

### UPDATE Task Request:
```json
{
  "title": "New title",       ← w update używaj "title"
  "priority": 2
}
```

---

## 🔧 Bearer Token format

**ZAWSZE używaj:**

```python
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}
```

**NIE używaj:**
- `workspace_id` w parametrach
- Custom headers
- Query params dla autoryzacji

---

## ✅ Status Codes

- `200 OK` - Success (nawet dla POST!)
- `404 Not Found` - Zły endpoint
- `401 Unauthorized` - Zły token
- `400 Bad Request` - Złe dane

---

**API WEEEK fixed i działa! 🎉**
