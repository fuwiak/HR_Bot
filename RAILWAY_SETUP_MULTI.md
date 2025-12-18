# 🚂 Настройка нескольких сервисов на Railway

Пошаговая инструкция по созданию трех отдельных сервисов на Railway.

## 📋 Что будет развернуто

1. **Telegram Bot** - порт 8080 (webhook)
2. **Backend API** - порт 8081 (FastAPI)
3. **Frontend** - порт 3000 (Next.js)

## 🎯 Способ 1: Через Railway Dashboard (Рекомендуется)

### Шаг 1: Создание проекта

1. Откройте https://railway.app
2. **New Project** → **Empty Project**
3. Назовите проект: `HR2137-Bot`

### Шаг 2: Создание Telegram Bot сервиса

1. В проекте нажмите **"+ New"** → **"GitHub Repo"**
2. Выберите репозиторий `HR_Bot`
3. Railway начнет сборку
4. **Settings** → **Build** → **Dockerfile Path**: `Dockerfile.telegram`
5. **Settings** → **Networking** → **Generate Domain**
6. **Variables** → добавьте:
   ```
   TELEGRAM_TOKEN=your_token
   OPENROUTER_API_KEY=your_key
   USE_WEBHOOK=true
   PORT=8080
   ```

### Шаг 3: Создание Backend сервиса

1. В том же проекте **"+ New"** → **"GitHub Repo"**
2. Выберите тот же репозиторий `HR_Bot`
3. **Settings** → **Build** → **Dockerfile Path**: `Dockerfile.backend`
4. **Settings** → **Networking** → **Generate Domain**
5. **Variables** → добавьте:
   ```
   WEB_INTERFACE_PORT=8081
   PORT=8081
   SECRET_KEY=your_secret_key
   ```

### Шаг 4: Создание Frontend сервиса

1. В том же проекте **"+ New"** → **"GitHub Repo"**
2. Выберите тот же репозиторий `HR_Bot`
3. **Settings** → **Build** → **Dockerfile Path**: `Dockerfile.frontend`
4. **Settings** → **Networking** → **Generate Domain**
5. **Variables** → добавьте:
   ```
   PORT=3000
   NODE_ENV=production
   NEXT_PUBLIC_API_URL=https://your-backend-service.up.railway.app
   BACKEND_URL=https://your-backend-service.up.railway.app
   ```

**Важно**: Замените `your-backend-service.up.railway.app` на реальный домен вашего Backend сервиса.

## 🎯 Способ 2: Через Railway CLI

```bash
# Установка
npm i -g @railway/cli

# Вход
railway login

# Создание проекта
railway init
railway link

# Создание Telegram Bot сервиса
railway service create telegram-bot
cd .railway
echo 'Dockerfile.telegram' > dockerfile
cd ..
railway variables set TELEGRAM_TOKEN=your_token --service telegram-bot
railway variables set OPENROUTER_API_KEY=your_key --service telegram-bot
railway up --service telegram-bot

# Создание Backend сервиса
railway service create backend
cd .railway
echo 'Dockerfile.backend' > dockerfile
cd ..
railway variables set WEB_INTERFACE_PORT=8081 --service backend
railway up --service backend

# Создание Frontend сервиса
railway service create frontend
cd .railway
echo 'Dockerfile.frontend' > dockerfile
cd ..
railway variables set NEXT_PUBLIC_API_URL=https://backend-url --service frontend
railway up --service frontend
```

## 🔗 Настройка связей между сервисами

### 1. Получите URL каждого сервиса

В Railway Dashboard для каждого сервиса:
- **Settings** → **Networking** → скопируйте домен

Пример:
- Telegram Bot: `telegram-bot-production.up.railway.app`
- Backend: `backend-production.up.railway.app`
- Frontend: `frontend-production.up.railway.app`

### 2. Настройте Frontend для работы с Backend

В переменных Frontend сервиса:
```bash
NEXT_PUBLIC_API_URL=https://backend-production.up.railway.app
BACKEND_URL=https://backend-production.up.railway.app
```

### 3. Настройте Telegram Bot webhook

В переменных Telegram Bot сервиса:
```bash
WEBHOOK_URL=https://telegram-bot-production.up.railway.app
# Или
RAILWAY_PUBLIC_DOMAIN=telegram-bot-production.up.railway.app
```

## 📝 Переменные окружения по сервисам

### Общие (Project Variables - доступны всем):

Добавьте в **Project Settings** → **Variables**:
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

### Telegram Bot сервис:

```bash
TELEGRAM_TOKEN=required
USE_WEBHOOK=true
PORT=8080
WEBHOOK_URL=https://telegram-bot-service.up.railway.app
```

### Backend сервис:

```bash
WEB_INTERFACE_PORT=8081
PORT=8081
SECRET_KEY=required
```

### Frontend сервис:

```bash
PORT=3000
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://backend-service.up.railway.app
BACKEND_URL=https://backend-service.up.railway.app
```

## ✅ Проверка работы

### Telegram Bot:
```bash
# Проверьте логи
railway logs --service telegram-bot

# Должно быть:
# ✅ Webhook установлен
# ✅ Бот запущен с webhook
```

### Backend:
```bash
# Откройте в браузере
https://backend-service.up.railway.app/health

# Должен вернуть: {"status": "ok"}
```

### Frontend:
```bash
# Откройте в браузере
https://frontend-service.up.railway.app

# Должна открыться главная страница
```

## 🔄 Обновление кода

При push в репозиторий Railway автоматически пересоберет все сервисы, которые используют этот репозиторий.

Или вручную:
```bash
railway up --service telegram-bot
railway up --service backend
railway up --service frontend
```

## 🐛 Troubleshooting

### Проблема: Не могу указать Dockerfile Path

**Решение**: Railway определяет Dockerfile автоматически. Если нужно использовать другой:
1. Переименуйте нужный Dockerfile в `Dockerfile` временно
2. Или используйте настройки сервиса → Build → Dockerfile Path

### Проблема: Frontend не подключается к Backend

**Решение**:
1. Проверьте `NEXT_PUBLIC_API_URL` в переменных Frontend
2. Убедитесь что Backend сервис запущен
3. Проверьте CORS в Backend (если нужно)

### Проблема: Переменные не применяются

**Решение**:
1. Убедитесь что переменные добавлены в правильный сервис
2. Перезапустите сервис после изменения переменных
3. Проверьте синтаксис (нет пробелов вокруг `=`)

---

**Готово! Три сервиса развернуты на Railway 🚂**
