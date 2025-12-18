# 🚂 Деплой трех сервисов на Railway

Полная инструкция по развертыванию Telegram Bot, Backend и Frontend как отдельных сервисов.

## 📦 Структура сервисов

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

### Шаг 1: Подготовка репозитория

```bash
git add .
git commit -m "Ready for multi-service Railway deployment"
git push origin main
```

### Шаг 2: Создание проекта на Railway

1. Откройте https://railway.app
2. **New Project** → **Empty Project**
3. Назовите: `HR2137-Bot`

### Шаг 3: Создание Telegram Bot сервиса

1. **"+ New"** → **"GitHub Repo"**
2. Выберите `HR_Bot`
3. **Settings** → **Build**:
   - **Dockerfile Path**: `Dockerfile.telegram`
4. **Settings** → **Networking**:
   - **Generate Domain** → скопируйте URL
5. **Variables** → добавьте:
   ```bash
   TELEGRAM_TOKEN=your_token
   OPENROUTER_API_KEY=your_key
   USE_WEBHOOK=true
   PORT=8080
   WEBHOOK_URL=https://your-telegram-bot-url.up.railway.app
   ```

### Шаг 4: Создание Backend сервиса

1. В том же проекте **"+ New"** → **"GitHub Repo"**
2. Выберите `HR_Bot`
3. **Settings** → **Build**:
   - **Dockerfile Path**: `Dockerfile.backend`
4. **Settings** → **Networking**:
   - **Generate Domain** → скопируйте URL (например: `backend-production.up.railway.app`)
5. **Variables** → добавьте:
   ```bash
   WEB_INTERFACE_PORT=8081
   PORT=8081
   SECRET_KEY=your-random-secret-key
   ```

### Шаг 5: Создание Frontend сервиса

1. В том же проекте **"+ New"** → **"GitHub Repo"**
2. Выберите `HR_Bot`
3. **Settings** → **Build**:
   - **Dockerfile Path**: `Dockerfile.frontend`
4. **Settings** → **Networking**:
   - **Generate Domain** → скопируйте URL
5. **Variables** → добавьте:
   ```bash
   PORT=3000
   NODE_ENV=production
   NEXT_PUBLIC_API_URL=https://backend-production.up.railway.app
   BACKEND_URL=https://backend-production.up.railway.app
   ```
   **Важно**: Замените `backend-production.up.railway.app` на реальный URL вашего Backend сервиса!

### Шаг 6: Общие переменные (Project Variables)

В **Project Settings** → **Variables** добавьте переменные, доступные всем сервисам:

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

## ✅ Проверка работы

### 1. Telegram Bot

```bash
# Проверьте логи
railway logs --service telegram-bot

# Должно быть:
# ✅ Webhook установлен: https://...
# ✅ Бот запущен с webhook
# ✅ Фоновые задачи мониторинга запущены

# Отправьте /start боту
```

### 2. Backend API

```bash
# Откройте в браузере
https://backend-production.up.railway.app/health

# Должен вернуть: {"status": "ok"}

# Проверьте логин
https://backend-production.up.railway.app/login
# Логин: admin, Пароль: admin
```

### 3. Frontend

```bash
# Откройте в браузере
https://frontend-production.up.railway.app

# Должна открыться главная страница Next.js
# API запросы должны проксироваться на Backend
```

## 🔄 Обновление кода

При push в репозиторий Railway автоматически пересоберет все сервисы.

Или вручную через CLI:
```bash
railway up --service telegram-bot
railway up --service backend
railway up --service frontend
```

## 📊 Мониторинг

### Просмотр логов всех сервисов:

```bash
# Все сервисы
railway logs

# Конкретный сервис
railway logs --service telegram-bot
railway logs --service backend
railway logs --service frontend
```

### Через Dashboard:

Railway Dashboard → Ваш проект → Выберите сервис → **Logs**

## 🐛 Troubleshooting

### Проблема: Railway не находит Dockerfile.telegram

**Решение**:
1. Убедитесь что файл существует в репозитории
2. В настройках сервиса → Build → Dockerfile Path укажите: `Dockerfile.telegram`
3. Или переименуйте временно в `Dockerfile` для этого сервиса

### Проблема: Frontend не может подключиться к Backend

**Решение**:
1. Проверьте `NEXT_PUBLIC_API_URL` в переменных Frontend
2. Убедитесь что URL правильный (скопируйте из Backend сервиса)
3. Проверьте что Backend сервис запущен
4. Проверьте логи Backend на ошибки

### Проблема: Telegram Bot не получает обновления

**Решение**:
1. Проверьте `WEBHOOK_URL` в переменных Telegram Bot
2. Проверьте логи: должно быть `✅ Webhook установлен`
3. Убедитесь что домен Telegram Bot сервиса правильный

### Проблема: Сборка Frontend падает

**Решение**:
1. Проверьте что `next.config.js` использует `output: 'standalone'`
2. Убедитесь что все зависимости в `package.json`
3. Проверьте логи сборки в Railway

## 💡 Советы

1. **Используйте Project Variables** для общих переменных (QDRANT, API ключи)
2. **Используйте Service Variables** для специфичных (порты, URL)
3. **Копируйте URL сервисов** сразу после создания для настройки связей
4. **Мониторьте логи** после каждого деплоя

## 📝 Чек-лист

- [ ] Проект создан на Railway
- [ ] Telegram Bot сервис создан и настроен
- [ ] Backend сервис создан и настроен
- [ ] Frontend сервис создан и настроен
- [ ] Все URL сервисов скопированы
- [ ] `NEXT_PUBLIC_API_URL` указывает на Backend URL
- [ ] `WEBHOOK_URL` указывает на Telegram Bot URL
- [ ] Все обязательные переменные добавлены
- [ ] Все сервисы успешно собраны
- [ ] Telegram Bot отвечает на команды
- [ ] Backend API доступен
- [ ] Frontend открывается и работает

---

**Готово! Три сервиса развернуты на Railway 🚂**
