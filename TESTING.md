# Руководство по тестированию

Документация по запуску и написанию тестов для HR2137 Bot.

## Структура тестов

Проект содержит три набора тестов:

1. **test_scenario_workflows.py** - Тесты бизнес-логики всех 4 сценариев
2. **test_telegram_integration.py** - Тесты интеграции через Telegram бота (async проверки)
3. **test_integration_full.py** - Полные end-to-end интеграционные тесты

## Установка зависимостей для тестирования

```bash
pip install -r requirements.txt
```

Или отдельно:
```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

## Запуск тестов

### Все тесты
```bash
pytest
```

### С подробным выводом
```bash
pytest -v -s
```

### Конкретный файл
```bash
pytest test_scenario_workflows.py -v
pytest test_telegram_integration.py -v
pytest test_integration_full.py -v
```

### Конкретный тест
```bash
pytest test_scenario_workflows.py::test_scenario1_warm_lead_workflow -v
pytest test_telegram_integration.py::test_bot_is_async -v
```

### С покрытием кода
```bash
pytest --cov=scenario_workflows --cov=integrate_scenarios --cov-report=html
```

Откройте `htmlcov/index.html` для просмотра отчета.

## Что проверяют тесты

### test_scenario_workflows.py

- ✅ **Сценарий 1**: Обработка заказов HR Time (теплые и холодные лиды)
- ✅ **Сценарий 2**: Обработка email с подтверждением и без
- ✅ **Сценарий 3**: Обработка Telegram лидов (теплые и холодные)
- ✅ **Сценарий 4**: Мониторинг дедлайнов и суммаризация проектов
- ✅ Интеграционные тесты полного workflow

### test_telegram_integration.py

- ✅ Проверка что все функции используют async
- ✅ Проверка уведомлений через Telegram (Сценарий 1)
- ✅ Проверка подтверждений через Telegram (Сценарий 2)
- ✅ Проверка обработки лидов через Telegram (Сценарий 3)
- ✅ Проверка напоминаний через Telegram (Сценарий 4)
- ✅ Проверка параллельной обработки запросов
- ✅ Проверка что команды бота async

### test_integration_full.py

- ✅ End-to-end тест HR Time → Telegram
- ✅ End-to-end тест Email → Telegram Approval → Send
- ✅ End-to-end тест Telegram → WEEEK → Notification
- ✅ Проверка параллельной работы всех сценариев

## Проверка async функциональности

Все тесты проверяют, что:

1. **Бот использует async**: `Application.builder().concurrent_updates(True)`
2. **Все handlers async**: Используют `async def`
3. **Все интеграции async**: Все функции в workflow используют `async`
4. **Параллельная обработка**: Система может обрабатывать несколько запросов одновременно

## Моки и зависимости

Тесты используют моки для:
- Telegram Bot API (AsyncMock)
- HR Time API
- Email (IMAP/SMTP)
- WEEEK API
- RAG Chain (Qdrant)
- LLM API (OpenRouter/GigaChat)

Все внешние зависимости мокируются, поэтому тесты работают без реальных API ключей.

## Переменные окружения для тестов

Тесты используют переменные окружения через `patch.dict('os.environ', {...})`:

```python
with patch.dict('os.environ', {'TELEGRAM_CONSULTANT_CHAT_ID': '123456'}):
    # тест код
```

Реальные переменные окружения не требуются для запуска тестов.

## Примеры запуска

### Быстрая проверка
```bash
# Проверить что все функции async
pytest test_telegram_integration.py::test_bot_is_async -v

# Проверить один сценарий
pytest test_scenario_workflows.py::test_scenario1_warm_lead_workflow -v
```

### Полная проверка
```bash
# Все тесты с покрытием
pytest --cov=. --cov-report=term-missing -v
```

### Отладка
```bash
# С выводом print и остановкой на первой ошибке
pytest -v -s -x

# Конкретный тест с подробным выводом
pytest test_integration_full.py::TestFullSystemIntegration::test_end_to_end_hrtime_to_telegram -v -s
```

## CI/CD интеграция

Пример для GitHub Actions:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Покрытие кода

Текущее покрытие можно проверить:

```bash
pytest --cov=scenario_workflows --cov=integrate_scenarios --cov-report=term
```

Цель: >80% покрытие для критических модулей.

## Добавление новых тестов

При добавлении нового функционала:

1. Добавьте unit тесты в соответствующий файл
2. Добавьте интеграционный тест если нужен
3. Проверьте покрытие кода
4. Убедитесь что тесты проходят

Пример нового теста:

```python
@pytest.mark.asyncio
async def test_new_feature():
    """Описание теста"""
    # Arrange
    mock_data = {...}
    
    # Act
    result = await your_function(mock_data)
    
    # Assert
    assert result["success"] is True
    assert result["field"] == expected_value
```

## Troubleshooting

### Тесты не запускаются
```bash
# Установите зависимости
pip install -r requirements.txt

# Проверьте Python версию (нужен 3.8+)
python --version
```

### Async тесты падают
```bash
# Убедитесь что pytest-asyncio установлен
pip install pytest-asyncio

# Используйте маркер @pytest.mark.asyncio
```

### Импорты не работают
```bash
# Убедитесь что вы в корневой директории проекта
cd /path/to/HR_Bot

# Установите проект в dev режиме (если нужно)
pip install -e .
```

