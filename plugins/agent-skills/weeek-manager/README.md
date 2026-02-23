# Weeeek Manager — custom agent skill для AnythingLLM

Управление проектами и задачами в [Weeeek](https://weeek.net) через агента AnythingLLM.

## Требования

- Node.js 18+ (для `fetch`)
- AnythingLLM с поддержкой custom agent skills
- Токен Weeeek API: в окружении AnythingLLM задайте **`WEEEEK_TOKEN`** или **`WEEEK_API_KEY`**
- Опционально: **`WEEEK_API_URL`** (по умолчанию `https://api.weeek.net/public/v1`)

## Установка

1. Скопируйте папку **`weeek-manager`** в каталог скиллов AnythingLLM:
   - **Docker:** `STORAGE_LOCATION/plugins/agent-skills/weeek-manager`
   - **Локально:** `server/storage/plugins/agent-skills/weeek-manager`
   - **Desktop:** в storage по [инструкции](https://docs.useanything.com) создайте `plugins/agent-skills/weeek-manager`

2. Убедитесь, что в окружении AnythingLLM задана переменная **`WEEEEK_TOKEN`** (или `WEEEK_API_KEY`).

3. В UI AnythingLLM включите скилл **«Weeeek Manager»** в настройках агента.

4. **Чтобы агент вызывал скилл, а не отвечал сам:** в AnythingLLM откройте **Workspace → Agent** (или настройки агента) → поле **System Prompt** / **Instructions** и вставьте блок ниже. Тогда при любом сообщении, начинающемся с `weeek`, агент будет вызывать скилл Weeeek Manager, а не отвечать от себя.

5. При необходимости перезагрузите страницу или завершите сессию (`/exit`) и начните новую.

### Готовый System Prompt для агента (скопируйте в AnythingLLM)

```
When the user message starts with "weeek" (three letters e — the Weeeek service name, not "week"), you MUST call the skill "Weeeek Manager" and pass the full user message as the prompt. Return the skill result to the user. Do not answer from your own knowledge and do not correct "weeek" to "week". Examples: "weeek проекты", "weeek задачи", "weeek добавь задачу: 1 | Title" — always invoke Weeeek Manager skill.
```

## Как писать команды (пошагово)

**Все команды начинаются с префикса `weeek`** (три буквы «e» — это название сервиса Weeeek, не слово «week»). С пробелом после: `weeek проекты`.

1. Откройте AnythingLLM → чат с агентом (поле ввода внизу).
2. Введите **одну** фразу из примеров ниже (обязательно с `weeek` в начале).
3. Отправьте сообщение. Агент вызовет скилл и ответит результатом.

Кнопки скилла нажимать не нужно — достаточно текста в чате.

### Примеры — что именно ввести

- Список проектов:
  ```
  weeek проекты
  ```

- Информация о workspace:
  ```
  weeek info
  ```

- Список задач:
  ```
  weeek задачи
  ```
  или по проекту: `weeek задачи 1` (1 — ID проекта из «weeek проекты»).

- Создать задачу (1 — ID проекта, после `|` — название):
  ```
  weeek добавь задачу: 1 | Позвонить клиенту
  ```
  Символ **|** (вертикальная чёрточка): на ПК клавиша с `\`, на Mac — Option+7.

- Создать проект:
  ```
  weeek создай проект: Маркетинг
  ```

- Завершить задачу (456 — ID задачи):
  ```
  weeek заверши задачу: 456
  ```

- Удалить задачу:
  ```
  weeek удали задачу: 456
  ```

- Справка по командам (если забыли формат):
  ```
  weeek
  ```
  или любое сообщение, начинающееся с `weeek` и не совпадающее с командой.

---

## Сводка команд (префикс weeek обязателен)

Команда **`weeek проекты`** вызывает API: **GET** `https://api.weeek.net/public/v1/tm/projects` (ответ: `{ success, projects: [{ id, name, ... }] }`).

| Действие | Что ввести в чат |
|----------|------------------|
| Информация о workspace | `weeek info` |
| Список проектов | `weeek проекты` |
| Список задач | `weeek задачи` или `weeek задачи 1` |
| Одна задача | `weeek задача 456` |
| Создать задачу | `weeek добавь задачу: 1 \| Текст` |
| Создать проект | `weeek создай проект: Название` |
| Завершить задачу | `weeek заверши задачу: 456` |
| Возобновить задачу | `weeek возобнови задачу: 456` |
| Удалить задачу | `weeek удали задачу: 456` |
| Справка | `weeek` |

## Связь с HR_Bot

Этот скилл дублирует функционал Weeeek из Python-бота (Telegram) в виде навыка агента AnythingLLM. Используются те же эндпоинты API: `/tm/projects`, `/tm/tasks`, `/ws`. Токен можно взять тот же, что и для бота (`WEEEEK_TOKEN` в `.env` или Railway), но задать его нужно в окружении **сервера AnythingLLM**, а не только бота.

## Файлы

- `plugin.json` — описание скилла (name, hubId, entry).
- `handler.js` — логика: разбор текста, вызовы API Weeeek, ответы строками.
- `README.md` — эта инструкция.
