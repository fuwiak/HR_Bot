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

4. При необходимости перезагрузите страницу или завершите сессию (`/exit`) и начните новую.

## Команды (в чате с агентом)

| Действие | Примеры |
|----------|--------|
| Информация о workspace | `weeek info`, `workspace` |
| Список проектов | `проекты`, `list projects` |
| Список задач | `задачи`, `list tasks`, `задачи 123` (123 — ID проекта) |
| Одна задача | `задача 456`, `task 456` |
| Создать задачу | `добавь задачу: 1 \| Купить молоко`, `add task: 1 \| Title` |
| Создать проект | `создай проект: Маркетинг`, `create project: Name` |
| Завершить задачу | `заверши задачу: 456`, `complete task: 456` |
| Возобновить задачу | `возобнови задачу: 456`, `uncomplete task: 456` |
| Удалить задачу | `удали задачу: 456`, `delete task: 456` |
| Справка | любой текст, не совпадающий с командами — выведет список команд |

## Формат «добавить задачу»

- **Добавь задачу:** `ID_проекта | Название задачи`
- Пример: `добавь задачу: 1 | Подготовить отчёт`
- ID проекта можно узнать командой **проекты**.

## Связь с HR_Bot

Этот скилл дублирует функционал Weeeek из Python-бота (Telegram) в виде навыка агента AnythingLLM. Используются те же эндпоинты API: `/tm/projects`, `/tm/tasks`, `/ws`. Токен можно взять тот же, что и для бота (`WEEEEK_TOKEN` в `.env` или Railway), но задать его нужно в окружении **сервера AnythingLLM**, а не только бота.

## Файлы

- `plugin.json` — описание скилла (name, hubId, entry).
- `handler.js` — логика: разбор текста, вызовы API Weeeek, ответы строками.
- `README.md` — эта инструкция.
