# 📋 Сводка: Деплой трех сервисов на Railway

## ✅ Что создано

### Отдельные Dockerfile:

1. **Dockerfile.telegram** - для Telegram Bot сервиса
   - Запускает только `app.py`
   - Порт: 8080
   - Команда: `python app.py`

2. **Dockerfile.backend** - для Backend API сервиса
   - Запускает только `web_interface.py`
   - Порт: 8081
   - Команда: `python web_interface.py`

3. **Dockerfile.frontend** - для Frontend сервиса
   - Собирает Next.js приложение
   - Порт: 3000
   - Команда: `node server.js` (standalone mode)

### Обновленные конфигурации:

- ✅ **frontend/next.config.js** - использует `BACKEND_URL` или `NEXT_PUBLIC_API_URL`
- ✅ **frontend/lib/api.ts** - использует `NEXT_PUBLIC_API_URL` для подключения к Backend

### Документация:

- ✅ **RAILWAY_DEPLOY_MULTI.md** - полная инструкция
- ✅ **RAILWAY_SETUP_MULTI.md** - пошаговая настройка
- ✅ **RAILWAY_QUICK_MULTI.md** - быстрый старт (15 минут)
- ✅ **DEPLOY_MULTI_SERVICES.md** - краткая инструкция
- ✅ **railway.services.toml** - описание структуры сервисов

## 🚀 Как задеплоить

### Вариант 1: Через Railway Dashboard (рекомендуется)

1. Создайте **Empty Project** на Railway
2. Создайте 3 сервиса из одного репозитория:
   - Telegram Bot: Dockerfile Path = `Dockerfile.telegram`
   - Backend: Dockerfile Path = `Dockerfile.backend`
   - Frontend: Dockerfile Path = `Dockerfile.frontend`
3. Настройте переменные окружения для каждого сервиса
4. Укажите `NEXT_PUBLIC_API_URL` в Frontend на URL Backend сервиса

### Вариант 2: Через Railway CLI

```bash
railway login
railway init

# Telegram Bot
railway service create telegram-bot
railway variables set DOCKERFILE_PATH=Dockerfile.telegram --service telegram-bot
railway up --service telegram-bot

# Backend
railway service create backend
railway variables set DOCKERFILE_PATH=Dockerfile.backend --service backend
railway up --service backend

# Frontend
railway service create frontend
railway variables set DOCKERFILE_PATH=Dockerfile.frontend --service frontend
railway variables set NEXT_PUBLIC_API_URL=https://backend-url --service frontend
railway up --service frontend
```

## 📝 Ключевые переменные

### Telegram Bot:
- `TELEGRAM_TOKEN`
- `USE_WEBHOOK=true`
- `PORT=8080`

### Backend:
- `WEB_INTERFACE_PORT=8081`
- `PORT=8081`
- `SECRET_KEY`

### Frontend:
- `PORT=3000`
- `NEXT_PUBLIC_API_URL=https://backend-service.up.railway.app` ⚠️ **ВАЖНО!**
- `BACKEND_URL=https://backend-service.up.railway.app`

## 🔗 Связи между сервисами

- **Frontend → Backend**: через `NEXT_PUBLIC_API_URL`
- **Telegram Bot**: независимый сервис
- **Все сервисы**: используют общие Project Variables (QDRANT, API ключи)

## ✅ Проверка

После деплоя проверьте:

1. Telegram Bot: `/start` команда работает
2. Backend: `https://backend-url/health` возвращает `{"status": "ok"}`
3. Frontend: `https://frontend-url` открывается и API запросы работают

---

**Готово! Три сервиса готовы к деплою на Railway 🚂**
