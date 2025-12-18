# Use Python 3.11 slim image for smaller size
# Этот Dockerfile используется для локальной разработки через docker-compose
# Для Railway используйте отдельные Dockerfile.telegram, Dockerfile.backend, Dockerfile.frontend

FROM python:3.11-slim

# Set working directory
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
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Expose ports
# 8080 - для Telegram webhook
# 8081 - для веб-интерфейса демонстрации
EXPOSE 8080 8081

# Run both bot and web interface
# Используем start.sh скрипт для запуска обоих сервисов
# Для Railway используйте отдельные Dockerfile для каждого сервиса
CMD ["sh", "start.sh"]



