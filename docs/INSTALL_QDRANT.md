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

### Вариант 3: Qdrant Cloud (для продакшена на Railway) ✅ У ВАС УЖЕ ЕСТЬ

**Ваш кластер уже создан:**
- Endpoint: `https://239a4026-d673-4b8b-bfab-a99c7044e6b1.us-east4-0.gcp.cloud.qdrant.io`

**Для Railway:**

1. Получите API ключ из панели Qdrant Cloud: https://cloud.qdrant.io
2. Добавьте переменные в Railway:
   ```
   QDRANT_URL=https://239a4026-d673-4b8b-bfab-a99c7044e6b1.us-east4-0.gcp.cloud.qdrant.io
   QDRANT_API_KEY=ваш_api_ключ
   ```

**Подробная инструкция**: см. `QDRANT_RAILWAY_SETUP.md`

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

