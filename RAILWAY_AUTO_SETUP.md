# 🔧 Автоматическая настройка Dockerfile Path на Railway

Railway не поддерживает несколько сервисов с разными Dockerfile в одном `railway.toml`, но можно настроить автоматически.

## 🚀 Способ 1: Через Railway Dashboard (Рекомендуется)

### Для каждого сервиса:

1. **Создайте сервис** в Railway Dashboard
2. **Settings** → **Build** → **Dockerfile Path**
3. Укажите:
   - **Telegram Bot**: `Dockerfile.telegram`
   - **Backend**: `Dockerfile.backend`
   - **Frontend**: `Dockerfile.frontend`

## 🚀 Способ 2: Через Railway CLI

### Автоматическая настройка:

```bash
# Установите Railway CLI (если еще не установлен)
npm i -g @railway/cli

# Войдите в Railway
railway login

# Запустите скрипт автоматической настройки
chmod +x setup_railway_services.sh
./setup_railway_services.sh
```

### Или вручную через CLI:

```bash
# Создайте сервисы
railway service create telegram-bot
railway service create backend
railway service create frontend

# Настройте Dockerfile Path для каждого сервиса
railway service --service telegram-bot
railway variables set DOCKERFILE_PATH=Dockerfile.telegram

railway service --service backend
railway variables set DOCKERFILE_PATH=Dockerfile.backend

railway service --service frontend
railway variables set DOCKERFILE_PATH=Dockerfile.frontend
```

**Примечание**: Railway CLI может не поддерживать `DOCKERFILE_PATH` через переменные. В этом случае настройте в Dashboard.

## 🚀 Способ 3: Через .railway/ директорию

Созданы конфигурационные файлы в `.railway/`:

- `.railway/telegram-bot.toml` - для Telegram Bot
- `.railway/backend.toml` - для Backend
- `.railway/frontend.toml` - для Frontend

Эти файлы используются Railway CLI при работе с конкретным сервисом:

```bash
# Переключитесь на сервис
railway service --service telegram-bot

# Railway автоматически использует .railway/telegram-bot.toml
railway up
```

## 📝 Структура конфигурации

### .railway/telegram-bot.toml:
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile.telegram"
```

### .railway/backend.toml:
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile.backend"
```

### .railway/frontend.toml:
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile.frontend"
```

## ✅ Проверка

После настройки проверьте:

1. **Railway Dashboard** → Выберите сервис → **Settings** → **Build**
2. Должно быть указано правильное значение в **Dockerfile Path**
3. При следующем деплое Railway использует правильный Dockerfile

## 🔄 Обновление

Если нужно изменить Dockerfile Path:

1. **Через Dashboard**: Settings → Build → Dockerfile Path
2. **Через CLI**: Обновите соответствующий `.railway/*.toml` файл
3. **Через переменные**: `railway variables set DOCKERFILE_PATH=...` (если поддерживается)

---

**Готово! Dockerfile Path настроен автоматически 🚂**
