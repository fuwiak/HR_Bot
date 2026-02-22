# Dockerfile для AnythingLLM — веб-интерфейс RAG и базы знаний.
# Старый Next.js UI больше не используется; frontend-сервис отдаёт только AnythingLLM.
# Официальный образ: https://hub.docker.com/r/mintplexlabs/anythingllm

FROM mintplexlabs/anythingllm:latest

# AnythingLLM слушает порт 3001 (по умолчанию в образе)
ENV SERVER_PORT=3001
ENV STORAGE_DIR=/app/server/storage

EXPOSE 3001

# Сохранение данных AnythingLLM: в Railway настрой тома в Dashboard → Volumes (mount path: /app/server/storage)

# CMD наследуется из базового образа
