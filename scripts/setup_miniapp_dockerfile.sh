#!/bin/bash
# Скрипт для автоматической настройки Dockerfile Path для Mini App сервиса
# Использование: ./scripts/setup_miniapp_dockerfile.sh [SERVICE_NAME]

set -e

SERVICE_NAME="${1:-MINI-APP}"
DOCKERFILE_PATH="frontend/Dockerfile"

echo "🔧 Настройка Dockerfile Path для сервиса: $SERVICE_NAME"
echo "=========================================="
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

# Подключение к сервису
echo "📦 Подключение к сервису $SERVICE_NAME..."
if railway link -s "$SERVICE_NAME" 2>/dev/null; then
    echo "✅ Подключен к сервису $SERVICE_NAME"
else
    echo "⚠️  Не удалось подключиться к сервису $SERVICE_NAME"
    echo "Убедитесь, что сервис существует в Railway Dashboard"
    exit 1
fi

echo ""

# Установка переменной RAILWAY_DOCKERFILE_PATH
echo "🔧 Установка RAILWAY_DOCKERFILE_PATH=$DOCKERFILE_PATH..."
if railway variables --set "RAILWAY_DOCKERFILE_PATH=$DOCKERFILE_PATH" 2>/dev/null; then
    echo "✅ Переменная RAILWAY_DOCKERFILE_PATH установлена"
else
    echo "⚠️  Не удалось установить переменную через CLI"
    echo "Установите вручную в Railway Dashboard:"
    echo "   Settings → Variables → Add Variable"
    echo "   Key: RAILWAY_DOCKERFILE_PATH"
    echo "   Value: $DOCKERFILE_PATH"
fi

echo ""

# Проверка текущей конфигурации
echo "📋 Текущая конфигурация:"
railway variables 2>&1 | grep -E "RAILWAY_DOCKERFILE_PATH|PORT|NODE_ENV" || echo "   (переменные не найдены)"

echo ""
echo "✅ Настройка завершена!"
echo ""
echo "📝 Следующие шаги:"
echo "1. Проверьте в Railway Dashboard:"
echo "   Settings → Build → Dockerfile Path"
echo "   Должно быть: $DOCKERFILE_PATH"
echo ""
echo "2. Если Dockerfile Path не изменился, установите вручную:"
echo "   Settings → Build → Dockerfile Path → $DOCKERFILE_PATH"
echo ""
echo "3. Перезапустите сервис:"
echo "   Deployments → Redeploy"
