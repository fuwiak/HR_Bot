# 🚂 Деплой нескольких сервисов на Railway

Railway не поддерживает docker-compose.yml, но позволяет создать несколько сервисов в одном проекте. Эта инструкция покажет, как развернуть три отдельных сервиса.

## 📦 Архитектура

```
Railway Project
├── Service 1: Telegram Bot (Dockerfile.telegram) - порт 8080
├── Service 2: Backend API (Dockerfile.backend) - порт 8081
└── Service 3: Frontend (Dockerfile.frontend) - порт 3000
```

## 🚀 Шаг 1: Создание проекта на Railway

1. Перейдите на https://railway.app
2. **New Project** → **Empty Project**
3. Назовите проект (например: `HR2137-Bot`)

## 🔧 Шаг 2: Создание первого сервиса - Telegram Bot

1. В проекте нажмите **"+ New"** → **"GitHub Repo"**
2. Выберите ваш репозиторий `HR_Bot`
3. Railway начнет сборку, но нужно изменить Dockerfile

### Настройка Telegram Bot сервиса:

1. В настройках сервиса → **Settings** → **Build**
2. Измените **Dockerfile Path** на: `Dockerfile.telegram`
3. Или переименуйте `Dockerfile.telegram` в `Dockerfile` в корне (временно)

**Переменные окружения для Telegram Bot:**
```bash
TELEGRAM_TOKEN=your_bot_token
OPENROUTER_API_KEY=your_api_key
USE_WEBHOOK=true
PORT=8080
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key
# ... другие переменные из ENV_VARIABLES.md
```

## 🔧 Шаг 3: Создание второго сервиса - Backend API

1. В том же проекте нажмите **"+ New"** → **"GitHub Repo"**
2. Выберите тот же репозиторий `HR_Bot`
3. В настройках сервиса → **Settings** → **Build**
4. Измените **Dockerfile Path** на: `Dockerfile.backend`

**Переменные окружения для Backend:**
```bash
WEB_INTERFACE_PORT=8081
PORT=8081
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key
OPENROUTER_API_KEY=your_api_key
SECRET_KEY=your_secret_key
# ... другие переменные
```

## 🔧 Шаг 4: Создание третьего сервиса - Frontend

1. В том же проекте нажмите **"+ New"** → **"GitHub Repo"**
2. Выберите тот же репозиторий `HR_Bot`
3. В настройках сервиса → **Settings** → **Build**
4. Измените **Dockerfile Path** на: `Dockerfile.frontend`
5. Измените **Root Directory** на: `/` (корень репозитория)

**Переменные окружения для Frontend:**
```bash
PORT=3000
NEXT_PUBLIC_API_URL=https://your-backend-service.up.railway.app
BACKEND_URL=https://your-backend-service.up.railway.app
NODE_ENV=production
```

**Важно**: `NEXT_PUBLIC_API_URL` должен указывать на публичный URL вашего Backend сервиса.

## 🔗 Шаг 5: Настройка связей между сервисами

### Получение URL сервисов:

1. В Railway Dashboard для каждого сервиса:
   - Перейдите в **Settings** → **Networking**
   - Нажмите **"Generate Domain"** (если еще не создан)
   - Скопируйте домен (например: `telegram-bot-production.up.railway.app`)

### Настройка Frontend для работы с Backend:

В переменных окружения Frontend сервиса установите:
```bash
NEXT_PUBLIC_API_URL=https://your-backend-service.up.railway.app
BACKEND_URL=https://your-backend-service.up.railway.app
```

### Настройка Telegram Bot для webhook:

В переменных окружения Telegram Bot сервиса:
```bash
WEBHOOK_URL=https://your-telegram-bot-service.up.railway.app
# Или используйте автоматический домен
RAILWAY_PUBLIC_DOMAIN=your-telegram-bot-service.up.railway.app
```

## 📋 Альтернативный способ: Через Railway CLI

### Создание сервисов через CLI:

```bash
# Установка CLI
npm i -g @railway/cli

# Вход
railway login

# Создание проекта
railway init

# Создание первого сервиса (Telegram Bot)
railway service create telegram-bot
railway service --service telegram-bot
railway variables set DOCKERFILE_PATH=Dockerfile.telegram
railway variables set TELEGRAM_TOKEN=your_token
railway variables set OPENROUTER_API_KEY=your_key
railway up

# Создание второго сервиса (Backend)
railway service create backend
railway service --service backend
railway variables set DOCKERFILE_PATH=Dockerfile.backend
railway variables set WEB_INTERFACE_PORT=8081
railway up

# Создание третьего сервиса (Frontend)
railway service create frontend
railway service --service frontend
railway variables set DOCKERFILE_PATH=Dockerfile.frontend
railway variables set NEXT_PUBLIC_API_URL=https://your-backend-url
railway up
```

