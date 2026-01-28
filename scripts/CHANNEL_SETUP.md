# Настройка канала для лидов

## Информация о канале

- **Название**: HRAI_ANovoselova_Лиды
- **Username**: @HRAI_ANovoselova_Leads
- **ID канала**: `-1003862655606`
- **Ссылка**: https://t.me/HRAI_ANovoselova_Leads

## Настройка переменной окружения

Добавьте в ваш `.env` файл или переменные окружения:

```bash
TELEGRAM_LEADS_CHANNEL_ID=-1003862655606
```

## Проверка работы

### Отправить тестовое сообщение "test":

```bash
python scripts/send_test_to_channel.py --channel-id '-1003862655606'
```

Или если переменная окружения установлена:

```bash
python scripts/send_test_to_channel.py
```

### Получить информацию о канале:

```bash
python scripts/get_channel_id.py @HRAI_ANovoselova_Leads
```

## Важно

- Бот @HR2137_bot должен быть добавлен в канал как администратор
- Бот должен иметь права на отправку сообщений
- ID канала начинается с `-100` (это нормально для каналов Telegram)
