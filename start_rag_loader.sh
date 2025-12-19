#!/bin/sh
# Запуск загрузчика RAG папки

echo "🚀 Загрузка файлов из /RAG HR-Business-Consultant в Qdrant..."

# Загружаем переменные окружения
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Переменные окружения загружены из .env"
fi

# Проверяем наличие токена
if [ -z "$YANDEX_TOKEN" ]; then
    echo "❌ ОШИБКА: YANDEX_TOKEN не установлен в .env"
    exit 1
fi

# Запускаем загрузчик
echo "📂 Папка: /RAG HR-Business-Consultant"
echo "📦 Коллекция: hr2137_bot_knowledge_base"
echo ""

python3 load_rag_folder.py
