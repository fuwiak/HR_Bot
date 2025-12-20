# Интеграция RAG системы для HR2137 Bot

## Обзор

В проект интегрирована полноценная RAG (Retrieval-Augmented Generation) система для работы с базой знаний HR консультанта. Система включает:

- **Qdrant** - векторная база данных для семантического поиска
- **Qwen2.5-1.5B-Instruct** - модель для генерации эмбеддингов
- **DeepSeek Chat** (primary) и **GigaChat** (fallback) - LLM для генерации ответов
- **Hybrid Search** - комбинация BM25 и Dense search для лучших результатов
- **Dashboard** - веб-интерфейс для управления и тестирования RAG

## Структура файлов

### Основные модули

- `qdrant_loader.py` - Загрузка и управление документами в Qdrant (Singleton)
- `rag_chain.py` - RAG цепочка для генерации ответов (Singleton)
- `llm_api.py` - Универсальный LLM клиент с fallback
- `rag_evaluator.py` - Оценка качества RAG системы
- `whitelist.py` - Управление whitelist источников

### Загрузчики данных

- `load_pdf.py` - Загрузка PDF файлов
- `load_pricelist.py` - Загрузка Excel прайс-листов
- `scraper.py` - Веб-скрапинг для загрузки данных
- `index_yandex_disk.py` - Индексация файлов с Яндекс Диска

### Интерфейсы

- `dashboard.py` - FastAPI дашборд для управления RAG
- `config.yaml` - Конфигурация RAG системы

## Конфигурация

### config.yaml

```yaml
# Whitelist источников
whitelist:
  - https://disk.yandex.ru/d/-BtoZgh5VMdsPQ
  - file://media/

# LLM параметры
llm:
  primary:
    provider: "openrouter"
    model: "deepseek/deepseek-chat"
  
  fallback_chain:
    - provider: "openrouter"
      model: "deepseek/deepseek-chat"
    - provider: "gigachat"
      model: "GigaChat:latest"

# RAG параметры
rag:
  collection_name: "hr2137_bot_knowledge_base"
  top_k: 10
  min_score: 0.3
  chunk_size: 500
  chunk_overlap: 50
  search_strategy: "hybrid"
```

## Использование

### 1. Индексация файлов с Яндекс Диска

```bash
# Использование локальной папки с файлами
python index_yandex_disk.py --local-path /path/to/files --category "knowledge_base"

# Скачивание и индексация (требует токен Яндекс Диска)
python index_yandex_disk.py --yandex-url https://disk.yandex.ru/d/-BtoZgh5VMdsPQ --token YOUR_TOKEN
```

### 2. Использование RAG в коде

```python
from rag_chain import RAGChain

# Создание RAG цепочки (Singleton)
rag = RAGChain()

# Запрос к RAG системе
result = await rag.query("Какие услуги вы предоставляете?")

print(result["answer"])  # Ответ
print(result["sources"])  # Источники
print(result["context_count"])  # Количество найденных документов
```

### 3. Запуск Dashboard

```bash
# Запуск dashboard
python dashboard.py

# Или через uvicorn
uvicorn dashboard:app --host 0.0.0.0 --port 8000 --reload
```

Dashboard доступен по адресу: http://localhost:8000

## Интеграция с существующим проектом

### Использование существующих модулей

RAG система интегрирована с существующими модулями проекта:

- **qdrant_helper.py** - используется для генерации эмбеддингов через Qwen
- **llm_helper.py** - может использоваться параллельно с llm_api.py
- **COLLECTION_NAME** - используется та же коллекция: "hr2137_bot_knowledge_base"

### Работа с Qdrant

RAG система работает с Qdrant Cloud (если установлен `QDRANT_API_KEY`) или локальным сервером:

```bash
# Qdrant Cloud (рекомендуется)
export QDRANT_URL=https://your-cluster.cloud.qdrant.io
export QDRANT_API_KEY=your_api_key

# Локальный Qdrant (для разработки)
# docker run -p 6333:6333 qdrant/qdrant
export QDRANT_URL=http://localhost:6333
# QDRANT_API_KEY не требуется
```

## Особенности

### Hybrid Search

Система использует комбинированный поиск:
- **Dense Search** - семантический поиск по эмбеддингам (Qwen)
- **BM25** - поиск по ключевым словам
- **Hybrid** - комбинация обоих методов с настраиваемыми весами

### Whitelist

Все документы фильтруются по whitelist источников. Это гарантирует, что RAG использует только проверенные источники.

### Fallback цепочка LLM

При ошибке или низкой уверенности основной модели автоматически пробуются fallback модели:
1. DeepSeek Chat (OpenRouter) - primary
2. DeepSeek Chat (OpenRouter) - fallback 1
3. GigaChat - fallback 2 (российское решение)

## Зависимости

Все необходимые зависимости добавлены в `requirements.txt`:

- `qdrant-client` - клиент Qdrant
- `transformers`, `torch` - для Qwen эмбеддингов
- `langchain`, `langchain-community`, `langchain-text-splitters` - для чанкинга
- `rank-bm25` - для BM25 поиска
- `fastapi`, `uvicorn` - для dashboard
- `beautifulsoup4`, `lxml` - для веб-скрапинга
- `pandas`, `openpyxl` - для работы с Excel
- `PyPDF2` - для работы с PDF

## Тестирование

### Оценка качества RAG

```python
from rag_evaluator import RAGEvaluator, GroundTruthQA
from rag_chain import RAGChain

rag_chain = RAGChain()
evaluator = RAGEvaluator(rag_chain=rag_chain)

# Загрузите ground truth QA из файла
qa_list = [
    GroundTruthQA(
        question="Вопрос",
        expected_answer="Ожидаемый ответ",
        category="general",
        expected_sources=["source1", "source2"],
        key_facts=["факт1", "факт2"]
    )
]

summary = await evaluator.evaluate(qa_list, k=5)
evaluator.save_results(summary, "evaluation_results.json")
```

## Troubleshooting

### Проблемы с эмбеддингами

Если возникают проблемы с генерацией эмбеддингов:
1. Проверьте, что transformers и torch установлены
2. Убедитесь, что модель Qwen доступна: `Qwen/Qwen2.5-1.5B-Instruct`

### Проблемы с Qdrant

Если Qdrant недоступен:
1. Проверьте `QDRANT_URL` и `QDRANT_API_KEY`
2. Для локального использования запустите Docker контейнер
3. Проверьте, что коллекция существует: используйте `ensure_collection()`

### Проблемы с LLM

Если LLM не отвечает:
1. Проверьте API ключи: `OPENROUTER_API_KEY`, `GIGACHAT_API_KEY`
2. Проверьте логи для ошибок от провайдеров
3. Система автоматически переключится на fallback при ошибках

## Дополнительная информация

- Все модули используют паттерн Singleton для оптимизации ресурсов
- RAG система может работать в фоновом режиме
- Dashboard поддерживает асинхронную загрузку файлов
- Система автоматически перестраивает BM25 индекс при добавлении документов





