## 🔄 Обновление railway.toml для нескольких сервисов

Создайте `railway.toml` в корне проекта:

```toml
[build]
builder = "DOCKERFILE"

# Для каждого сервиса Railway автоматически определит Dockerfile
# если указать в настройках сервиса

[deploy]
numReplicas = 1
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

**Примечание**: Railway использует настройки каждого сервиса отдельно. Dockerfile path указывается в настройках каждого сервиса.

## 📝 Структура файлов

```
HR_Bot/
├── Dockerfile.telegram    # Для Telegram Bot сервиса
├── Dockerfile.backend     # Для Backend API сервиса
├── Dockerfile.frontend    # Для Frontend сервиса
├── app.py                 # Telegram Bot
├── web_interface.py       # Backend API
├── dashboard.py           # RAG Dashboard
├── frontend/              # Next.js приложение
│   ├── package.json
│   ├── next.config.js
│   └── ...
└── railway.toml           # Общая конфигурация
```

## 🔧 Настройка переменных окружения

### Общие переменные (для всех сервисов):

Добавьте в **Project Variables** (доступны всем сервисам):
```bash
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key
OPENROUTER_API_KEY=your_api_key
```

### Специфичные переменные (для каждого сервиса):

**Telegram Bot:**
- `TELEGRAM_TOKEN`
- `USE_WEBHOOK=true`
- `PORT=8080`

**Backend:**
- `WEB_INTERFACE_PORT=8081`
- `PORT=8081`
- `SECRET_KEY`

**Frontend:**
- `PORT=3000`
- `NEXT_PUBLIC_API_URL` (URL Backend сервиса)
- `NODE_ENV=production`

## 🌐 Настройка доменов

Для каждого сервиса Railway предоставляет отдельный домен:

1. **Telegram Bot**: `telegram-bot-production.up.railway.app`
2. **Backend**: `backend-production.up.railway.app`
3. **Frontend**: `frontend-production.up.railway.app`

Или можно использовать один кастомный домен с путями (требует настройки прокси).

## ✅ Проверка работы

### Telegram Bot:
1. Проверьте логи: должно быть `✅ Webhook установлен`
2. Отправьте `/start` боту

### Backend:
1. Откройте `https://backend-production.up.railway.app/health`
2. Должен вернуться JSON с `{"status": "ok"}`

### Frontend:
1. Откройте `https://frontend-production.up.railway.app`
2. Должна открыться главная страница
3. API запросы должны проксироваться на Backend

## 🐛 Troubleshooting

### Проблема: Frontend не может подключиться к Backend

**Решение:**
1. Убедитесь что `NEXT_PUBLIC_API_URL` указывает на правильный URL Backend
2. Проверьте что Backend сервис запущен и доступен
3. Проверьте CORS настройки в Backend (если нужно)

### Проблема: Telegram Bot не получает обновления

**Решение:**
1. Проверьте `WEBHOOK_URL` в переменных Telegram Bot сервиса
2. Проверьте логи: должно быть `✅ Webhook установлен`
3. Убедитесь что порт 8080 открыт

### Проблема: Сборка Frontend падает

**Решение:**
1. Проверьте что `next.config.js` использует `output: 'standalone'`
2. Убедитесь что все зависимости в `package.json`
3. Проверьте логи сборки в Railway

## 📊 Мониторинг

Каждый сервис имеет свои логи:
- Railway Dashboard → Ваш проект → Выберите сервис → Logs

Или через CLI:
```bash
railway logs --service telegram-bot
railway logs --service backend
railway logs --service frontend
```

## 💰 Стоимость

Railway взимает плату за каждый активный сервис. Три сервиса = три отдельных контейнера.

Для экономии можно:
- Объединить Backend и Frontend в один сервис (через nginx)
- Или использовать один сервис с несколькими процессами (через start.sh)

Но для разделения и масштабирования лучше использовать отдельные сервисы.

---

**Готово! Теперь у вас три отдельных сервиса на Railway 🚂**

