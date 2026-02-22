# Frontend: AnythingLLM

В этой папке лежит **Dockerfile для AnythingLLM**. Старый Next.js UI больше не используется.

## Что это

- **AnythingLLM** — единый веб-интерфейс для RAG: настройка LLM (OpenRouter), эмбеддингов, векторной БД (Qdrant и др.), загрузка документов, workspace и чат с базой знаний.
- Сервис слушает порт **3001**.
- HR_Bot подключается к AnythingLLM через Developer API (см. `docs/ANYTHINGLLM_SETUP.md`).

## Сборка и запуск

```bash
# Из корня репозитория (контекст — frontend)
docker build -f frontend/Dockerfile -t anythingllm frontend/

# Запуск
docker run -d -p 3001:3001 -v anythingllm_storage:/app/server/storage --name anythingllm anythingllm
```

Открой в браузере: **http://localhost:3001**.

## Railway

Сервис Frontend в Railway настроен на этот Dockerfile; после деплоя веб-интерфейс AnythingLLM доступен по публичному URL сервиса. В HR_Bot задай `ANYTHINGLLM_BASE_URL` на этот URL.
