# 📋 Переменные окружения для Mini App в Railway

## 🎯 Обязательные переменные для Mini App сервиса

### В сервисе **Mini App** (Frontend):

```env
# Порт приложения (обязательно)
PORT=3000

# Режим работы Next.js
NODE_ENV=production

# (Опционально) URL Backend API, если Mini App делает запросы к API
NEXT_PUBLIC_API_URL=https://your-backend-service.up.railway.app
BACKEND_URL=https://your-backend-service.up.railway.app
```

### В сервисе **Telegram Bot**:

```env
# URL Mini App (обязательно для отображения кнопки)
MINI_APP_URL=https://mini-app-production-3766.up.railway.app

# Или используйте FRONTEND_URL (бот автоматически добавит /miniapp)
FRONTEND_URL=https://mini-app-production-3766.up.railway.app
```

## ❌ Переменные, которые НЕ нужны в Mini App

**Mini App НЕ нужны эти переменные:**
- ❌ `DATABASE_URL` - только для Backend/Telegram Bot
- ❌ `TELEGRAM_TOKEN` - только для Telegram Bot
- ❌ `QDRANT_HOST` / `QDRANT_URL` - только для Backend
- ❌ `OPENROUTER_API_KEY` - только для Backend/Telegram Bot
- ❌ `REDIS_URL` - только для Backend
- ❌ `USE_WEBHOOK` - только для Telegram Bot
- ❌ `PORT=8080` или `PORT=8081` - Mini App использует `PORT=3000`

## ✅ Минимальная конфигурация Mini App

Для работы Mini App достаточно:

```env
PORT=3000
NODE_ENV=production
```

Все остальное - опционально.

## 🔧 Настройка в Railway Dashboard

### Шаг 1: Откройте Mini App сервис
1. Railway Dashboard → **Mini App** (или **Frontend**)
2. **Settings** → **Variables**

### Шаг 2: Добавьте переменные
```
PORT=3000
NODE_ENV=production
```

### Шаг 3: (Опционально) Если Mini App использует Backend API
```
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
BACKEND_URL=https://your-backend.up.railway.app
```

### Шаг 4: Настройте Telegram Bot сервис
1. Railway Dashboard → **Telegram Bot** (или **HR_Bot**)
2. **Settings** → **Variables**
3. Добавьте:
```
MINI_APP_URL=https://mini-app-production-3766.up.railway.app
```

## 📝 Пример полной конфигурации

### Mini App сервис:
```env
PORT=3000
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://backend-production-xxxx.up.railway.app
BACKEND_URL=https://backend-production-xxxx.up.railway.app
```

### Telegram Bot сервис:
```env
TELEGRAM_TOKEN=your_bot_token
MINI_APP_URL=https://mini-app-production-3766.up.railway.app
OPENROUTER_API_KEY=your_key
DATABASE_URL=${{Postgres.DATABASE_URL}}
# ... другие переменные для бота
```

## 🔍 Проверка конфигурации

После настройки проверьте:

1. **Mini App доступен:**
   ```bash
   curl https://mini-app-production-3766.up.railway.app/
   ```

2. **Mini App путь работает:**
   ```bash
   curl https://mini-app-production-3766.up.railway.app/miniapp
   ```

3. **В логах Telegram Bot должно быть:**
   ```
   🌐 Mini App URL настроен: https://mini-app-production-3766.up.railway.app
   ```

4. **В боте должна появиться кнопка:**
   - Откройте бота
   - Команда `/start`
   - Должна быть кнопка "🌐 Открыть Mini App"

## ⚠️ Важные замечания

1. **URL должен быть HTTPS** - Mini App требует HTTPS
2. **URL должен быть доступен** - проверьте, что сервис запущен
3. **Не добавляйте `/miniapp` в `MINI_APP_URL`**, если хотите открывать корневой URL
4. **Если используете `FRONTEND_URL`**, бот автоматически добавит `/miniapp`

## 📚 Дополнительная информация

- [Railway Mini App Setup](./RAILWAY_MINIAPP_SETUP.md)
- [Mini App BotFather Setup](./MINIAPP_BOTFATHER_SETUP.md)
- [Mini App Quick Start](./MINIAPP_QUICK_START.md)
