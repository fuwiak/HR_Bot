# Dockerfile для AnythingLLM — веб-интерфейс RAG и базы знаний.
# Старый Next.js UI больше не используется; frontend-сервис отдаёт только AnythingLLM.
# Официальный образ: https://hub.docker.com/r/mintplexlabs/anythingllm
#
# Сборка: docker build -f frontend/Dockerfile -t anythingllm .  (из КОРНЯ репозитория!)
# Railway использует корень репозитория как build context автоматически.

FROM mintplexlabs/anythingllm:latest

# Entrypoint должен работать от root, чтобы выставить права на смонтированный Railway volume
USER root

# Порт и каталог хранилища
ENV SERVER_PORT=3001
ENV PORT=3001
ENV STORAGE_DIR=/app/server/storage
# Коллектор (документ-процессор) — обязателен для загрузки файлов в RAG
ENV COLLECTOR_PORT=8888

# gosu — для запуска сервера от пользователя anythingllm после инициализации volume
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends gosu && rm -rf /var/lib/apt/lists/*

# Каталог хранилища обязателен; при монтировании Railway volume права выставляет entrypoint
RUN mkdir -p /app/server/storage
# Постоянное хранилище: Railway Volumes (Mount Path: /app/server/storage). См. docs/RAILWAY_ANYTHINGLLM_VOLUME.md

# ── Custom agent skills ────────────────────────────────────────────────────────
# Копируем скиллы в /app/skills-bundle (ВНЕ volume-каталога STORAGE_DIR),
# чтобы Railway-volume /app/server/storage не перекрыл их при монтировании.
# Entrypoint при каждом старте копирует скиллы из /app/skills-bundle → STORAGE_DIR/plugins/agent-skills/.
# Build context должен быть корень репозитория (Railway делает это автоматически).
COPY plugins/agent-skills/ /app/skills-bundle/
# ────────────────────────────────────────────────────────────────────────────────

# Entrypoint: копирует скиллы в хранилище и запускает AnythingLLM
# Запуск через sh — базовый образ может запрещать chmod в /app
COPY frontend/docker-entrypoint.sh /app/docker-entrypoint.sh

EXPOSE 3001
EXPOSE 8888

# В Railway: Settings → Networking → Port = 3001; Variables: PORT=3001, SERVER_PORT=3001.
# ОБЯЗАТЕЛЬНО для сохранения данных между деплоями: Dashboard → сервис Frontend → Volumes
# → Add Volume → Mount Path: /app/server/storage (иначе после каждого коммита сбрасываются workspace, пароль, анкета).
# См. docs/RAILWAY_ANYTHINGLLM_VOLUME.md

ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint.sh"]
