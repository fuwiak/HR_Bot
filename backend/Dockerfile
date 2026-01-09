# Dockerfile для Backend API сервиса
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
COPY backend/ ./backend/
COPY services/ ./services/
COPY tests/ ./tests/
COPY scripts/ ./scripts/
COPY config.yaml .
COPY config/ ./config/
COPY templates/ ./templates/
COPY dashboard_static/ ./dashboard_static/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Expose port for backend API
EXPOSE 8081

# Опциональный запуск тестов и миграции услуг перед стартом
ENV RUN_TESTS=${RUN_TESTS:-false}
ENV RUN_SERVICES_MIGRATION=${RUN_SERVICES_MIGRATION:-false}

# Создаем entrypoint скрипт для запуска миграций, инициализации Qdrant и тестов
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
if [ "$RUN_SERVICES_MIGRATION" = "true" ]; then\n\
    echo "📦 Запуск миграции услуг в RAG коллекцию..."\n\
    python scripts/migrate_services_to_rag.py || echo "⚠️ Миграция услуг завершилась с ошибками, но продолжаем запуск"\n\
fi\n\
if [ "$RUN_TESTS" = "true" ]; then\n\
    echo "🧪 Запуск тестов перед стартом приложения..."\n\
    python tests/run_tests.py || echo "⚠️ Тесты завершились с ошибками, но продолжаем запуск"\n\
fi\n\
exec python -u backend/web_interface.py\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Используем entrypoint для запуска миграций и условного запуска тестов
ENTRYPOINT ["/entrypoint.sh"]
