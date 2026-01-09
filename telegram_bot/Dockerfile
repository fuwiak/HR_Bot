# Dockerfile для Telegram Bot сервиса
FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY telegram_bot/ ./telegram_bot/
COPY backend/ ./backend/
COPY services/ ./services/
COPY tests/ ./tests/
COPY scripts/ ./scripts/
COPY config.yaml .
COPY config/ ./config/
COPY templates/ ./templates/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Expose port for Telegram webhook
EXPOSE 8080

# Опциональный запуск тестов перед стартом
ENV RUN_TESTS=${RUN_TESTS:-false}

# Создаем entrypoint скрипт для запуска миграций, инициализации Qdrant и условного запуска тестов
RUN echo '#!/bin/sh\n\
set -e\n\
echo "🔄 Запуск миграций Alembic..."\n\
if alembic upgrade head; then\n\
    echo "✅ Миграции успешно применены"\n\
else\n\
    echo "❌ Ошибка применения миграций!"\n\
    exit 1\n\
fi\n\
echo "🔧 Инициализация Qdrant коллекции..."\n\
python scripts/init_qdrant.py || echo "⚠️ Инициализация Qdrant завершилась с ошибками, но продолжаем запуск"\n\
if [ "$RUN_TESTS" = "true" ]; then\n\
    echo "🧪 Запуск тестов перед стартом приложения..."\n\
    python tests/run_tests.py || echo "⚠️ Тесты завершились с ошибками, но продолжаем запуск"\n\
fi\n\
exec python -u telegram_bot/app.py\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Используем entrypoint для условного запуска тестов
ENTRYPOINT ["/entrypoint.sh"]
