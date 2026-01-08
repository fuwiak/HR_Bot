# Декомпозиция telegram_bot/app.py

## Структура проекта

Файл `app.py` (6489 строк) был декомпозирован на следующие модули:

```
telegram_bot/
├── app.py                    # Главный файл (упрощенный)
├── app_old.py               # Резервная копия оригинального файла
├── config.py                 # Конфигурация и промпты
├── storage/                  # Модули для работы с хранилищем
│   ├── __init__.py
│   ├── memory.py            # Память пользователей (история чата)
│   ├── email_subscribers.py # Подписчики на email уведомления
│   ├── user_data.py         # Данные пользователей (телефоны, booking data)
│   └── user_records.py      # Записи пользователей
├── integrations/             # Интеграции с внешними сервисами
│   ├── __init__.py
│   ├── google_sheets.py     # Интеграция с Google Sheets
│   ├── qdrant.py            # Интеграция с Qdrant
│   └── openrouter.py        # Интеграция с OpenRouter API
├── nlp/                      # NLP обработка
│   ├── __init__.py
│   ├── intent_classifier.py # Классификатор намерений
│   ├── booking_parser.py   # Парсер запросов на запись
│   └── text_utils.py        # Утилиты для работы с текстом
├── services/                 # Бизнес-логика
│   ├── __init__.py
│   └── booking_service.py   # Сервис для работы с записями
└── handlers/                 # Обработчики (TODO: перенести из app_old.py)
    ├── __init__.py
    ├── commands/            # Обработчики команд
    ├── menu/                # Обработчики меню
    └── messages/            # Обработчики сообщений
```

## Что было сделано

### ✅ Завершено:

1. **config.py** - Конфигурация, переменные окружения, промпты
2. **storage/** - Модули для работы с хранилищем:
   - `memory.py` - Память пользователей (Redis -> PostgreSQL -> RAM)
   - `email_subscribers.py` - Управление подписчиками
   - `user_data.py` - Данные пользователей
   - `user_records.py` - Записи пользователей
3. **integrations/** - Интеграции:
   - `google_sheets.py` - Работа с Google Sheets
   - `qdrant.py` - Векторная база данных
   - `openrouter.py` - LLM API
4. **nlp/** - NLP модули:
   - `intent_classifier.py` - Классификация намерений
   - `booking_parser.py` - Парсинг запросов на запись
   - `text_utils.py` - Утилиты для текста
5. **services/** - Бизнес-логика:
   - `booking_service.py` - Сервис для работы с записями

### ⏳ В процессе:

6. **handlers/** - Обработчики (временно импортируются из `app_old.py`):
   - `commands/` - Обработчики команд (/start, /menu, /rag_search и т.д.)
   - `menu/` - Обработчики меню и callback кнопок
   - `messages/` - Обработчики сообщений (reply, booking flow, chat flow)

## Следующие шаги

1. Перенести handlers из `app_old.py` в отдельные модули:
   - `handlers/commands/basic.py` - /start, /menu, /status
   - `handlers/commands/rag.py` - /rag_search, /rag_stats, /rag_docs
   - `handlers/commands/weeek.py` - Все WEEEK команды
   - `handlers/commands/yadisk.py` - Yandex Disk команды
   - `handlers/commands/email.py` - Email команды
   - `handlers/commands/tools.py` - /summary, /demo_proposal и т.д.
   - `handlers/menu/callback_router.py` - Роутер для callback кнопок
   - `handlers/messages/reply_handler.py` - Основная функция reply()
   - `handlers/messages/booking_flow.py` - Логика обработки запросов на запись
   - `handlers/messages/chat_flow.py` - Логика обычного чата с AI
   - `handlers/messages/document_handler.py` - Обработка документов

2. Создать `services/email_service.py` для работы с email

3. Обновить `app.py` для использования новых handlers модулей

## Использование

Текущая версия `app.py` использует новую структуру модулей, но handlers временно импортируются из `app_old.py` для обратной совместимости.

Для полной декомпозиции нужно:
1. Перенести handlers в отдельные модули
2. Обновить импорты в `app.py`
3. Удалить `app_old.py` после проверки работоспособности

## Преимущества декомпозиции

1. **Модульность** - каждый модуль отвечает за свою область
2. **Тестируемость** - легче писать тесты для отдельных модулей
3. **Читаемость** - легче найти нужный код
4. **Масштабируемость** - проще добавлять новые функции
5. **Переиспользование** - модули можно использовать в других частях проекта
