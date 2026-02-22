# Установка custom agent skills в AnythingLLM

Сообщение **"No imported skills found"** означает, что AnythingLLM не видит папки скиллов в своём каталоге хранения.

## Что сделать

1. **Найти каталог хранения AnythingLLM (STORAGE_DIR).**
   - **Docker:** каталог, смонтированный как `STORAGE_LOCATION` (см. [документацию](https://docs.useanything.com/installation-docker/local-docker)).
   - **Локально:** обычно `server/storage` внутри репозитория AnythingLLM.
   - **Desktop:** см. [Where is my data located](https://docs.useanything.com/installation-desktop/storage#where-is-my-data-located).

2. **Создать подкаталог скиллов (если его ещё нет):**
   ```
   STORAGE_DIR/plugins/agent-skills/
   ```

3. **Скопировать весь скилл целиком** (папку с именем как `hubId`):
   ```
   Из репозитория HR_Bot:
   plugins/agent-skills/weeek-manager/   →   STORAGE_DIR/plugins/agent-skills/weeek-manager/
   ```
   Внутри должны быть файлы: `plugin.json`, `handler.js`, при желании `README.md`.

4. **Перезагрузить страницу AnythingLLM** (F5 или обновить вкладку). После этого скилл «Weeeek Manager» должен появиться в списке Custom Skills.

5. В настройках **агента** включить скилл «Weeeek Manager».

6. Задать в окружении AnythingLLM переменную **`WEEEEK_TOKEN`** (или `WEEEK_API_KEY`).

## Проверка

- Имя папки должно **совпадать** с полем `hubId` в `plugin.json` (например `weeek-manager`).
- Путь в итоге: `STORAGE_DIR/plugins/agent-skills/weeek-manager/plugin.json` и `handler.js`.
