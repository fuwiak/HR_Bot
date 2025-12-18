#!/bin/bash
# Скрипт для автоматической настройки трех сервисов на Railway
# с правильными Dockerfile Path для каждого сервиса

set -e

echo "🚂 Настройка сервисов на Railway"
echo "================================"
echo ""

# Проверка установки Railway CLI
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI не установлен"
    echo "Установите: npm i -g @railway/cli"
    exit 1
fi

echo "✅ Railway CLI установлен"
echo ""

# Проверка авторизации
if ! railway whoami &> /dev/null; then
    echo "⚠️  Не авторизован в Railway"
    echo "Выполните: railway login"
    exit 1
fi

echo "✅ Авторизован в Railway"
echo ""

# Создание Telegram Bot сервиса
echo "📦 Создание Telegram Bot сервиса..."
if railway service create telegram-bot 2>/dev/null; then
    echo "✅ Сервис telegram-bot создан"
else
    echo "⚠️  Сервис telegram-bot уже существует или ошибка создания"
fi

# Настройка Dockerfile Path для Telegram Bot
echo "🔧 Настройка Dockerfile Path для telegram-bot..."
railway variables set DOCKERFILE_PATH=Dockerfile.telegram --service telegram-bot 2>/dev/null || true

# Создание Backend сервиса
echo "📦 Создание Backend сервиса..."
if railway service create backend 2>/dev/null; then
    echo "✅ Сервис backend создан"
else
    echo "⚠️  Сервис backend уже существует или ошибка создания"
fi

# Настройка Dockerfile Path для Backend
echo "🔧 Настройка Dockerfile Path для backend..."
railway variables set DOCKERFILE_PATH=Dockerfile.backend --service backend 2>/dev/null || true

# Создание Frontend сервиса
echo "📦 Создание Frontend сервиса..."
if railway service create frontend 2>/dev/null; then
    echo "✅ Сервис frontend создан"
else
    echo "⚠️  Сервис frontend уже существует или ошибка создания"
fi

# Настройка Dockerfile Path для Frontend
echo "🔧 Настройка Dockerfile Path для frontend..."
railway variables set DOCKERFILE_PATH=Dockerfile.frontend --service frontend 2>/dev/null || true

echo ""
echo "✅ Настройка завершена!"
echo ""
echo "📝 Следующие шаги:"
echo "1. В Railway Dashboard для каждого сервиса:"
echo "   Settings → Build → Dockerfile Path"
echo "   - telegram-bot: Dockerfile.telegram"
echo "   - backend: Dockerfile.backend"
echo "   - frontend: Dockerfile.frontend"
echo ""
echo "2. Добавьте переменные окружения для каждого сервиса"
echo "3. Запустите деплой: railway up"
