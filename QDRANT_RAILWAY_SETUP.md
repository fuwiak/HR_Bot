# Настройка Qdrant Cloud для Railway

## Ваш Qdrant Cloud кластер

У вас уже создан кластер Qdrant Cloud:

- **Endpoint**: `https://239a4026-d673-4b8b-bfab-a99c7044e6b1.us-east4-0.gcp.cloud.qdrant.io`
- **Cluster ID**: `239a4026-d673-4b8b-bfab-a99c7044e6b1`
- **Provider**: GCP (us-east4)
- **Version**: v1.16.2

## Быстрая настройка для Railway

### Шаг 1: Получите API ключ

1. Войдите в панель управления Qdrant Cloud: https://cloud.qdrant.io
2. Выберите ваш кластер
3. Перейдите в раздел **"API Keys"** (в боковом меню или настройках кластера)
4. Нажмите **"Create API Key"** или используйте существующий
5. **Скопируйте API ключ** - он понадобится в следующем шаге
   - ⚠️ **Важно**: Сохраните ключ, он показывается только один раз!

### Шаг 2: Добавьте переменные окружения в Railway

1. Откройте проект в Railway: https://railway.app
2. Выберите ваш сервис с ботом
3. Перейдите во вкладку **"Variables"**
4. Нажмите **"+ New Variable"**
5. Добавьте следующие переменные:

   **Переменная 1:**
   - **Key**: `QDRANT_URL`
   - **Value**: `https://239a4026-d673-4b8b-bfab-a99c7044e6b1.us-east4-0.gcp.cloud.qdrant.io`

   **Переменная 2:**
   - **Key**: `QDRANT_API_KEY`
   - **Value**: `ваш_api_ключ_из_шага_1`

6. Railway автоматически перезапустит сервис после добавления переменных

### Шаг 3: Проверка

После перезапуска проверьте логи Railway. Должно появиться:

```
✅ Qdrant клиент успешно подключен: https://239a4026-d673-4b8b-bfab-a99c7044e6b1.us-east4-0.gcp.cloud.qdrant.io
✅ Модель для эмбеддингов загружена
✅ Создана коллекция 'romanbot_services' в Qdrant
✅ Индексировано X услуг в Qdrant
```

## Альтернатива: Railway CLI

Если используете Railway CLI:

```bash
railway variables set QDRANT_URL=https://239a4026-d673-4b8b-bfab-a99c7044e6b1.us-east4-0.gcp.cloud.qdrant.io
railway variables set QDRANT_API_KEY=ваш_api_ключ
```

## Проверка подключения

После настройки вы можете проверить подключение через API:

```bash
curl -H "api-key: ваш_api_ключ" \
  https://239a4026-d673-4b8b-bfab-a99c7044e6b1.us-east4-0.gcp.cloud.qdrant.io/collections
```

Должен вернуться список коллекций (JSON).

## Безопасность

⚠️ **Важно:**
- Никогда не коммитьте API ключ в репозиторий
- API ключ должен быть только в переменных окружения Railway
- Если ключ скомпрометирован, создайте новый в панели Qdrant Cloud

## Troubleshooting

### Ошибка: "Qdrant клиент не доступен"
- Проверьте, что `QDRANT_URL` указан правильно (полный URL с https://)
- Проверьте, что `QDRANT_API_KEY` установлен
- Убедитесь, что API ключ валидный (можно проверить через curl выше)

### Ошибка: "403 Forbidden" или "Unauthorized"
- API ключ неверный или истек
- Создайте новый API ключ в панели Qdrant Cloud

### Ошибка: "Connection timeout"
- Проверьте, что кластер активен в панели Qdrant Cloud
- Убедитесь, что URL правильный (с https://, без порта)





