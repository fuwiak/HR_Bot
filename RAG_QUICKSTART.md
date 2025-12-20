# Быстрый старт RAG системы для HR2137 Bot

## Установка зависимостей

```bash
pip install -r requirements.txt
```

## Первоначальная настройка

1. **Настройте переменные окружения** (`.env`):
   ```bash
   # Qdrant Cloud (обязательно для продакшена)
   QDRANT_URL=https://your-cluster.cloud.qdrant.io
   QDRANT_API_KEY=your_api_key
   
   # LLM провайдеры
   OPENROUTER_API_KEY=your_openrouter_key
   GIGACHAT_API_KEY=your_gigachat_key
   
   # Яндекс Диск (опционально, для индексации файлов)
   YANDEX_DISK_TOKEN=your_yandex_disk_token
   YANDEX_DISK_FOLDER_URL=https://disk.yandex.ru/d/-BtoZgh5VMdsPQ
   ```

2. **Проверьте config.yaml**:
   - Убедитесь, что `collection_name: "hr2137_bot_knowledge_base"`
   - Проверьте whitelist источников
   - Настройте параметры RAG (top_k, min_score, chunk_size и т.д.)

## Индексация файлов с Яндекс Диска

### Вариант 1: Ручное скачивание (рекомендуется)

1. Скачайте все файлы с Яндекс Диска в папку `media/yandex_disk/`
2. Запустите индексацию:
   ```bash
   python index_yandex_disk.py --local-path media/yandex_disk --category "knowledge_base"
   ```

### Вариант 2: Автоматическое скачивание

Требуется OAuth токен Яндекс Диска (получить: https://yandex.ru/dev/id/doc/ru/register-client)

```bash
export YANDEX_DISK_TOKEN=your_token
python index_yandex_disk.py --yandex-url https://disk.yandex.ru/d/-BtoZgh5VMdsPQ
```

### Вариант 3: Использование существующего скрипта индексации

Если файлы уже в папке `media/`:

```bash
python index_knowledge_base.py media/ --category "knowledge_base" --recursive
```

## Использование RAG в коде

### Простой пример

```python
import asyncio
from rag_chain import RAGChain

async def main():
    # Создание RAG цепочки (Singleton - используется один экземпляр)
    rag = RAGChain()
    
    # Запрос к RAG системе
    result = await rag.query("Какие услуги вы предоставляете по HR консалтингу?")
    
    print(f"Ответ: {result['answer']}")
    print(f"Источники: {result['sources']}")
    print(f"Найдено документов: {result['context_count']}")
    print(f"Модель: {result['model']} ({result['provider']})")
    
    await rag.close()

asyncio.run(main())
```

### Использование в Telegram боте

В `app.py` уже есть интеграция с RAG через `qdrant_helper`. Для использования новой RAG системы:

```python
from rag_chain import RAGChain

async def rag_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args) if context.args else "Что такое HR консалтинг?"
    
    rag = RAGChain()
    result = await rag.query(query)
    
    response = f"🔍 Результат поиска:\n\n{result['answer']}\n\n"
    if result['sources']:
        response += f"📚 Источники:\n" + "\n".join(result['sources'][:3])
    
    await update.message.reply_text(response)
```

## Запуск Dashboard

Dashboard предоставляет веб-интерфейс для управления и тестирования RAG:

```bash
python dashboard.py
```

Или через uvicorn:

```bash
uvicorn dashboard:app --host 0.0.0.0 --port 8000 --reload
```

Dashboard доступен по адресу: http://localhost:8000

### Возможности Dashboard:

- Просмотр информации о векторной БД
- Загрузка файлов (PDF, Excel) для индексации
- Тестирование запросов к RAG
- Просмотр метрик качества
- Управление источниками

## Интеграция с существующим проектом

RAG система полностью интегрирована с существующим проектом:

- **Использует ту же коллекцию Qdrant**: `hr2137_bot_knowledge_base`
- **Использует Qwen для эмбеддингов** (как в `qdrant_helper.py`)
- **Работает с Qdrant Cloud** (если установлен `QDRANT_API_KEY`)
- **Поддерживает существующие переменные окружения**

### Отличия от старой системы:

1. **Hybrid Search** - комбинация BM25 и семантического поиска
2. **Fallback цепочка LLM** - автоматическое переключение при ошибках
3. **Dashboard** - веб-интерфейс для управления
4. **Оценка качества** - метрики для тестирования RAG

## Работа локально и через Cloud

Система автоматически определяет режим работы:

- **Если установлен `QDRANT_API_KEY`** → используется Qdrant Cloud
- **Если нет API ключа** → используется локальный Qdrant (требует Docker)

```bash
# Локальный Qdrant (для разработки)
docker run -p 6333:6333 qdrant/qdrant
export QDRANT_URL=http://localhost:6333
# QDRANT_API_KEY не требуется
```

## Troubleshooting

### Проблемы с эмбеддингами

Если возникают ошибки при генерации эмбеддингов:

```bash
# Проверьте установку transformers и torch
pip install transformers torch sentencepiece

# Проверьте, что модель доступна
python -c "from transformers import AutoModel; AutoModel.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct')"
```

### Проблемы с Qdrant

```bash
# Проверьте подключение
python -c "from qdrant_helper import get_qdrant_client; print(get_qdrant_client())"

# Проверьте коллекцию
python -c "from qdrant_helper import COLLECTION_NAME, ensure_collection; print(ensure_collection())"
```

### Проблемы с LLM

Проверьте логи для ошибок от провайдеров. Система автоматически переключится на fallback при ошибках.

## Дополнительная информация

- Подробная документация: `RAG_INTEGRATION.md`
- Конфигурация: `config.yaml`
- Примеры использования: см. код в `app.py` и `dashboard.py`






















