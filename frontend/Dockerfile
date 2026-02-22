# Dockerfile для AnythingLLM — веб-интерфейс RAG и базы знаний.
# Старый Next.js UI больше не используется; frontend-сервис отдаёт только AnythingLLM.
# Официальный образ: https://hub.docker.com/r/mintplexlabs/anythingllm

FROM mintplexlabs/anythingllm:latest

# AnythingLLM слушает порт 3001 (по умолчанию в образе)
ENV SERVER_PORT=3001
ENV STORAGE_DIR=/app/server/storage

EXPOSE 3001

# Том для сохранения данных между перезапусками (при монтировании в Railway/хост)
VOLUME /app/server/storage

# CMD наследуется из базового образа
