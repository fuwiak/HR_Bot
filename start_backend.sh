#!/bin/bash
# Запуск backend (FastAPI)

cd "$(dirname "$0")"

echo "🚀 Запуск Backend (FastAPI) на порту 8081..."
echo "📍 URL: http://localhost:8081"
echo ""

# Активируем venv если есть
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Запускаем web_interface.py
python web_interface.py









