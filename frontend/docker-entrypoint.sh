#!/bin/sh
# 1) Подставляет OpenRouter в OPENAI_API_* если задан только OPENROUTER_API_KEY.
# 2) Применяет миграции Prisma (создаёт таблицы system_settings, workspace_documents и др.).
# 3) Копирует custom agent skills в хранилище AnythingLLM.
# 4) Запускает AnythingLLM.

# Приоритет OpenRouter: если задан OPENROUTER_API_KEY — всегда подставляем его в OPENAI_API_*
# (перезаписываем placeholder или пустое значение, чтобы не было 401 от OpenAI)
if [ -n "${OPENROUTER_API_KEY}" ]; then
  export OPENAI_API_KEY="${OPENROUTER_API_KEY}"
  export OPENAI_API_BASE_URL="${OPENAI_API_BASE_URL:-https://openrouter.ai/api/v1}"
  echo "[entrypoint] Использую OpenRouter: OPENAI_API_KEY и BASE_URL заданы из OPENROUTER_API_KEY"
fi

# Миграции Prisma — иначе "The table main.system_settings does not exist"
if [ -f /app/server/package.json ] && [ -d /app/server/prisma ]; then
  echo "[entrypoint] Применяю миграции Prisma..."
  ( cd /app/server && npx prisma migrate deploy ) 2>/dev/null || ( cd /app/server && npx prisma db push ) 2>/dev/null || true
fi

STORAGE="${STORAGE_DIR:-/app/server/storage}"
SKILLS_DEST="${STORAGE}/plugins/agent-skills"
SKILLS_SRC="/app/skills-bundle"

# Каталоги, которые AnythingLLM ожидает (иначе "No direct uploads path found")
mkdir -p "${STORAGE}/direct-uploads" "${STORAGE}/documents" "${SKILLS_DEST}"

echo "[entrypoint] Копирую custom agent skills из ${SKILLS_SRC} в ${SKILLS_DEST}"

if [ -d "${SKILLS_SRC}" ]; then
  cp -r "${SKILLS_SRC}/." "${SKILLS_DEST}/"
  echo "[entrypoint] Скиллы скопированы:"
  ls "${SKILLS_DEST}"
else
  echo "[entrypoint] Папка ${SKILLS_SRC} не найдена, скиллы не скопированы"
fi

echo "[entrypoint] Запускаю AnythingLLM..."
exec node /app/server/index.js
