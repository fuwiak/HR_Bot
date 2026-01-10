# 🚀 Настройка Backend API сервиса на Railway

## 📋 Обзор

Для работы Mini App с уведомлениями и синхронизацией с Telegram ботом нужно создать отдельный Backend API сервис на Railway.

## ✅ Шаг 1: Создание нового сервиса на Railway

1. Откройте ваш проект на Railway Dashboard
2. Нажмите **"+ New"** → **"GitHub Repo"**
3. Выберите тот же репозиторий `HR_Bot`
4. Railway начнет сборку (пока не настроен правильно)

## ✅ Шаг 2: Настройка Dockerfile

1. В настройках нового сервиса → **Settings** → **Build**
2. Измените **Dockerfile Path** на: `backend/Dockerfile`
3. Сохраните изменения

## ✅ Шаг 3: Настройка Networking

1. **Settings** → **Networking**
2. Включите **Public Domain** (Railway автоматически создаст HTTPS домен)
3. Скопируйте URL (например: `https://backend-production-xxxx.up.railway.app`)
4. Этот URL будет использоваться как `BACKEND_URL` для Frontend

## ✅ Шаг 4: Настройка переменных окружения

В **Variables** добавьте:

```env
# Порт сервиса
PORT=8081
WEB_INTERFACE_PORT=8081

# База данных (используйте Railway Service Reference)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Или отдельные переменные PostgreSQL
PGHOST=${{Postgres.PGHOST}}
PGPORT=${{Postgres.PGPORT}}
PGDATABASE=${{Postgres.PGDATABASE}}
PGUSER=${{Postgres.PGUSER}}
PGPASSWORD=${{Postgres.PGPASSWORD}}

# Redis (если используется)
REDIS_URL=${{Redis.REDIS_URL}}

# Qdrant (если используется)
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key

# OpenRouter для LLM
OPENROUTER_API_KEY=your_openrouter_key

# Telegram (для отправки уведомлений из API)
TELEGRAM_TOKEN=your_telegram_token
TELEGRAM_ADMIN_IDS=5305427956

# Email (для проверки писем)
YANDEX_EMAIL=your_email
YANDEX_PASSWORD=your_password

# Другие интеграции (опционально)
WEEEEK_TOKEN=your_weeek_token
HRTIME_API_KEY=your_hrtime_key
```

## ✅ Шаг 5: Обновление Frontend сервиса

В **Frontend** сервисе обновите переменные:

```env
NEXT_PUBLIC_API_URL=https://your-backend-service.up.railway.app
BACKEND_URL=https://your-backend-service.up.railway.app
```

**Важно:** Замените `your-backend-service.up.railway.app` на реальный URL из Шага 3.

## ✅ Шаг 6: Проверка работы

1. Дождитесь успешной сборки Backend сервиса
2. Проверьте логи - должны быть строки:
   ```
   ✅ PostgreSQL инициализирован
   🚀 Запуск веб-интерфейса на порту 8081
   ```
3. Откройте в браузере: `https://your-backend-service.up.railway.app/health`
4. Должен вернуться JSON: `{"status": "ok", ...}`

## 🔧 Доступные API endpoints

После настройки будут доступны:

- `GET /notifications?user_id=...` - список уведомлений
- `GET /notifications/unread-count?user_id=...` - количество непрочитанных
- `POST /notifications/mark-read` - отметить как прочитанное
- `GET /email/unread-count?user_id=...` - количество непрочитанных писем
- `GET /email/recent?user_id=...` - последние письма
- `POST /chat` - синхронизированный чат с Telegram ботом
- `GET /chat/history?user_id=...` - история чата

## 📝 Структура сервисов на Railway

```
Railway Project: HR2137-Bot
│
├── Service 1: Telegram Bot
│   ├── Dockerfile: telegram_bot/Dockerfile
│   ├── Port: 8080
│   └── URL: telegram-bot-production.up.railway.app
│
├── Service 2: Backend API (НОВЫЙ)
│   ├── Dockerfile: backend/Dockerfile
│   ├── Port: 8081
│   └── URL: backend-production.up.railway.app ← Используется Frontend
│
└── Service 3: Frontend
    ├── Dockerfile: frontend/Dockerfile
    ├── Port: 3000
    └── URL: frontend-production.up.railway.app
    └── NEXT_PUBLIC_API_URL → backend-production.up.railway.app
```

## ⚠️ Важные моменты

1. **Один порт на сервис**: Railway позволяет только один публичный порт на сервис
2. **Service References**: Используйте `${{Postgres.DATABASE_URL}}` для подключения к PostgreSQL
3. **CORS**: Backend API уже настроен на CORS для работы с Frontend
4. **HTTPS**: Railway автоматически предоставляет HTTPS для всех сервисов

## 🐛 Устранение проблем

### Backend не запускается
- Проверьте логи в Railway Dashboard
- Убедитесь, что `DATABASE_URL` установлен
- Проверьте, что `backend/Dockerfile` указан правильно

### Frontend не может подключиться к Backend
- Проверьте `NEXT_PUBLIC_API_URL` в Frontend сервисе
- Убедитесь, что Backend сервис имеет Public Domain
- Проверьте CORS настройки в `backend/web_interface.py`

### Endpoints возвращают 404
- Убедитесь, что endpoints добавлены в `backend/web_interface.py`
- Проверьте, что Frontend proxy правильно настроен в `next.config.js`
