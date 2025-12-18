# 🚂 Настройка Dockerfile Path на Railway

## ✅ Автоматическая настройка

В репозитории созданы конфигурационные файлы для каждого сервиса:

- `.railway/telegram-bot.toml` - для Telegram Bot (Dockerfile.telegram)
- `.railway/backend.toml` - для Backend (Dockerfile.backend)
- `.railway/frontend.toml` - для Frontend (Dockerfile.frontend)

## 🚀 Способ 1: Через Railway Dashboard (Самый простой)

### Для каждого сервиса:

1. Создайте сервис в Railway Dashboard
2. **Settings** → **Build** → **Dockerfile Path**
3. Укажите:
   - **Telegram Bot**: `Dockerfile.telegram`
   - **Backend**: `Dockerfile.backend`
   - **Frontend**: `Dockerfile.frontend`

## 🚀 Способ 2: Через Railway CLI

### Использование конфигурационных файлов:

```bash
# Установите Railway CLI
npm i -g @railway/cli

# Войдите в Railway
railway login

# Создайте сервисы
railway service create telegram-bot
railway service create backend
railway service create frontend

# Для каждого сервиса переключитесь и Railway автоматически использует .railway/*.toml
railway service --service telegram-bot
railway up  # Использует .railway/telegram-bot.toml

railway service --service backend
railway up  # Использует .railway/backend.toml

railway service --service frontend
railway up  # Использует .railway/frontend.toml
```

### Или используйте скрипт:

```bash
chmod +x setup_railway_services.sh
./setup_railway_services.sh
```

## 📝 Структура конфигурации

Каждый `.railway/*.toml` файл содержит:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile.telegram"  # или .backend, .frontend

[deploy]
numReplicas = 1
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

## ✅ Проверка

После настройки:

1. Railway Dashboard → Сервис → Settings → Build
2. Проверьте, что **Dockerfile Path** указан правильно
3. При следующем деплое Railway использует правильный Dockerfile

## 🔄 Обновление

Если нужно изменить Dockerfile Path:

1. **Через Dashboard**: Settings → Build → Dockerfile Path
2. **Через файлы**: Обновите соответствующий `.railway/*.toml` файл
3. **Через CLI**: `railway variables set DOCKERFILE_PATH=...` (если поддерживается)

---

**Готово! Dockerfile Path настроен автоматически 🚂**
