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

Frontend (AnythingLLM) z tego repozytorium jest dostępny pod adresem: **https://anastassiya-hr-bot.up.railway.app**. W Railway dla serwisu Frontend ustaw w Settings → Networking port 3001 i domenę `anastassiya-hr-bot.up.railway.app`. W HR_Bot: `ANYTHINGLLM_BASE_URL=https://anastassiya-hr-bot.up.railway.app`.

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

- **Railway**: сервис Frontend настроен на `frontend/Dockerfile` и порт 3001. AnythingLLM Web UI доступен по адресу: **https://anastassiya-hr-bot.up.railway.app** — в Railway для сервиса Frontend укажите в Settings → Networking домен `anastassiya-hr-bot.up.railway.app` (или добавьте custom domain).

После развёртывания откройте веб-интерфейс: **https://anastassiya-hr-bot.up.railway.app**.

## 2. Настройка в AnythingLLM

1. **LLM**: Settings → LLM Provider → OpenRouter, укажите модель (например DeepSeek, как в `config/llm.yaml`).
2. **Embedder**: выберите модель с поддержкой русского (или OpenRouter), размерность по возможности совместима с вашей коллекцией (например 1536).
3. **Vector DB**: Qdrant (если используете существующий кластер) или встроенная LanceDB.
4. **Workspace**: создайте workspace (например имя «HR Bot», slug `hr-bot`), загрузите документы через UI (или позже через API).

## 3. API ключ

В AnythingLLM: **Settings → Developer API** → создайте API ключ. Не публикуйте ключ; он нужен только для сервисов HR_Bot.

## 4. Переменные окружения сервиса Frontend (AnythingLLM) в Railway

В Railway откройте **сервис Frontend** → **Variables** и задайте:

| Переменная      | Значение   | Обязательно | Описание |
|-----------------|------------|-------------|----------|
| `PORT`          | `3001`     | да          | Порт, на котором слушает приложение; должен совпадать с Port в Settings → Networking. |
| `SERVER_PORT`   | `3001`     | да          | То же для AnythingLLM (читает эту переменную). |
| `STORAGE_DIR`   | `/app/server/storage` | нет | Уже задано в Dockerfile; можно не дублировать. |
| `DISABLE_TELEMETRY` | `true` | нет       | Отключить анонимную телеметрию AnythingLLM. |
| `WEEEEK_TOKEN`  | `e9b78361-...` | нет    | API-ключ Weeeek — нужен для работы custom agent skill «Weeeek Manager». |
| `DATABASE_URL`  | —              | нет    | Если задан (PostgreSQL), AnythingLLM использует его; при старте контейнера применяются миграции Prisma (`system_settings`, `workspace_documents` и др.). Без `DATABASE_URL` используется встроенная SQLite. |

Остальное (LLM, Embedder, векторная БД) настраивается после первого входа через веб-интерфейс AnythingLLM (Settings в приложении).

**Ошибка «The table main.system_settings does not exist»:** при старте контейнера entrypoint автоматически запускает `prisma migrate deploy` (или `prisma db push`), создавая нужные таблицы. После обновления образа сделайте **Redeploy** сервиса Frontend.

## 4.1. Custom agent skills (Weeeek Manager)

Скилл «Weeeek Manager» встроен прямо в Docker-образ: при каждом запуске контейнера entrypoint автоматически копирует папку скилла из `/app/skills-bundle/weeek-manager/` в `STORAGE_DIR/plugins/agent-skills/weeek-manager/`.

**Что нужно сделать:**
1. Убедиться, что в переменных сервиса Frontend на Railway задан **`WEEEEK_TOKEN`** (тот же ключ, что у Telegram-бота — `WEEEK_API_KEY`).
2. После деплоя открыть AnythingLLM UI → **Agents** → найти скилл **«Weeeek Manager»** и включить его.
3. Если скилл не появился — перезагрузить страницу (F5). Если всё равно нет — проверить логи Railway: должна быть строка `[entrypoint] Скиллы скопированы`.

