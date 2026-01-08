# Проверка таблиц PostgreSQL на Railway

## После деплоя

После успешного деплоя на Railway, миграции Alembic автоматически выполнятся при старте контейнера.

## Созданные таблицы

После выполнения миграции `001_initial_telegram_tables` будут созданы следующие таблицы:

1. **telegram_users** - Пользователи Telegram
   - `user_id` (PRIMARY KEY)
   - `username`, `first_name`, `last_name`, `phone`
   - `language_code`, `is_bot`
   - `created_at`, `updated_at`

2. **telegram_messages** - Сообщения Telegram (входящие и исходящие)
   - `id` (PRIMARY KEY, AUTO_INCREMENT)
   - `user_id` (FOREIGN KEY -> telegram_users)
   - `message_id`, `chat_id`
   - `role` (user/assistant)
   - `content` (текст сообщения)
   - `message_type`, `platform`
   - `metadata_json` (JSON)
   - `processed_by_llm`, `indexed_in_qdrant` (флаги)
   - `created_at`, `updated_at`

3. **conversation_contexts** - Контекст разговоров
   - `id` (PRIMARY KEY)
   - `user_id` (FOREIGN KEY -> telegram_users)
   - `chat_id`
   - `context_json` (JSON массив сообщений)
   - `context_size`, `last_message_id`
   - `created_at`, `updated_at`

## Как проверить таблицы в Railway

### Вариант 1: Через Railway Dashboard

1. Откройте ваш проект на Railway
2. Перейдите в PostgreSQL сервис
3. Откройте вкладку **"Data"** или **"Query"**
4. Выполните SQL запрос:

```sql
-- Список всех таблиц
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';

-- Проверка таблицы telegram_users
SELECT * FROM telegram_users LIMIT 10;

-- Проверка таблицы telegram_messages
SELECT * FROM telegram_messages LIMIT 10;

-- Проверка таблицы conversation_contexts
SELECT * FROM conversation_contexts LIMIT 10;
```

### Вариант 2: Через psql (локально)

1. Получите DATABASE_URL из Railway:
   - Railway Dashboard → PostgreSQL → Variables → DATABASE_URL

2. Подключитесь к базе:

```bash
psql $DATABASE_URL
```

3. Выполните запросы:

```sql
\dt  -- Список таблиц
\d telegram_users  -- Структура таблицы
\d telegram_messages
\d conversation_contexts

SELECT COUNT(*) FROM telegram_users;
SELECT COUNT(*) FROM telegram_messages;
```

### Вариант 3: Через Railway CLI

```bash
railway connect postgres
```

Затем выполните SQL запросы как в варианте 2.

## Проверка миграций Alembic

Чтобы проверить, что миграции выполнены:

```sql
SELECT * FROM alembic_version;
```

Должна быть запись с `version_num = '001_initial'`.

## Мониторинг данных

После того как бот начнет работать, вы можете отслеживать:

```sql
-- Количество пользователей
SELECT COUNT(*) as total_users FROM telegram_users;

-- Количество сообщений по ролям
SELECT role, COUNT(*) as count 
FROM telegram_messages 
GROUP BY role;

-- Последние сообщения
SELECT user_id, role, content, created_at 
FROM telegram_messages 
ORDER BY created_at DESC 
LIMIT 20;

-- Сообщения, индексированные в Qdrant
SELECT COUNT(*) as indexed_count 
FROM telegram_messages 
WHERE indexed_in_qdrant = true;
```

## Индексы

Таблицы имеют следующие индексы для быстрого поиска:

- `telegram_users`: `user_id`, `username`
- `telegram_messages`: 
  - `user_id`, `message_id`, `chat_id`
  - `role`, `created_at`
  - `processed_by_llm`, `indexed_in_qdrant`
  - Композитные: `(user_id, created_at)`, `(role, created_at)`, `(indexed_in_qdrant, created_at)`

## Устранение проблем

Если таблицы не созданы:

1. Проверьте логи Railway:
   ```bash
   railway logs
   ```

2. Ищите строки:
   - `🔄 Запуск миграций Alembic...`
   - `✅ Миграции выполнены успешно` или ошибки

3. Если миграции не выполнились, запустите вручную:
   ```bash
   railway run alembic upgrade head
   ```

4. Проверьте переменные окружения:
   - `DATABASE_URL` должен быть установлен
   - Или `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`
