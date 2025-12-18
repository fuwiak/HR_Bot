# RAG Endpoints в web_interface.py

Все endpoints для работы с RAG системой доступны в `web_interface.py`.

## 🔍 Поиск и запросы

### `GET /rag/test`
Тестовый RAG запрос через GET (удобно для браузера)

**Параметры:**
- `query` (строка) - вопрос для тестирования (по умолчанию: "Что такое HR консалтинг?")
- `top_k` (int) - количество результатов (по умолчанию: 5)

**Пример:**
```
GET /rag/test?query=Какие услуги вы предоставляете?&top_k=5
```

### `POST /rag/query`
Полноценный RAG запрос с генерацией ответа через LLM

**Тело запроса:**
```json
{
  "query": "Ваш вопрос",
  "top_k": 5,
  "min_score": 0.3
}
```

**Ответ:**
```json
{
  "status": "success",
  "query": "Ваш вопрос",
  "answer": "Ответ от LLM...",
  "sources": ["source1", "source2"],
  "context_count": 3,
  "provider": "openrouter",
  "model": "deepseek/deepseek-chat",
  "confidence": 0.85,
  "tokens_used": 150,
  "timestamp": "2024-12-14T18:30:00"
}
```

### `GET /rag/search`
Поиск в RAG базе знаний (старый метод для совместимости)

**Параметры:**
- `query` (строка) - поисковый запрос
- `limit` (int) - количество результатов (по умолчанию: 5)

## 📊 Статистика и информация

### `GET /rag/stats`
Статистика RAG базы знаний

**Ответ:**
```json
{
  "collection_name": "hr2137_bot_knowledge_base",
  "points_count": 1500,
  "vectors_count": 1500,
  "status": "green",
  "source": "qdrant_loader"
}
```

### `GET /rag/docs`
Список документов в базе знаний

**Параметры:**
- `limit` (int) - максимальное количество документов (по умолчанию: 50)

## ⚙️ Workflow (действия)

### `POST /rag/workflow/evaluate`
Запуск оценки RAG системы

**Требования:**
- Файл `ground_truth_qa.json` с тестовыми вопросами

**Ответ:**
```json
{
  "status": "success",
  "output_file": "evaluation_results_20241214_183000.json",
  "summary": {
    "total_questions": 10,
    "precision_at_k_regulated": 0.85,
    "precision_at_k_general": 0.78,
    "precision_at_k_overall": 0.82,
    "mrr_overall": 0.91,
    "groundedness_overall": 0.88,
    "halucination_rate_overall": 0.12
  }
}
```

### `POST /rag/workflow/load-pdf`
Загрузка PDF файла в RAG базу знаний

**Форма:**
- `file` (File) - PDF файл для загрузки

**Ответ:**
```json
{
  "status": "success",
  "filename": "document.pdf",
  "chunks_count": 45,
  "source_url": "file://media/document.pdf",
  "message": "Загружено 45 чанков"
}
```

### `POST /rag/workflow/scrape`
Скрапинг сайтов из whitelist для загрузки в RAG

**Ответ:**
```json
{
  "status": "success",
  "pages_loaded": 15,
  "urls_processed": 5,
  "message": "Загружено 15 страниц"
}
```

## 📈 Метрики

### `GET /rag/metrics/latest`
Получение последних метрик оценки

**Ответ:**
```json
{
  "status": "success",
  "file": "evaluation_results_20241214_183000.json",
  "metrics": {
    "total_questions": 10,
    "precision_at_k_overall": 0.82,
    "mrr_overall": 0.91,
    ...
  }
}
```

## 🎛️ Параметры

### `GET /rag/parameters`
Получение текущих параметров RAG

**Ответ:**
```json
{
  "status": "success",
  "parameters": {
    "chunk_size": 500,
    "chunk_overlap": 50,
    "top_k": 10,
    "min_score": 0.3,
    "temperature": 0.7,
    "max_tokens": 2048
  }
}
```

### `POST /rag/parameters`
Обновление параметров RAG (временно, без сохранения в config.yaml)

**Тело запроса:**
```json
{
  "chunk_size": 600,
  "top_k": 15,
  "temperature": 0.8
}
```

## 🏥 Health Check

### `GET /health`
Проверка здоровья сервиса и статуса RAG

**Ответ:**
```json
{
  "status": "ok",
  "timestamp": "2024-12-14T18:30:00",
  "integrations_available": true,
  "rag_system": "available"
}
```

## Примеры использования

### Тестовый запрос через curl:
```bash
# GET запрос
curl "http://localhost:8081/rag/test?query=Что такое HR консалтинг?"

# POST запрос
curl -X POST http://localhost:8081/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Какие услуги вы предоставляете?", "top_k": 5}'
```

### Загрузка PDF:
```bash
curl -X POST http://localhost:8081/rag/workflow/load-pdf \
  -F "file=@document.pdf"
```

### Запуск оценки:
```bash
curl -X POST http://localhost:8081/rag/workflow/evaluate
```

### Обновление параметров:
```bash
curl -X POST http://localhost:8081/rag/parameters \
  -H "Content-Type: application/json" \
  -d '{"top_k": 15, "temperature": 0.8}'
```

## Примечания

- Все endpoints требуют активной RAG системы (проверка через `RAG_AVAILABLE`)
- Параметры обновляются временно и не сохраняются в `config.yaml`
- Для оценки требуется файл `ground_truth_qa.json` с тестовыми вопросами
- Загрузка PDF сохраняет файлы в папку `media/`