**Локальная сборка (из корня репозитория):**
```bash
docker build -f frontend/Dockerfile -t anythingllm .
docker run -d -p 3001:3001 \
  -v anythingllm_storage:/app/server/storage \
  -e WEEEEK_TOKEN=e9b78361-0705-408a-af49-ca4300b5cf1b \
  --name anythingllm anythingllm
```
⚠️ Важно: `docker build` запускать из **корня** репозитория (`.`), а не из `frontend/`.

**Settings → Networking** для сервиса Frontend: **Port** = **3001**.

---

## 5. Переменные окружения HR_Bot (Telegram/Backend)

Добавьте в окружение Telegram-бота и/или backend (например в Railway → Variables):

```env
USE_ANYTHINGLLM_RAG=true
ANYTHINGLLM_BASE_URL=https://your-anythingllm.up.railway.app
ANYTHINGLLM_API_KEY=your_anythingllm_api_key
ANYTHINGLLM_WORKSPACE_SLUG=hr-bot
```

- `ANYTHINGLLM_BASE_URL` — базовый URL инстанса AnythingLLM (без слэша в конце). Для продакшена: `https://anastassiya-hr-bot.up.railway.app`.
- `ANYTHINGLLM_API_KEY` — ключ из Settings → Developer API.
- `ANYTHINGLLM_WORKSPACE_SLUG` — slug workspace, в котором загружены документы.
- `USE_ANYTHINGLLM_RAG=true` — включить использование AnythingLLM для RAG; при `false` или отсутствии используется прежняя схема (Qdrant + OpenRouter).

Описание переменных также есть в `railway.env.example`.

## 6. Поведение HR_Bot

- **Ответы в Telegram** (обработчик сообщений): при запросе, для которого классификатор решил использовать RAG (`use_rag=True`), если включён AnythingLLM — запрос уходит в AnythingLLM workspace chat; иначе — поиск в Qdrant и ответ через OpenRouter.
- **Команда /rag_search**: при включённом AnythingLLM — один вызов к workspace API; иначе — поиск в Qdrant и генерация через `generate_with_fallback`.
- **Backend `/rag/query`**: для не-ценовых запросов при включённом AnythingLLM — вызов workspace chat; иначе — `RAGChain.query()`. Ценовые запросы по-прежнему могут идти через LangGraph при необходимости.

При недоступности AnythingLLM или ошибке API бот автоматически переходит на старый пайплайн (Qdrant + OpenRouter).

## 7. Документы

- Текущую базу в Qdrant можно не переносить: загрузите те же (или обновлённые) документы в workspace AnythingLLM через UI.
- Если подключаете AnythingLLM к тому же Qdrant — избегайте конфликта имён коллекций; при отдельной БД в AnythingLLM загрузка только через AnythingLLM.

## 8. Проверка API

На инстансе AnythingLLM откройте `/api/docs` — там полный список эндпоинтов и форматы запросов/ответов. При изменении формата ответа чата может потребоваться правка `services/integrations/anythingllm_client.py`.

## 9. Ошибка «Application failed to respond» в Railway

Если после деплоя открывается «Application failed to respond» на https://anastassiya-hr-bot.up.railway.app:

1. **Порт** — приложение слушает **3001**. В Railway: сервис Frontend → **Settings → Networking → Port** укажи **3001** (без кавычек). Иначе Railway стучится не на тот порт и считает сервис недоступным.
2. **Переменные** — в **Variables** сервиса добавь (если ещё нет): `PORT=3001`, `SERVER_PORT=3001`.
3. **Хранилище** — в логах может быть «No direct uploads path found»: в Dockerfile уже создаётся каталог `/app/server/storage`. Для сохранения данных между деплоями: **Dashboard → сервис Frontend → Volumes** → добавь том с **Mount Path** `/app/server/storage`.
4. После правок сделай **Redeploy** сервиса.
