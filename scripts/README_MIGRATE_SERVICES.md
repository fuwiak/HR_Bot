# Миграция услуг в RAG коллекцию

## Описание

Скрипт `migrate_services_to_rag.py` загружает услуги исполнителя в RAG коллекцию `hr2137_bot_knowledge_base` для точного поиска через Telegram бота.

## Формат данных

Каждая услуга состоит из 2 строк:
1. **Название услуги** (первая строка)
2. **Цена** (вторая строка, начинается с "от X рублей")

Пример:
```
Автоматизация и настройка HR бизнес - процессов / постановка работы HR-функции с "0"
от 80 000 рублей
```

## Использование

### Автоматически при деплое (рекомендуется)

Миграция автоматически выполняется при старте Backend контейнера, если установлена переменная:

```bash
RUN_SERVICES_MIGRATION=true
```

**Настройка на Railway:**
1. Railway Dashboard → HR_Bot → Variables
2. Добавьте: `RUN_SERVICES_MIGRATION=true`
3. Перезапустите сервис

Подробнее: см. `docs/SERVICES_MIGRATION_AUTO.md`

### Локально

```bash
# Из корневой директории проекта
python3 scripts/migrate_services_to_rag.py
```

### На Railway (вручную)

```bash
# Через Railway Shell (рекомендуется)
railway shell --service HR_Bot
python3 scripts/migrate_services_to_rag.py

# Или через Railway CLI
QDRANT_HOST="https://qdrant-production-bf97.up.railway.app" \
railway run --service HR_Bot python3 scripts/migrate_services_to_rag.py
```

## Требования

1. **Qdrant** должен быть доступен и настроен
   - Переменные окружения: `QDRANT_HOST`, `QDRANT_PORT`
   - Или через конфиг: `config/qdrant.yaml`

2. **API ключ для эмбеддингов**
   - `OPENROUTER_API_KEY` или `OPENAI_API_KEY`

## Что делает скрипт

1. ✅ Парсит текст с услугами (каждая услуга - 2 строки)
2. ✅ Извлекает название и цену для каждой услуги
3. ✅ Генерирует эмбеддинги для каждой услуги
4. ✅ Загружает услуги в Qdrant коллекцию `hr2137_bot_knowledge_base`
5. ✅ Структурирует данные для точного поиска через RAG

## Структура данных в Qdrant

Каждая услуга сохраняется с следующими полями:

```python
{
    "title": "Название услуги",
    "price": 80000,  # Число
    "price_str": "от 80 000 рублей",  # Строка
    "text": "Полный текст для поиска",
    "source_type": "service",  # Маркер для фильтрации
    "category": "услуги_исполнителя",
    "service_id": "уникальный_id",
    "indexed_at": "2026-01-08T23:00:00"
}
```

## Проверка результатов

После миграции услуги можно найти через функцию `search_service()` в `services/rag/qdrant_helper.py`:

```python
from services.rag.qdrant_helper import search_service

# Поиск услуг
results = search_service("автоматизация HR", limit=5)
for service in results:
    print(f"{service['title']} - {service['price_str']}")
```

## Логи

Скрипт выводит подробные логи:
- ✅ Количество найденных услуг
- ✅ Прогресс обработки каждой услуги
- ✅ Результаты загрузки в Qdrant
- ⚠️ Предупреждения о проблемах
- ❌ Ошибки с подробным traceback

## Troubleshooting

### Ошибка: "Qdrant клиент не доступен"
- Проверьте переменные `QDRANT_HOST` и `QDRANT_PORT`
- Убедитесь, что Qdrant сервис запущен

### Ошибка: "API ключ для эмбеддингов не установлен"
- Установите `OPENROUTER_API_KEY` или `OPENAI_API_KEY`

### Ошибка: "Не удалось сгенерировать эмбеддинг"
- Проверьте доступность API (OpenRouter/OpenAI)
- Проверьте баланс API ключа
