#!/bin/bash

# Скрипт для локального запуска (без Docker)

set -e

echo "🚀 Локальный запуск HR2137 Bot..."

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создайте .env файл на основе ENV_VARIABLES.md"
    exit 1
fi

# Загружаем переменные окружения
export $(cat .env | grep -v '^#' | xargs)

# Проверяем обязательные переменные
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "❌ TELEGRAM_TOKEN не установлен в .env"
    exit 1
fi

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "❌ OPENROUTER_API_KEY не установлен в .env"
    exit 1
fi

# Проверяем, запущен ли Qdrant (для локальной разработки)
if [ -z "$QDRANT_URL" ]; then
    export QDRANT_URL="http://localhost:6333"
fi

echo "📋 Конфигурация:"
echo "   - Qdrant: $QDRANT_URL"
echo "   - Web Interface Port: ${WEB_INTERFACE_PORT:-8081}"
echo ""

# Функция для обработки сигнала завершения
cleanup() {
    echo ""
    echo "⏹️  Получен сигнал завершения..."
    kill $BOT_PID $WEB_PID 2>/dev/null || true
    wait
    echo "✅ Процессы остановлены"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Запускаем Telegram бота в фоне
echo "🤖 Запуск Telegram бота..."
python app.py &
BOT_PID=$!

# Ждем немного
sleep 2

# Запускаем веб-интерфейс если не отключен
if [ "${DISABLE_WEB_INTERFACE:-false}" != "true" ]; then
    echo "🌐 Запуск веб-интерфейса на порту ${WEB_INTERFACE_PORT:-8081}..."
    python web_interface.py &
    WEB_PID=$!
    
    echo ""
    echo "✅ Оба сервиса запущены:"
    echo "   - Telegram Bot: PID $BOT_PID"
    echo "   - Web Interface: http://localhost:${WEB_INTERFACE_PORT:-8081} (PID $WEB_PID)"
else
    WEB_PID=""
    echo ""
    echo "✅ Telegram Bot запущен: PID $BOT_PID"
    echo "   (Веб-интерфейс отключен через DISABLE_WEB_INTERFACE=true)"
fi

echo ""
echo "💡 Для остановки нажмите Ctrl+C"
echo ""

# Ждем завершения процессов
if [ -n "$WEB_PID" ]; then
    wait $BOT_PID $WEB_PID
else
    wait $BOT_PID
fi

