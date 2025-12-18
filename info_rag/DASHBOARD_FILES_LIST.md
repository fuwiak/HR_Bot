# 📦 Список файлов для переноса Dashboard

## 🎯 Основные файлы Dashboard

### Frontend (веб-интерфейс)
```
dashboard_static/
  ├── index.html          # HTML интерфейс (ретро UI)
  ├── style.css           # Ретро стили (зелено-черная тема)
  └── script.js           # JavaScript логика (API вызовы, UI)
```

### Backend (FastAPI)
```
dashboard.py              # Основной файл FastAPI приложения
```

## 🔗 Зависимости (обязательные модули)

### Основные модули RAG системы
```
qdrant_loader.py          # Работа с векторной БД Qdrant (Singleton)
rag_chain.py              # RAG цепочка (Singleton)
rag_evaluator.py          # Оценка метрик RAG
llm_api.py                # Универсальный LLM клиент
```

### Загрузчики данных
```
load_pdf.py               # Загрузка PDF файлов в векторную БД
load_pricelist.py         # Загрузка Excel прайс-листов
scraper.py                # Веб-скрапинг для загрузки данных
```

### Вспомогательные модули
```
whitelist.py              # Управление whitelist (используется в qdrant_loader)
```

## ⚙️ Конфигурационные файлы

```
config.yaml               # Конфигурация RAG (chunk_size, overlap, top_k и т.д.)
.env                      # Переменные окружения (или env.example)
ground_truth_qa.json      # Набор вопросов-ответов для оценки метрик
```

## 📋 Зависимости Python (requirements.txt)

Минимальный набор для dashboard:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
langchain>=0.1.0
langchain-community>=0.0.10
langchain-huggingface>=0.0.1
langchain-text-splitters>=0.0.1
qdrant-client>=1.6.9
pydantic>=2.5.0
pydantic-settings>=2.1.0
pyyaml>=6.0.1
httpx>=0.25.2
openai>=1.3.7
python-multipart==0.0.6
sentence-transformers>=2.2.2
torch>=2.1.0
numpy<2.0
pandas>=2.0.0
openpyxl>=3.1.0
rank-bm25>=0.2.2
scikit-learn>=1.3.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
PyPDF2>=3.0.0
```

## 📁 Структура для нового проекта

```
новый_проект/
├── dashboard.py
├── dashboard_static/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── qdrant_loader.py
├── rag_chain.py
├── rag_evaluator.py
├── llm_api.py
├── load_pdf.py
├── load_pricelist.py
├── scraper.py
├── whitelist.py
├── config.yaml
├── .env
├── ground_truth_qa.json
└── requirements.txt
```

## 🔍 Важные зависимости между модулями

### dashboard.py импортирует:
- `qdrant_loader.QdrantLoader`
- `rag_chain.RAGChain`
- `rag_evaluator.RAGEvaluator, GroundTruthQA, EvaluationSummary`
- `load_pdf.load_pdf`
- `load_pricelist.PriceListLoader`
- `scraper.WebScraper`

### qdrant_loader.py импортирует:
- `whitelist.WhitelistManager`

### rag_chain.py импортирует:
- `qdrant_loader.QdrantLoader`
- `llm_api.LLMClient, LLMResponse`

## ⚠️ Важные замечания

1. **Singleton Pattern**: `QdrantLoader` и `RAGChain` используют паттерн Singleton - убедитесь, что он правильно работает в новом проекте.

2. **Переменные окружения**: Проверьте `.env` файл - dashboard использует те же переменные, что и основная система (QDRANT_URL, QDRANT_API_KEY, LLM ключи и т.д.)

3. **Qdrant Storage**: Dashboard работает с локальной Qdrant БД или удаленной. Убедитесь, что путь к storage или URL настроены правильно.

4. **Модели embeddings**: Dashboard использует `sentence-transformers` для создания эмбеддингов. Модель загружается автоматически при первом использовании.

5. **Фоновые задачи**: Dashboard использует `BackgroundTasks` FastAPI для асинхронной загрузки файлов и оценки.

## 🚀 Команда для запуска

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск dashboard
python -m uvicorn dashboard:app --host 0.0.0.0 --port 8000 --reload
```

Или просто:
```bash
python dashboard.py
```

## 📝 Дополнительные файлы (опционально)

Если нужна документация:
- `DASHBOARD_README.md` - документация по dashboard

Если нужна интеграция с ботом:
- `run_both.py` - запуск бота и dashboard вместе (не обязательно для standalone dashboard)

