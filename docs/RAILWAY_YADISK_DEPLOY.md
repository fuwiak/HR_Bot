# 🚂 Railway: Деплой Yandex Disk Indexer

## 🎯 Цель

Развернуть Yandex Disk Indexer как отдельный сервис на Railway, который будет работать в фоне и автоматически индексировать файлы с Яндекс.Диска в Qdrant Cloud.

---

## 📋 Подготовка

### 1. Файлы уже готовы:

- ✅ `Dockerfile.yadisk` - Docker образ для индексатора
- ✅ `yadisk_indexer.py` - основной скрипт
- ✅ `yandex_disk_helper.py` - модуль работы с Яндекс.Диском
- ✅ `.railway/yadisk-indexer.toml` - конфигурация Railway (нужно создать)

---

## 🚀 Вариант 1: Railway Dashboard (GUI)

### Шаг 1: Создать новый сервис

1. Откройте Railway Dashboard
2. Выберите ваш проект
3. Нажмите `+ New Service`
4. Выберите `GitHub Repo`
5. Выберите репозиторий `HR_Bot`

### Шаг 2: Настроить сервис

1. **Service Name:** `yadisk-indexer`

2. **Settings → Build:**
   - Builder: `Dockerfile`
   - Dockerfile Path: `Dockerfile.yadisk`

3. **Settings → Deploy:**
   - Start Command: `python -u yadisk_indexer.py`
   - Restart Policy: `On Failure`
   - Max Retries: `10`

### Шаг 3: Добавить переменные окружения

В разделе `Variables` добавьте:

```env
# Обязательные
YANDEX_TOKEN=your_yandex_token_here
QDRANT_URL=https://your-cluster.aws.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_key
OPENAI_API_KEY=your_openai_key

# Опциональные
YADISK_WATCH_FOLDERS=/
YADISK_SCAN_INTERVAL=300
YADISK_MAX_FILE_SIZE=50
QDRANT_COLLECTION=hr_knowledge_base
EMBEDDING_DIMENSION=1536
TARGET_DIMENSION=1536
```

### Шаг 4: Deploy

1. Нажмите `Deploy`
2. Дождитесь завершения сборки
3. Проверьте логи

---

## 🚀 Вариант 2: Railway CLI

### Шаг 1: Создать конфигурацию

Создайте файл `.railway/yadisk-indexer.toml`:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile.yadisk"

[deploy]
startCommand = "python -u yadisk_indexer.py"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

### Шаг 2: Создать и развернуть сервис

```bash
# 1. Создать сервис
railway service create yadisk-indexer

# 2. Переключиться на сервис
railway service use yadisk-indexer

# 3. Добавить переменные окружения
railway variables set YANDEX_TOKEN="your_yandex_token_here"
railway variables set QDRANT_URL="https://your-cluster.aws.cloud.qdrant.io"
railway variables set QDRANT_API_KEY="your_qdrant_key"
railway variables set OPENAI_API_KEY="your_openai_key"
railway variables set YADISK_WATCH_FOLDERS="/"
railway variables set YADISK_SCAN_INTERVAL="300"
railway variables set QDRANT_COLLECTION="hr_knowledge_base"

# 4. Развернуть
railway up
```

---

## 📊 Проверка работы

### Просмотр логов

```bash
# CLI
railway logs

# Или в Dashboard:
Service → Deployments → Latest → View Logs
```

### Ожидаемый вывод

```log
2024-12-19 11:00:00 [INFO] 🚀 Запуск Yandex Disk Indexer
2024-12-19 11:00:00 [INFO] 📂 Папки для мониторинга: ['/']
2024-12-19 11:00:00 [INFO] ⏱️ Интервал сканирования: 300 секунд
2024-12-19 11:00:00 [INFO] ============================================================
2024-12-19 11:00:00 [INFO] 🔄 ИТЕРАЦИЯ #1 - 2024-12-19 11:00:00
2024-12-19 11:00:00 [INFO] ============================================================
2024-12-19 11:00:01 [INFO] 🔍 Сканирование папки: /
2024-12-19 11:00:02 [INFO] ✅ Найдено 5 файлов для обработки в /
2024-12-19 11:00:03 [INFO] 📥 Скачивание: document.pdf
2024-12-19 11:00:05 [INFO] 🎉 Файл document.pdf успешно проиндексирован (4 точек)
...
2024-12-19 11:05:00 [INFO] ✅ Итерация #1 завершена
2024-12-19 11:05:00 [INFO] ✅ Обработано файлов: 5
2024-12-19 11:05:00 [INFO] ⏳ Следующее сканирование через 300 секунд...
```

