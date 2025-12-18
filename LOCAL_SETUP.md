# Локальная настройка и запуск

## Требования

- Python 3.11+
- pip
- Docker и Docker Compose (для Qdrant)
- Git

## Быстрый старт

### 1. Клонирование и установка зависимостей

```bash
# Установка зависимостей
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
# Обязательные
TELEGRAM_TOKEN=your_telegram_bot_token
OPENROUTER_API_KEY=your_openrouter_api_key

# Опционально (для полного функционала)
GIGACHAT_API_KEY=your_gigachat_api_key
QDRANT_URL=http://localhost:6333
WEEEEK_TOKEN=e9b78361-0705-408a-af49-ca4300b5cf1b
YANDEX_EMAIL=your_email@yandex.ru
YANDEX_PASSWORD=your_app_password
HRTIME_API_KEY=your_hrtime_api_key

# Подробнее см. ENV_VARIABLES.md
```

### 3. Запуск Qdrant (векторная БД)

#### Вариант A: Docker Compose (рекомендуется)

```bash
# Запустить только Qdrant
docker-compose up -d qdrant

# Или запустить всё (бот + Qdrant)
docker-compose up --build
```

#### Вариант B: Docker напрямую

```bash
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### 4. Индексация базы знаний (опционально)

Если у вас есть документы для RAG базы знаний:

```bash
# Индексация одного файла
python index_knowledge_base.py /path/to/document.docx --category кейсы

# Индексация директории
python index_knowledge_base.py /path/to/documents --category методики --recursive
```

### 5. Запуск бота

#### Вариант A: Скрипт запуска (рекомендуется)

```bash
./run_local.sh
```

Скрипт запустит:
- Telegram бота (порт 8080 для webhook, если используется)
- Веб-интерфейс (http://localhost:8081)

#### Вариант B: Запуск отдельно

```bash
# Терминал 1: Telegram бот
python app.py

# Терминал 2: Веб-интерфейс
python web_interface.py
```

#### Вариант C: Docker Compose

```bash
docker-compose up --build
```

## Проверка работы

### Telegram бот

1. Найдите вашего бота в Telegram
2. Отправьте команду `/start`
3. Попробуйте команды:
   - `/rag_search подбор персонала` - поиск в RAG базе
   - `/rag_stats` - статистика базы знаний
   - `/demo_proposal нужна помощь с HR` - генерация КП

### Веб-интерфейс

Откройте в браузере: http://localhost:8081

Доступные функции:
- Отправка тестового email
- Генерация коммерческого предложения
- Поиск в RAG базе знаний
- Просмотр статистики и документов
- Визуализация архитектуры

## Режимы работы

### Polling (для локальной разработки)

По умолчанию используется polling режим:

```bash
USE_WEBHOOK=false python app.py
```

### Webhook (для production)

Для webhook нужен публичный URL:

```bash
USE_WEBHOOK=true \
WEBHOOK_URL=https://your-domain.com \
python app.py
```

## Устранение проблем

### Qdrant не запускается

```bash
# Проверить, запущен ли Qdrant
curl http://localhost:6333/collections

# Посмотреть логи
docker-compose logs qdrant
```

### Ошибки импорта модулей

```bash
# Переустановить зависимости
pip install -r requirements.txt --upgrade
```

### Ошибки с моделями Qwen

Модели автоматически скачиваются при первом использовании. 
Убедитесь, что есть достаточно места на диске (несколько GB).

### Порт уже занят

Измените порты в `.env`:
```bash
PORT=8080
WEB_INTERFACE_PORT=8082
```

## Разработка

### Структура проекта

```
HR_Bot/
├── app.py                    # Основной файл Telegram бота
├── web_interface.py          # Веб-интерфейс (FastAPI)
├── llm_helper.py            # Модуль для LLM (DeepSeek/GigaChat)
├── qdrant_helper.py         # Модуль для RAG (Qdrant + Qwen)
├── lead_processor.py        # Обработка лидов
├── email_helper.py          # Работа с email
├── hrtime_helper.py         # Интеграция HR Time
├── weeek_helper.py          # Интеграция WEEEK
├── summary_helper.py        # Суммаризация
├── index_knowledge_base.py  # Скрипт индексации документов
├── templates/               # HTML шаблоны для веб-интерфейса
├── requirements.txt         # Python зависимости
├── Dockerfile               # Docker образ
├── docker-compose.yml       # Docker Compose конфигурация
└── .env                     # Переменные окружения (не в git)
```

### Логирование

Логи выводятся в консоль. Для детального логирования:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Тестирование модулей

```bash
# Тест LLM
python -c "from llm_helper import generate_with_fallback; import asyncio; print(asyncio.run(generate_with_fallback([{'role': 'user', 'content': 'Привет'}])))"

# Тест Qdrant
python -c "from qdrant_helper import get_qdrant_client; print(get_qdrant_client())"
```

## Следующие шаги

1. Индексируйте ваши документы в RAG базу знаний
2. Настройте интеграции (WEEEK, Email, HR Time)
3. Протестируйте все команды бота
4. Настройте веб-интерфейс для демонстрации










