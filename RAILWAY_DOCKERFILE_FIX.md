# Исправление ошибки "couldn't locate the dockerfile"

## Проблема
Railway ищет Dockerfile в корне проекта, но мы переместили их в папки сервисов:
- `telegram/Dockerfile`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `yadisk/Dockerfile`

## Решение

### Вариант 1: Настройка через Railway Dashboard (Рекомендуется)

Для каждого сервиса в Railway Dashboard:

1. Откройте сервис → **Settings** → **Build**
2. В поле **Dockerfile Path** укажите:
   - **Telegram Bot**: `telegram/Dockerfile`
   - **Backend**: `backend/Dockerfile`
   - **Frontend**: `frontend/Dockerfile`
   - **Yadisk Indexer**: `yadisk/Dockerfile`
3. Сохраните изменения
4. Запустите новый деплой

### Вариант 2: Использование Railway CLI

Если используете Railway CLI, конфигурации уже созданы в `.railway/`:

```bash
# Для каждого сервиса
railway service --service telegram-bot
railway up  # Использует .railway/telegram-bot.toml

railway service --service backend
railway up  # Использует .railway/backend.toml

railway service --service frontend
railway up  # Использует .railway/frontend.toml

railway service --service yadisk-indexer
railway up  # Использует .railway/yadisk-indexer.toml
```

### Вариант 3: Временное решение (если ничего не помогает)

Создайте симлинки в корне проекта (только для локальной разработки):

```bash
ln -s telegram/Dockerfile Dockerfile.telegram
ln -s backend/Dockerfile Dockerfile.backend
ln -s frontend/Dockerfile Dockerfile.frontend
ln -s yadisk/Dockerfile Dockerfile.yadisk
```

Но лучше использовать Вариант 1 - настройку через Dashboard.

## Проверка

После настройки проверьте:
1. Railway Dashboard → Сервис → Settings → Build
2. Должно быть указано: `telegram/Dockerfile` (или соответствующий путь)
3. При следующем деплое ошибка должна исчезнуть
