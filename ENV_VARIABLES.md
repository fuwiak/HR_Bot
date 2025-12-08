# Environment Variables Reference

Список необходимых переменных окружения для RomanBot.

## Обязательные переменные

### Telegram Bot Token
```
TELEGRAM_TOKEN=your_telegram_bot_token_here
```
- Получить у @BotFather в Telegram
- Также поддерживается старое имя `TELEGRAM_BOT_TOKEN` для обратной совместимости

### OpenRouter API Key
```
OPENROUTER_API_KEY=your_openrouter_api_key_here
```
- Получить на https://openrouter.ai
- Используется для генерации ответов через модель Grok

### OpenRouter API URL (опционально)
```
OPENROUTER_API_URL=https://openrouter.ai/api/v1/chat/completions
```
- URL по умолчанию, можно не указывать
- Если используется другой эндпоинт - укажите его

## Опциональные переменные (Google Sheets)

### Google Sheets Credentials (выберите один способ)

#### Способ 1: JSON из переменной окружения (рекомендуется для Railway)
```
GOOGLE_SHEETS_CREDENTIALS_JSON={"type":"service_account","project_id":"...","private_key":"..."}
```
- Содержимое файла `credentials.json` в виде JSON строки
- Удобно для Railway и других облачных платформ
- Просто скопируйте весь JSON из `credentials.json` и вставьте в переменную

#### Способ 2: Путь к файлу (для локальной разработки)
```
GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials.json
```
- Путь к файлу с credentials для Google Sheets API
- Используется если `GOOGLE_SHEETS_CREDENTIALS_JSON` не указан

**Приоритет**: Если указаны обе переменные, используется `GOOGLE_SHEETS_CREDENTIALS_JSON`

### Google Sheets Spreadsheet ID
```
GOOGLE_SHEETS_SPREADSHEET_ID=1NF25EWqRxjdNTKk4VFVAYZGIOlVFfaktpEvvj1bRXKU
```
- ID Google таблицы (установлен по умолчанию из вашей ссылки)
- Лист "Ценник" используется для чтения услуг
- Лист "Запись" используется для записи записей (создается автоматически)

**Подробная инструкция**: см. `GOOGLE_SHEETS_SETUP.md`

## Установка переменных в Railway

1. Перейдите в дашборд проекта Railway
2. Выберите сервис
3. Перейдите во вкладку "Variables"
4. Нажмите "New Variable"
5. Добавьте каждую переменную с её значением
6. Railway автоматически перезапустит сервис

## Установка переменных локально

Создайте файл `.env` в корне проекта:

```bash
TELEGRAM_TOKEN=your_telegram_bot_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_API_URL=https://openrouter.ai/api/v1/chat/completions

# Опционально (для Google Sheets):
GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
```

**Важно:** Никогда не коммитьте файлы `.env` в репозиторий!

## Проверка

После установки переменных, бот проверит их при запуске. Если какая-то переменная отсутствует, вы увидите сообщение об ошибке.

## Placeholder режим

Если Google Sheets не настроены, бот будет работать в placeholder режиме:
- Данные хранятся в памяти
- Записи не сохраняются между перезапусками
- Подходит для тестирования


