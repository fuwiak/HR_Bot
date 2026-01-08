# Настройка WEEEEK_TOKEN

Инструкция по добавлению токена Weeek API в проект.

## Токен

```
WEEEEK_TOKEN=e9b78361-0705-408a-af49-ca4300b5cf1b
```

## Документация API

- **Документация Weeek API**: https://developers.weeek.net/api/workspace
- **Получение токена**: API section настроек workspace в Weeek

## Добавление в локальный .env файл

Создайте или отредактируйте файл `.env` в корне проекта:

```bash
# Добавьте эту строку в ваш .env файл
WEEEEK_TOKEN=e9b78361-0705-408a-af49-ca4300b5cf1b
```

## Добавление в Railway Variables

### Через Railway Dashboard:

1. Перейдите в ваш проект на Railway: https://railway.app
2. Выберите сервис (service)
3. Перейдите во вкладку **"Variables"**
4. Нажмите **"New Variable"**
5. Добавьте:
   - **Variable Name**: `WEEEEK_TOKEN`
   - **Value**: `e9b78361-0705-408a-af49-ca4300b5cf1b`
6. Нажмите **"Add"**
7. Railway автоматически перезапустит сервис

### Через Railway CLI:

```bash
railway variables set WEEEEK_TOKEN=e9b78361-0705-408a-af49-ca4300b5cf1b
```

## Проверка

После добавления переменной, проверьте логи бота. Интеграция с Weeek должна работать автоматически.

Если есть ошибки, проверьте:
1. Правильность токена
2. Что токен добавлен в переменные окружения (Railway или .env)
3. Логи бота на наличие ошибок подключения к Weeek API

## Использование в коде

Токен автоматически используется в `weeek_helper.py`:

```python
# Код поддерживает оба варианта для обратной совместимости:
WEEEK_API_KEY = os.getenv("WEEEEK_TOKEN") or os.getenv("WEEEK_API_KEY")
```

Токен используется в заголовке `Authorization: Bearer {token}` для всех запросов к Weeek API.

## Примечание

- Старое имя переменной `WEEEK_API_KEY` также поддерживается для обратной совместимости
- Но рекомендуется использовать новое имя `WEEEEK_TOKEN` как указано в документации


