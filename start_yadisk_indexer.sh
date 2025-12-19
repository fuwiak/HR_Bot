#!/bin/sh
# Запуск Yandex Disk Indexer в фоновом режиме

echo "🚀 Запуск Yandex Disk Indexer..."

# Загружаем переменные окружения
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Переменные окружения загружены из .env"
fi

# Проверяем наличие токена
if [ -z "$YANDEX_TOKEN" ] && [ -z "$YANDEX_DISK_TOKEN" ]; then
    echo "❌ ОШИБКА: YANDEX_TOKEN не установлен в .env"
    exit 1
fi

# Создаем директорию для логов
mkdir -p logs

# Запускаем индексатор
nohup python3 yadisk_indexer.py > logs/yadisk_indexer.out 2>&1 &

PID=$!
echo $PID > yadisk_indexer.pid

echo "✅ Yandex Disk Indexer запущен (PID: $PID)"
echo "📋 Логи: logs/yadisk_indexer.out и yadisk_indexer.log"
echo ""
echo "Управление:"
echo "  Остановить: kill $PID"
echo "  Статус: ps -p $PID"
echo "  Логи: tail -f logs/yadisk_indexer.out"
