# Быстрый старт

## Локальная разработка

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка .env

Скопируйте `.env.example` (если есть) или создайте `.env` с минимумом:

```bash
TELEGRAM_TOKEN=your_token
OPENROUTER_API_KEY=your_key
QDRANT_URL=http://localhost:6333
```

### 3. Запуск Qdrant

```bash
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### 4. Запуск бота

```bash
./run_local.sh
```

Или через Docker Compose:

```bash
docker-compose up --build
```

**Готово!** Бот работает на Telegram, веб-интерфейс на http://localhost:8081

---

## Развертывание в Railway

### 1. Подготовка

- Код в Git репозитории
- Все секреты готовы

### 2. Создание проекта

1. Railway.app → New Project → Deploy from GitHub
2. Выберите репозиторий

### 3. Настройка переменных

Railway → Variables → добавьте все переменные из `ENV_VARIABLES.md`

**Минимум:**
```
TELEGRAM_TOKEN=...
OPENROUTER_API_KEY=...
QDRANT_URL=...
QDRANT_API_KEY=...
```

### 4. Деплой

Railway автоматически соберет и развернет приложение.

**Готово!** Бот работает в production.

---

## Команды бота

- `/start` - старт
- `/rag_search [запрос]` - поиск в RAG базе
- `/rag_stats` - статистика базы знаний
- `/rag_docs` - список документов
- `/demo_proposal [запрос]` - генерация КП
- `/summary [проект]` - суммаризация проекта

---

## Веб-интерфейс

Откройте: http://localhost:8081 (локально) или Railway URL:8081

Функции:
- Демонстрация email
- Генерация КП
- Поиск в RAG
- Статистика базы знаний
- Архитектура системы

---

## Документация

- `LOCAL_SETUP.md` - детальная настройка для локальной разработки
- `RAILWAY_SETUP.md` - детальная настройка для Railway
- `ENV_VARIABLES.md` - все переменные окружения

---

## Troubleshooting

**Qdrant недоступен?**
```bash
docker ps | grep qdrant
curl http://localhost:6333/collections
```

**Бот не отвечает?**
- Проверьте `TELEGRAM_TOKEN`
- Проверьте логи: `docker-compose logs bot`

**Веб-интерфейс не открывается?**
- Проверьте порт 8081
- Проверьте переменную `WEB_INTERFACE_PORT`










