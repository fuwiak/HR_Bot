# 🚂 Деплой трех сервисов на Railway

Railway не поддерживает docker-compose.yml, но позволяет создать несколько сервисов в одном проекте.

## 📦 Структура

```
Railway Project: HR2137-Bot
│
├── Service 1: Telegram Bot
│   ├── Dockerfile: Dockerfile.telegram
│   ├── Port: 8080
│   └── URL: telegram-bot-production.up.railway.app
│
├── Service 2: Backend API  
│   ├── Dockerfile: Dockerfile.backend
│   ├── Port: 8081
│   └── URL: backend-production.up.railway.app
│
└── Service 3: Frontend
    ├── Dockerfile: Dockerfile.frontend
    ├── Port: 3000
    └── URL: frontend-production.up.railway.app
```

## 🚀 Быстрый деплой

### Шаг 1: Создание проекта

1. https://railway.app → **New Project** → **Empty Project**
2. Назовите: `HR2137-Bot`

### Шаг 2: Telegram Bot сервис

1. **"+ New"** → **"GitHub Repo"** → выберите `HR_Bot`
2. **Settings** → **Build** → **Dockerfile Path**: `Dockerfile.telegram`
3. **Settings** → **Networking** → **Generate Domain**
4. **Variables**:
   ```bash
   TELEGRAM_TOKEN=your_token
   OPENROUTER_API_KEY=your_key
   USE_WEBHOOK=true
   PORT=8080
   WEBHOOK_URL=https://your-telegram-bot-url.up.railway.app
   ```

### Шаг 3: Backend сервис

1. **"+ New"** → **"GitHub Repo"** → выберите `HR_Bot`
2. **Settings** → **Build** → **Dockerfile Path**: `Dockerfile.backend`
3. **Settings** → **Networking** → **Generate Domain** → скопируйте URL
4. **Variables**:
   ```bash
   WEB_INTERFACE_PORT=8081
   PORT=8081
   SECRET_KEY=your-secret-key
   ```

### Шаг 4: Frontend сервис

1. **"+ New"** → **"GitHub Repo"** → выберите `HR_Bot`
2. **Settings** → **Build** → **Dockerfile Path**: `Dockerfile.frontend`
3. **Settings** → **Networking** → **Generate Domain**
4. **Variables**:
   ```bash
   PORT=3000
   NODE_ENV=production
   NEXT_PUBLIC_API_URL=https://backend-production.up.railway.app
   BACKEND_URL=https://backend-production.up.railway.app
   ```
   **Важно**: Замените на реальный URL вашего Backend сервиса!

### Шаг 5: Общие переменные

**Project Settings** → **Variables** (доступны всем сервисам):
```bash
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key
OPENROUTER_API_KEY=your_api_key
WEEEEK_TOKEN=your_weeek_token
HRTIME_API_KEY=your_hrtime_key
YANDEX_EMAIL=your_email
YANDEX_PASSWORD=your_password
TELEGRAM_CONSULTANT_CHAT_ID=your_chat_id
```

## ✅ Проверка

1. **Telegram Bot**: Отправьте `/start` боту
2. **Backend**: Откройте `https://backend-url/health`
3. **Frontend**: Откройте `https://frontend-url`

## 📚 Документация

- **RAILWAY_DEPLOY_MULTI.md** - полная инструкция
- **RAILWAY_SETUP_MULTI.md** - пошаговая настройка
- **RAILWAY_MULTI_SERVICE.md** - технические детали

---

**Готово! Три сервиса развернуты 🚂**
