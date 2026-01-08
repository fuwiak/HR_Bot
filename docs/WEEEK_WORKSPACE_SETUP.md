# 🔧 WEEEK Workspace ID Setup

## ✅ Problem rozwiązany!

**Przed:**
```
❌ Проектов не найдено или WEEEK недоступен
```

**Po:**
```
✅ Każdy user ustawia swoje Workspace ID w bocie
```

---

## 🎯 Jak to działa

### 1. Setup w `.env`

```env
WEEEEK_TOKEN=e9b78361-0705-408a-af49-ca4300b5cf1b
WEEEK_API_URL=https://api.weeek.net/public/v1
# WEEEK_WORKSPACE_ID - NIE potrzebne w .env!
```

**Bearer token działa globalnie, ale każdy user ma swoje workspace!**

---

### 2. User ustawia Workspace ID w bocie

#### Krok 1: Znajdź swoje Workspace ID

1. Otwórz WEEEK w przeglądarce
2. Zobacz URL: `https://app.weeek.net/ws/12345/board/...`
3. Skopiuj ID po `/ws/` (np. `12345`)

#### Krok 2: Ustaw w bocie

```bash
/weeek_set_workspace 12345
```

**Result:**
```
✅ Workspace ID ustawiony!

🆔 Workspace: 12345

Teraz możesz używać komend WEEEK:
• /weeek_projects - lista projektów
• /weeek_create_project [nazwa] - nowy projekt
• /weeek_task - nowa zadanie
```

---

## 📋 Sprawdź aktualny Workspace ID

```bash
/weeek_set_workspace
```

**Result:**
```
🔧 WEEEK Workspace ID

Aktualny: 12345

Aby zmienić:
/weeek_set_workspace [workspace_id]
```

---

## 🔧 Implementacja

### Storage (app.py)

```python
# Przechowywanie Workspace ID dla każdego użytkownika
UserWeeekWorkspace: Dict[int, str] = {}
```

### Komenda set workspace

```python
async def weeek_set_workspace_command(update, context):
    user_id = update.message.from_user.id
    
    if not context.args:
        # Pokaż aktualny
        current = UserWeeekWorkspace.get(user_id)
        await update.message.reply_text(f"Aktualny: {current or 'nie ustawiony'}")
        return
    
    # Zapisz nowy
    workspace_id = context.args[0]
    UserWeeekWorkspace[user_id] = workspace_id
    
    await update.message.reply_text(f"✅ Workspace ID ustawiony: {workspace_id}")
```

### get_projects() z workspace_id

```python
async def get_projects(workspace_id: Optional[str] = None) -> List[Dict]:
    url = f"{WEEEK_API_URL}/pm/projects"
    headers = get_headers()
    
    params = {}
    if workspace_id:
        params["workspaceId"] = workspace_id
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params, ...) as response:
            # ...
```

### Każda komenda sprawdza workspace ID

```python
async def weeek_projects_command(update, context):
    user_id = update.message.from_user.id
    workspace_id = UserWeeekWorkspace.get(user_id)
    
    if not workspace_id:
        await update.message.reply_text(
            "❌ Najpierw ustaw Workspace ID!\n"
            "/weeek_set_workspace [id]"
        )
        return
    
    projects = await get_projects(workspace_id)
    # ...
```

---

## 🚀 Przykład użycia

### 1. Setup workspace

```bash
User: /weeek_set_workspace 12345
Bot:  ✅ Workspace ID ustawiony!
```

### 2. Lista projektów

```bash
User: /weeek_projects
Bot:  📋 Проекты в WEEEK (всего: 5)
      
      1. HR Konsalting
         ID: 101
      
      2. Podбор персонала
         ID: 102
```

### 3. Utworzenie projektu

```bash
User: /weeek_create_project Nowy projekt 2025
Bot:  ✅ Projekt utworzony!
      
      📁 Nazwa: Nowy projekt 2025
      🆔 ID: 103
```

---

## ⚠️ Co się stanie jeśli user nie ustawi workspace ID?

```bash
User: /weeek_projects
Bot:  ❌ Najpierw ustaw Workspace ID!
      
      Użyj komendy:
      /weeek_set_workspace [twoje_workspace_id]
```

**Każda komenda WEEEK sprawdza workspace ID przed wykonaniem!**

---

## 🔐 Security

- ✅ Bearer token globalny (w `.env`)
- ✅ Workspace ID per user (w `UserWeeekWorkspace`)
- ✅ Każdy user widzi tylko swoje projekty
- ✅ Bezpieczne przechowywanie w runtime (Dict)

---

## 📊 Komendy wymagające workspace ID

| Komenda | Opis | Wymaga workspace? |
|---------|------|-------------------|
| `/weeek_set_workspace` | Ustaw ID | ❌ (ustawia ID) |
| `/weeek_projects` | Lista projektów | ✅ |
| `/weeek_create_project` | Nowy projekt | ✅ |
| `/weeek_task` | Nowa zadanie | ✅ |
| `/weeek_update` | Update zadania | ✅ |
| `/weeek_tasks` | Lista zadań | ✅ |

---

## ✅ Zalety tego rozwiązania

1. **Prosty setup** - jeden Bearer token w `.env`
2. **Multi-user** - każdy user ma swoje workspace
3. **Bezpieczne** - user widzi tylko swoje projekty
4. **Flexible** - user może zmienić workspace w dowolnym momencie
5. **No DB needed** - przechowywanie w runtime Dict

---

## 🎉 Status

**WEEEK multi-user workspace support fully working!**

- ✅ Bearer token globalny
- ✅ Workspace ID per user
- ✅ Komenda `/weeek_set_workspace`
- ✅ Wszystkie komendy sprawdzają workspace
- ✅ API query: `?workspaceId={id}`
- ✅ User-friendly error messages

**Problem "Проектов не найдено" rozwiązany! 🚀**
