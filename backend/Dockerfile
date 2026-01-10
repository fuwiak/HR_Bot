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

# Copy entrypoint script
COPY backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port for backend API
EXPOSE 8081

# Опциональный запуск тестов и миграции услуг перед стартом
ARG RUN_TESTS=false
ENV RUN_TESTS=${RUN_TESTS}
ARG RUN_SERVICES_MIGRATION=false
ENV RUN_SERVICES_MIGRATION=${RUN_SERVICES_MIGRATION}

# Используем entrypoint для условного запуска тестов
ENTRYPOINT ["/entrypoint.sh"]
