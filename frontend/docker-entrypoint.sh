#!/bin/sh
# 1) Применяет миграции Prisma (создаёт таблицы system_settings, workspace_documents и др.).
# 2) Копирует custom agent skills в хранилище AnythingLLM.
# 3) Запускает AnythingLLM.

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
