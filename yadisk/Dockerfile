# Dockerfile для Yandex Disk Indexer
FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем необходимые файлы
COPY yadisk/ ./yadisk/
COPY services/ ./services/
COPY config.yaml .

# Создаем директорию для логов
RUN mkdir -p logs

# Запускаем индексатор
CMD ["python", "-u", "yadisk/indexer.py"]
