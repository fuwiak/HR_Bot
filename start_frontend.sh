#!/bin/bash
# Запуск frontend (Next.js)

cd "$(dirname "$0")/frontend"

echo "🚀 Запуск Frontend (Next.js) на порту 3000..."
echo "📍 URL: http://localhost:3000"
echo ""

# Проверяем наличие node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 Установка зависимостей..."
    npm install
fi

# Запускаем Next.js dev server
npm run dev



















