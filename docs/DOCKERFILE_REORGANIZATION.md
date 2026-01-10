# 🔧 Реорганизация Dockerfile в проекте

## ✅ Изменения

Все Dockerfile были перемещены в соответствующие папки сервисов:

### Структура до:
```
/
├── Dockerfile              # ❌ Удален
├── Dockerfile.telegram      # ❌ Удален
├── Dockerfile.backend       # ❌ Удален
├── Dockerfile.frontend      # ❌ Удален
├── Dockerfile.yadisk        # ❌ Удален
```

### Структура после:
```
/
├── telegram_bot/
│   └── Dockerfile          # ✅ Для Telegram Bot
├── backend/
│   └── Dockerfile          # ✅ Для Backend API
├── frontend/
│   └── Dockerfile          # ✅ Для Mini App
└── yadisk/
    └── Dockerfile          # ✅ Для Yandex Disk Indexer
```

## 📋 Обновленная конфигурация

Все файлы `.railway/*.toml` обновлены:

```toml
# .railway/telegram-bot.toml
dockerfilePath = "telegram_bot/Dockerfile"

# .railway/backend.toml
dockerfilePath = "backend/Dockerfile"

# .railway/frontend.toml
dockerfilePath = "frontend/Dockerfile"

# .railway/yadisk-indexer.toml
dockerfilePath = "yadisk/Dockerfile"
```

## ⚠️ Важно для frontend/Dockerfile

`frontend/Dockerfile` использует пути с префиксом `frontend/`, так как Railway строит из корня проекта:

```dockerfile
COPY frontend/package.json frontend/package-lock.json* ./
COPY frontend/ .
```

Это правильно, потому что Railway использует корень проекта как build context.

## 🎯 Преимущества

1. **Организация:** Каждый Dockerfile находится рядом с кодом сервиса
2. **Чистота:** Нет Dockerfile в корне проекта
3. **Понятность:** Легко найти Dockerfile для конкретного сервиса
4. **Масштабируемость:** Легко добавлять новые сервисы

## 📝 Проверка

После изменений:

1. **В корне проекта:**
   ```bash
   ls Dockerfile*  # Должно быть пусто
   ```

2. **В папках сервисов:**
   ```bash
   ls telegram_bot/Dockerfile  # ✅ Должен существовать
   ls backend/Dockerfile        # ✅ Должен существовать
   ls frontend/Dockerfile       # ✅ Должен существовать
   ls yadisk/Dockerfile         # ✅ Должен существовать
   ```

3. **В .railway/*.toml:**
   ```bash
   cat .railway/*.toml | grep dockerfilePath
   # Должно показывать пути к папкам: telegram_bot/Dockerfile, backend/Dockerfile, etc.
   ```
