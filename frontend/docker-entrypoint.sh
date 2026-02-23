#!/bin/sh
# 1) Подставляет OpenRouter в OPENAI_API_* если задан только OPENROUTER_API_KEY.
# 2) Применяет миграции Prisma (создаёт таблицы system_settings, workspace_documents и др.).
# 3) Копирует custom agent skills в хранилище AnythingLLM.
# 4) Запускает AnythingLLM.

# OpenAI не используем — только OpenRouter. Убираем placeholder и подставляем ключ OpenRouter.
case "${OPENAI_API_KEY}" in *[Pp]lace*) export OPENAI_API_KEY="" ;; esac
ROUTER_KEY="${OPENROUTER_API_KEY:-${OPENROUTER_KEY}}"
if [ -n "${ROUTER_KEY}" ]; then
  export OPENAI_API_KEY="${ROUTER_KEY}"
  export OPENAI_API_BASE_URL="${OPENAI_API_BASE_URL:-https://openrouter.ai/api/v1}"
  echo "[entrypoint] OpenRouter: OPENAI_API_KEY и BASE_URL заданы (OpenAI отключён)"
else
  echo "[entrypoint] WARNING: Задайте OPENROUTER_API_KEY в Railway (Variables), иначе будет 401."
fi

# Миграции Prisma — иначе "The table main.system_settings does not exist"
if [ -f /app/server/package.json ] && [ -d /app/server/prisma ]; then
  echo "[entrypoint] Применяю миграции Prisma..."
  ( cd /app/server && npx prisma migrate deploy ) 2>/dev/null || ( cd /app/server && npx prisma db push ) 2>/dev/null || true
fi

STORAGE="${STORAGE_DIR:-/app/server/storage}"
SKILLS_DEST="${STORAGE}/plugins/agent-skills"
SKILLS_SRC="/app/skills-bundle"

# Каталоги, которые AnythingLLM ожидает (иначе "No direct uploads path found").
# При монтировании Railway volume каталог приходит без прав на запись — создаём от root и отдаём anythingllm.
mkdir -p "${STORAGE}/direct-uploads" "${STORAGE}/documents" "${SKILLS_DEST}"
chown -R anythingllm:anythingllm "${STORAGE}"

echo "[entrypoint] Копирую custom agent skills из ${SKILLS_SRC} в ${SKILLS_DEST}"

if [ -d "${SKILLS_SRC}" ]; then
  cp -r "${SKILLS_SRC}/." "${SKILLS_DEST}/"
  chown -R anythingllm:anythingllm "${SKILLS_DEST}"
  echo "[entrypoint] Скиллы скопированы:"
  ls "${SKILLS_DEST}"
else
  echo "[entrypoint] Папка ${SKILLS_SRC} не найдена, скиллы не скопированы"
fi

echo "[entrypoint] Запускаю коллектор (документ-процессор) на порту ${COLLECTOR_PORT:-8888}..."
COLLECTOR_PORT="${COLLECTOR_PORT:-8888}"
export COLLECTOR_PORT

if [ -f /app/collector/index.js ]; then
  gosu anythingllm node /app/collector/index.js &
  COLLECTOR_PID=$!
  echo "[entrypoint] Коллектор запущен (pid=${COLLECTOR_PID}, port=${COLLECTOR_PORT})"
else
  echo "[entrypoint] WARNING: /app/collector/index.js не найден, документ-процессор недоступен"
fi

echo "[entrypoint] Запускаю AnythingLLM server..."
exec gosu anythingllm node /app/server/index.js
