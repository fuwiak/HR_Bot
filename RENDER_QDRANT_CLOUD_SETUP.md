# 🔗 Настройка Qdrant Cloud для RAG Dashboard на Render.com

## ✅ Как это работает

**RAG Dashboard (фронтенд)** → **Backend API** (`dashboard.py`/`web_interface.py`) → **QdrantLoader** → **Qdrant Cloud**

Фронтенд **НЕ** подключается к Qdrant напрямую. Все запросы идут через backend API, который использует `QdrantLoader` с настройками из переменных окружения.

---

## 📋 Шаг 1: Получите данные Qdrant Cloud

1. Перейдите на **https://cloud.qdrant.io**
2. Войдите в аккаунт
3. Выберите ваш кластер
4. Перейдите в **Data Access** → **API Keys**
5. Скопируйте:
   - **Cluster URL** (например: `https://239a4026-d673-4b8b-bfab-a99c7044e6b1.us-east4-0.gcp.cloud.qdrant.io`)
   - **API Key** (начинается с букв/цифр)

---

## 📋 Шаг 2: Добавьте переменные в Render.com

В Render Dashboard → ваш Web Service → **Environment** добавьте:

```bash
# Qdrant Cloud настройки
QDRANT_URL=https://239a4026-d673-4b8b-bfab-a99c7044e6b1.us-east4-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=ваш_api_ключ_из_qdrant_cloud
```

**Важно:**
- Замените URL на ваш реальный Cluster URL из Qdrant Cloud
- Замените API Key на ваш реальный ключ

---

## 🔍 Как код использует эти переменные

### 1. `qdrant_helper.py` (базовые функции):

```python
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
if QDRANT_API_KEY:
    # Если есть API ключ, используем Qdrant Cloud
    QDRANT_URL = os.getenv("QDRANT_URL", "https://239a4026-d673-4b8b-bfab-a99c7044e6b1.us-east4-0.gcp.cloud.qdrant.io")
else:
    # Если нет API ключа, используем локальный сервер
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
```

### 2. `qdrant_loader.py` (QdrantLoader класс):

```python
self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
self.qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY", "")

# Создаем клиент Qdrant Cloud
client_kwargs = {"url": self.qdrant_url}
if self.qdrant_api_key:
    client_kwargs["api_key"] = self.qdrant_api_key
self.client = QdrantClient(**client_kwargs)
```

### 3. `dashboard.py` (Backend API):

```python
def get_qdrant_loader() -> QdrantLoader:
    """Получает singleton экземпляр QdrantLoader"""
    return QdrantLoader()  # Автоматически использует переменные окружения
```

### 4. Фронтенд (`frontend/app/rag/page.tsx`):

```typescript
// Фронтенд вызывает backend API
const result = await testRAGQuery(query, 5);
// Backend использует QdrantLoader → Qdrant Cloud
```

---

## ✅ Проверка работы

После добавления переменных:

1. **Перезапустите сервис в Render** (Manual Deploy → Clear build cache & deploy)
2. **Откройте RAG Dashboard** в браузере
3. **Попробуйте выполнить поиск** - должно работать!

**В логах Render должно быть:**
```
Используется Qdrant Cloud: https://239a4026-d673-4b8b-bfab-a99c7044e6b1.us-east4-0.gcp.cloud.qdrant.io
```

---

## 🐛 Если не работает

### Ошибка подключения к Qdrant:

**Проверьте:**
1. Правильность `QDRANT_URL` (должен начинаться с `https://`)
2. Правильность `QDRANT_API_KEY` (скопирован полностью)
3. Доступность Qdrant Cloud кластера (проверьте в https://cloud.qdrant.io)

**Тест подключения:**
```python
# В Render можно добавить тестовый endpoint
from qdrant_helper import get_qdrant_client
client = get_qdrant_client()
print(client.get_collections())  # Должно показать коллекции
```

### Фронтенд не видит данные:

**Проверьте:**
1. Backend API доступен (проверьте `NEXT_PUBLIC_API_URL` в переменных фронтенда)
2. Backend использует правильные переменные Qdrant
3. В Qdrant есть данные (проверьте в Qdrant Cloud Dashboard)

---

## 📝 Полный список переменных для Render

```bash
# Qdrant Cloud (обязательно для RAG Dashboard)
QDRANT_URL=https://239a4026-d673-4b8b-bfab-a99c7044e6b1.us-east4-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=ваш_api_ключ

# Backend API (для фронтенда)
WEB_INTERFACE_PORT=8081
PORT=8081

# OpenRouter (для LLM)
OPENROUTER_API_KEY=ваш_ключ

# Telegram (если используется)
TELEGRAM_BOT_TOKEN=ваш_токен

# Yandex Email (если используется)
YANDEX_EMAIL=a-novoselova07@yandex.ru
YANDEX_IMAP_PASSWORD=ваш_пароль
```

---

## 🎯 Итого

**RAG Dashboard автоматически использует Qdrant Cloud**, если установлены переменные:
- ✅ `QDRANT_URL` - URL вашего Qdrant Cloud кластера
- ✅ `QDRANT_API_KEY` - API ключ из Qdrant Cloud

**Фронтенд не требует дополнительных настроек** - он работает через backend API, который уже настроен на Qdrant Cloud.

---

## ✅ Готово!

После добавления переменных и перезапуска RAG Dashboard будет работать с Qdrant Cloud! 🎉
