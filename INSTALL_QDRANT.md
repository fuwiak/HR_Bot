# Установка Qdrant

## Проблема: "Qdrant клиент или модель не доступны"

Если вы видите эту ошибку, выполните следующие шаги:

## 1. Установите Python библиотеки

```bash
pip install qdrant-client sentence-transformers
```

Или если используете requirements.txt:
```bash
pip install -r requirements.txt
```

## 2. Запустите Qdrant сервер

### Вариант 1: Docker (рекомендуется)

```bash
docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant
```

### Вариант 2: Docker Compose

```bash
docker-compose up -d qdrant
```

### Вариант 3: Qdrant Cloud (для продакшена)

1. Зарегистрируйтесь на https://cloud.qdrant.io
2. Создайте кластер
3. Получите URL и API ключ
4. Установите переменные окружения:
   ```bash
   export QDRANT_URL=https://your-cluster.qdrant.io
   export QDRANT_API_KEY=your_api_key
   ```

## 3. Проверьте подключение

```bash
curl http://localhost:6333/collections
```

Если сервер работает, вы увидите список коллекций.

## 4. Перезапустите бота

После установки библиотек и запуска Qdrant сервера, перезапустите бота.

В логах должно появиться:
```
✅ Qdrant клиент успешно подключен: http://localhost:6333
✅ Модель для эмбеддингов загружена
✅ Индексировано X услуг в Qdrant
```

## Важно

- Первая загрузка модели может занять 1-2 минуты (модель скачивается из интернета)
- Qdrant должен быть доступен по адресу `http://localhost:6333` (или указанному в `QDRANT_URL`)
- Если используете Docker Compose, Qdrant будет доступен по адресу `http://qdrant:6333` внутри сети Docker

