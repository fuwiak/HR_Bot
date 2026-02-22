# Интеграция AnythingLLM с HR_Bot

HR_Bot может использовать [AnythingLLM](https://github.com/Mintplex-Labs/anything-llm) как единое место настройки RAG: LLM (OpenRouter), эмбеддинги, векторная БД (в т.ч. Qdrant) и документы настраиваются в AnythingLLM; бот обращается к workspace через Developer API.

## Jak włączyć Web UI AnythingLLM

Web UI to osobna aplikacja — musisz ją uruchomić (lokalnie lub na Railway), potem otworzyć w przeglądarce.

### Lokalnie (Docker)

1. Zainstaluj Docker. Sklonuj repozytorium AnythingLLM lub użyj gotowego obrazu.
2. Uruchom kontener (port **3001**):

```bash
docker run -d -p 3001:3001 \
  -v anythingllm_storage:/app/server/storage \
  --name anythingllm \
  mintplexlabs/anythingllm
```

3. Otwórz w przeglądarce: **http://localhost:3001** — to jest Web UI AnythingLLM (logowanie, ustawienia, workspace, dokumenty).

Szczegóły: [AnythingLLM Docker Quickstart](https://docs.anythingllm.com/installation-docker/quickstart).

### Na Railway

1. Wejdź na [Railway – AnythingLLM template](https://railway.app/template/HNSCS1?referralCode=WFgJkn).
2. Wdróż projekt (np. „Deploy Now”). Railway przypisze publiczny URL (np. `https://twoja-app.up.railway.app`).
3. Web UI AnythingLLM = ten URL w przeglądarce (np. `https://twoja-app.up.railway.app`).

Potem w HR_Bot ustaw `ANYTHINGLLM_BASE_URL` na ten sam URL (bez ukośnika na końcu).

---

## Когда использовать

- Нужна единая точка настройки моделей и базы знаний (в AnythingLLM UI).
- Хотите управлять документами и workspace без изменения кода HR_Bot.

При отсутствии настроенного AnythingLLM или при выключенном флаге бот работает по-старому: Qdrant + OpenRouter напрямую.

## 1. Развёртывание AnythingLLM

В этом репозитории AnythingLLM разворачивается из **frontend**: в папке `frontend/` лежит отдельный Dockerfile только под AnythingLLM (старый Next.js UI не используется).

- **Локально (Docker)** — из корня репозитория:
  ```bash
  docker build -f frontend/Dockerfile -t anythingllm frontend/
  docker run -d -p 3001:3001 -v anythingllm_storage:/app/server/storage --name anythingllm anythingllm
  ```
  Интерфейс: **http://localhost:3001**.

- **Railway**: сервис Frontend настроен на `frontend/Dockerfile` и порт 3001; после деплоя откройте URL сервиса в браузере. Либо используйте [шаблон AnythingLLM на Railway](https://railway.app/template/HNSCS1?referralCode=WFgJkn) отдельно.

После развёртывания откройте веб-интерфейс AnythingLLM (локально или по URL Railway).

## 2. Настройка в AnythingLLM

1. **LLM**: Settings → LLM Provider → OpenRouter, укажите модель (например DeepSeek, как в `config/llm.yaml`).
2. **Embedder**: выберите модель с поддержкой русского (или OpenRouter), размерность по возможности совместима с вашей коллекцией (например 1536).
3. **Vector DB**: Qdrant (если используете существующий кластер) или встроенная LanceDB.
4. **Workspace**: создайте workspace (например имя «HR Bot», slug `hr-bot`), загрузите документы через UI (или позже через API).

## 3. API ключ

В AnythingLLM: **Settings → Developer API** → создайте API ключ. Не публикуйте ключ; он нужен только для сервисов HR_Bot.

## 4. Переменные окружения HR_Bot

Добавьте в окружение Telegram-бота и/или backend (например в Railway → Variables):

```env
USE_ANYTHINGLLM_RAG=true
ANYTHINGLLM_BASE_URL=https://your-anythingllm.up.railway.app
ANYTHINGLLM_API_KEY=your_anythingllm_api_key
ANYTHINGLLM_WORKSPACE_SLUG=hr-bot
```

- `ANYTHINGLLM_BASE_URL` — базовый URL инстанса AnythingLLM (без слэша в конце).
- `ANYTHINGLLM_API_KEY` — ключ из Settings → Developer API.
- `ANYTHINGLLM_WORKSPACE_SLUG` — slug workspace, в котором загружены документы.
- `USE_ANYTHINGLLM_RAG=true` — включить использование AnythingLLM для RAG; при `false` или отсутствии используется прежняя схема (Qdrant + OpenRouter).

Описание переменных также есть в `railway.env.example`.

## 5. Поведение HR_Bot

- **Ответы в Telegram** (обработчик сообщений): при запросе, для которого классификатор решил использовать RAG (`use_rag=True`), если включён AnythingLLM — запрос уходит в AnythingLLM workspace chat; иначе — поиск в Qdrant и ответ через OpenRouter.
- **Команда /rag_search**: при включённом AnythingLLM — один вызов к workspace API; иначе — поиск в Qdrant и генерация через `generate_with_fallback`.
- **Backend `/rag/query`**: для не-ценовых запросов при включённом AnythingLLM — вызов workspace chat; иначе — `RAGChain.query()`. Ценовые запросы по-прежнему могут идти через LangGraph при необходимости.

При недоступности AnythingLLM или ошибке API бот автоматически переходит на старый пайплайн (Qdrant + OpenRouter).

## 6. Документы

- Текущую базу в Qdrant можно не переносить: загрузите те же (или обновлённые) документы в workspace AnythingLLM через UI.
- Если подключаете AnythingLLM к тому же Qdrant — избегайте конфликта имён коллекций; при отдельной БД в AnythingLLM загрузка только через AnythingLLM.

## 7. Проверка API

На инстансе AnythingLLM откройте `/api/docs` — там полный список эндпоинтов и форматы запросов/ответов. При изменении формата ответа чата может потребоваться правка `services/integrations/anythingllm_client.py`.
