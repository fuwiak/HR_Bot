# Dockerfile для Telegram Bot сервиса (по умолчанию)
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
# Используем --prefer-binary для быстрой установки wheel пакетов
# и --timeout для избежания зависаний
RUN pip install --upgrade pip && \
    pip install --prefer-binary --timeout=100 -r requirements.txt

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

# Copy entrypoint script
COPY telegram_bot/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port for Telegram webhook
EXPOSE 8080

# Опциональный запуск тестов перед стартом
ARG RUN_TESTS=false
ENV RUN_TESTS=${RUN_TESTS}

# Используем entrypoint для условного запуска тестов
ENTRYPOINT ["/entrypoint.sh"]
