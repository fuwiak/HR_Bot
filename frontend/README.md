# Frontend: AnythingLLM

**Сервис frontend в этом репозитории — это только AnythingLLM.** Старый Next.js UI для деплоя больше не используется.

## Что здесь

- **Dockerfile** — собирает образ [AnythingLLM](https://github.com/Mintplex-Labs/anything-llm) (официальный `mintplexlabs/anythingllm`). Веб-интерфейс RAG: настройка LLM (OpenRouter), эмбеддингов, векторной БД, загрузка документов, workspace, чат с базой знаний.
- **Порт:** 3001 (не 3000).
- HR_Bot подключается к AnythingLLM по API: см. `docs/ANYTHINGLLM_SETUP.md`.

## Локальный запуск

```bash
# Из корня репозитория
docker build -f frontend/Dockerfile -t anythingllm frontend/
docker run -d -p 3001:3001 -v anythingllm_storage:/app/server/storage --name anythingllm anythingllm
```

Открой в браузере: **http://localhost:3001**.

## Railway

Сервис **Frontend** в Railway настроен на `frontend/Dockerfile` и отдаёт AnythingLLM. Доступ: **https://anastassiya-hr-bot.up.railway.app**. В настройках сервиса укажи **Port: 3001** (Settings → Networking) и домен `anastassiya-hr-bot.up.railway.app`. В HR_Bot: `ANYTHINGLLM_BASE_URL=https://anastassiya-hr-bot.up.railway.app`.

## Подробнее

- `README_ANYTHINGLLM.md` — кратко про сборку и запуск.
- `docs/ANYTHINGLLM_SETUP.md` — настройка AnythingLLM и интеграция с HR_Bot.
