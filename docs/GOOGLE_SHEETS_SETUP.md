# Настройка Google Sheets для бота

## Требования

1. Google аккаунт с доступом к таблице
2. Service Account для API доступа
3. Настроенный Spreadsheet с листами "Ценник" и "Запись"

## Шаг 1: Создание Service Account

1. Перейдите на https://console.cloud.google.com
2. Создайте новый проект или выберите существующий
3. Включите Google Sheets API:
   - Перейдите в "APIs & Services" > "Library"
   - Найдите "Google Sheets API" и включите
4. Создайте Service Account:
   - Перейдите в "APIs & Services" > "Credentials"
   - Нажмите "Create Credentials" > "Service Account"
   - Заполните имя (например: "romanbot-service")
   - Нажмите "Create and Continue"
   - Роль: "Editor" или оставьте пустым
   - Нажмите "Done"
5. Создайте ключ:
   - Откройте созданный Service Account
   - Перейдите на вкладку "Keys"
   - Нажмите "Add Key" > "Create new key"
   - Выберите "JSON" формат
   - Скачайте файл и сохраните как `credentials.json`

## Шаг 2: Настройка доступа к таблице

1. Откройте вашу Google таблицу:
   https://docs.google.com/spreadsheets/d/1NF25EWqRxjdNTKk4VFVAYZGIOlVFfaktpEvvj1bRXKU

2. Получите email Service Account из файла `credentials.json` (поле `client_email`)

3. Поделитесь таблицей с этим email:
   - Нажмите "Share" в таблице
   - Добавьте email Service Account (например: `romanbot-service@project-id.iam.gserviceaccount.com`)
   - Права: "Editor"
   - Нажмите "Send"

## Шаг 3: Структура таблицы

### Лист "Ценник"

Таблица должна иметь следующие колонки:
- A: Тип услуги / Отдел (может быть заголовок секции)
- B: Услуга название
- C: Мастер 1
- D: Мастер 2
- E: Цена
- F: Время оказания (в мин.)
- G: Название доп. услуги (если есть)

### Лист "Запись" (создается автоматически)

Бот создаст лист "Запись" автоматически при первой записи. Колонки:
- A: Дата создания
- B: ID записи
- C: Дата
- D: Время
- E: Мастер
- F: Услуга
- G: Имя клиента
- H: Телефон
- I: Цена
- J: Статус
- K: Комментарий

## Шаг 4: Настройка переменных окружения

### Локальная разработка:

Добавьте в `.env` файл:

```bash
GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=1NF25EWqRxjdNTKk4VFVAYZGIOlVFfaktpEvvj1bRXKU
```

Поместите `credentials.json` в корень проекта рядом с `app.py`

### На Railway (рекомендуемый способ):

1. **Откройте файл `credentials.json`** и скопируйте все его содержимое
2. **В Railway Dashboard**:
   - Перейдите в ваш проект → Variables
   - Добавьте новую переменную:
     - **Имя**: `GOOGLE_SHEETS_CREDENTIALS_JSON`
     - **Значение**: Вставьте содержимое `credentials.json` целиком (весь JSON)
   
   Пример значения:
   ```json
   {
     "type": "service_account",
     "project_id": "your-project",
     "private_key_id": "...",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
     ...
   }
   ```

3. **Spreadsheet ID** уже установлен по умолчанию, но можно переопределить:
   - Переменная: `GOOGLE_SHEETS_SPREADSHEET_ID`
   - Значение: `1NF25EWqRxjdNTKk4VFVAYZGIOlVFfaktpEvvj1bRXKU`

**Примечание**: Бот автоматически определит, использовать ли JSON из переменной или файл. Приоритет у JSON переменной (для Railway).

## Проверка работы

После настройки бот будет:
- ✅ Читать услуги из листа "Ценник"
- ✅ Отслеживать изменения (кэш обновляется каждые 5 минут)
- ✅ Записывать новые записи в лист "Запись"
- ✅ Проверять доступность времени перед записью

## Кэширование

Для оптимизации бот кэширует данные об услугах на 5 минут. При необходимости можно принудительно обновить кэш, перезапустив бота.

## Отслеживание изменений

Бот автоматически обновляет данные из Google Sheets при каждом запросе (если кэш устарел). Для отслеживания в реальном времени можно:
1. Настроить Google Apps Script webhook
2. Уменьшить время кэширования (изменить `CACHE_TIMEOUT` в `google_sheets_helper.py`)

