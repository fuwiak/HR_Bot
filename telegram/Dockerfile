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
COPY telegram/ ./telegram/
COPY backend/ ./backend/
COPY services/ ./services/
COPY config.yaml .
COPY templates/ ./templates/ 2>/dev/null || true

# Expose port for Telegram webhook
EXPOSE 8080

# Опциональный запуск тестов перед стартом
ENV RUN_TESTS=${RUN_TESTS:-false}

# Создаем entrypoint скрипт для условного запуска тестов
RUN echo '#!/bin/sh\n\
if [ "$RUN_TESTS" = "true" ]; then\n\
    echo "🧪 Запуск тестов перед стартом приложения..."\n\
    python run_tests.py || echo "⚠️ Тесты завершились с ошибками, но продолжаем запуск"\n\
fi\n\
exec python -u telegram/app.py\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Используем entrypoint для условного запуска тестов
ENTRYPOINT ["/entrypoint.sh"]
