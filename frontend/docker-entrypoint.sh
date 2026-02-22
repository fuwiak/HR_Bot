#!/bin/sh
# Этот скрипт копирует custom agent skills в хранилище AnythingLLM при каждом запуске контейнера.
# Необходимо, потому что Railway монтирует volume на STORAGE_DIR и перекрывает данные, записанные при сборке образа.

STORAGE="${STORAGE_DIR:-/app/server/storage}"
SKILLS_DEST="${STORAGE}/plugins/agent-skills"
SKILLS_SRC="/app/skills-bundle"

echo "[entrypoint] Копирую custom agent skills из ${SKILLS_SRC} в ${SKILLS_DEST}"
mkdir -p "${SKILLS_DEST}"

if [ -d "${SKILLS_SRC}" ]; then
  cp -r "${SKILLS_SRC}/." "${SKILLS_DEST}/"
  echo "[entrypoint] Скиллы скопированы:"
  ls "${SKILLS_DEST}"
else
  echo "[entrypoint] Папка ${SKILLS_SRC} не найдена, скиллы не скопированы"
fi

echo "[entrypoint] Запускаю AnythingLLM..."
exec node /app/server/index.js