---

## 🎛️ Настройка параметров

### Изменить интервал сканирования

```bash
# 1 минута (быстро)
railway variables set YADISK_SCAN_INTERVAL="60"

# 10 минут (оптимально)
railway variables set YADISK_SCAN_INTERVAL="600"

# 1 час (редко)
railway variables set YADISK_SCAN_INTERVAL="3600"
```

### Изменить папки для мониторинга

```bash
# Только конкретные папки
railway variables set YADISK_WATCH_FOLDERS="/Документы,/КП,/Договоры"

# Вся корневая папка
railway variables set YADISK_WATCH_FOLDERS="/"
```

### Изменить максимальный размер файла

```bash
# 100 МБ
railway variables set YADISK_MAX_FILE_SIZE="100"

# 10 МБ (для экономии)
railway variables set YADISK_MAX_FILE_SIZE="10"
```

---

## 🔧 Управление сервисом

### Перезапуск

```bash
# CLI
railway restart

# Dashboard:
Service → Settings → Restart Service
```

### Остановка

```bash
# CLI
railway down

# Dashboard:
Service → Settings → Pause Service
```

### Удаление

```bash
# CLI
railway service delete yadisk-indexer

# Dashboard:
Service → Settings → Delete Service
```

---

## 💰 Стоимость

### Railway Pricing

- **Starter Plan:** $5/месяц
  - $5 кредитов включено
  - ~500 часов работы одного сервиса

- **Developer Plan:** $20/месяц
  - $20 кредитов включено
  - ~2000 часов работы

### Оптимизация затрат

1. **Увеличьте интервал сканирования:**
   ```env
   YADISK_SCAN_INTERVAL=3600  # 1 час вместо 5 минут
   ```

2. **Используйте sleep режим:**
   Остановите индексатор ночью через cron или Railway scheduler

3. **Локальный запуск:**
   Запустите индексатор на своем сервере:
   ```bash
   ./start_yadisk_indexer.sh
   ```

---

## 🐛 Решение проблем

### Проблема 1: Build Failed

```log
Error: Could not find Dockerfile.yadisk
```

**Решение:**
- Проверьте путь: `Dockerfile.yadisk` должен быть в корне
- Убедитесь, что файл закоммичен в Git

---

### Проблема 2: Container Crashed

```log
Error: YANDEX_TOKEN not set
```

**Решение:**
- Добавьте переменную окружения в Railway Dashboard
- Проверьте: `railway variables`

---

### Проблема 3: Out of Memory

```log
Error: Container exceeded memory limit
```

**Решение:**
- Уменьшите `YADISK_MAX_FILE_SIZE`
- Уменьшите `batch_size` в коде
- Увеличьте RAM в Railway (платно)

---

### Проблема 4: Too many requests

```log
Error: Rate limit exceeded
```

**Решение:**
- Увеличьте `YADISK_SCAN_INTERVAL`
- Добавьте задержки между файлами в коде

---

## 📈 Мониторинг

### Metrics в Railway

Dashboard → Service → Metrics покажет:
- CPU usage
- Memory usage
- Network traffic

### Логи в реальном времени

```bash
# CLI
railway logs --follow

# Dashboard:
Service → Logs → Enable "Follow logs"
```

### Алерты

Настройте уведомления в Railway:
1. Settings → Notifications
2. Добавьте Webhook или Email
3. Выберите события: `Deploy Failed`, `Service Crashed`

---

## ✅ Чек-лист деплоя

- [ ] Создан `Dockerfile.yadisk`
- [ ] Создан `.railway/yadisk-indexer.toml`
- [ ] Добавлены переменные окружения в Railway
- [ ] Сервис создан и развернут
- [ ] Логи показывают успешный запуск
- [ ] Первая итерация индексации завершена
- [ ] Файлы появились в Qdrant Cloud
- [ ] Настроены алерты (опционально)

---

## 🎉 Готово!

**Индексатор развернут на Railway и работает в фоне! 🚀**

### Что дальше?

1. ✅ Мониторьте логи первые 30 минут
2. ✅ Проверьте Qdrant Cloud (должны появиться точки)
3. ✅ Протестируйте поиск в боте: `/search [запрос]`
4. ✅ Настройте оптимальный интервал сканирования

**Все файлы с Яндекс.Диска теперь доступны для RAG! 🎉**
