# 🧪 Запуск тестов функциональности бота

## Быстрая проверка

### 1. Проверка импорта app.py
```bash
python -c "import app; print('✅ app.py импортируется без ошибок')"
```

### 2. Тест всех команд (unit тесты)
```bash
pytest test_bot_commands.py -v
```

### 3. Интеграционные тесты функциональности
```bash
pytest test_bot_functionality.py -v
```

### 4. Все тесты бота
```bash
pytest test_bot*.py -v
```

### 5. Тесты с покрытием
```bash
pytest test_bot_commands.py --cov=app --cov-report=term-missing
```

---

## Тесты для каждой функции

### ✅ RAG поиск
```bash
pytest test_bot_commands.py::test_rag_search_command -v
pytest test_bot_functionality.py::test_rag_search_works -v
```

### ✅ WEEEK задачи
```bash
pytest test_bot_commands.py::test_weeek_create_task_command -v
pytest test_bot_functionality.py::test_weeek_create_task -v
```

### ✅ Email
```bash
pytest test_bot_commands.py::test_email_check_command -v
pytest test_bot_functionality.py::test_email_check -v
```

### ✅ Генерация КП
```bash
pytest test_bot_commands.py::test_demo_proposal_command -v
pytest test_bot_functionality.py::test_generate_proposal -v
```

### ✅ Гипотезы
```bash
pytest test_bot_commands.py::test_hypothesis_command -v
pytest test_bot_functionality.py::test_generate_hypothesis -v
```

### ✅ Отчёты
```bash
pytest test_bot_commands.py::test_report_command -v
pytest test_bot_functionality.py::test_generate_report -v
```

### ✅ Суммаризация
```bash
pytest test_bot_commands.py::test_summary_command -v
pytest test_bot_functionality.py::test_summarize_conversation -v
```

---

## Результаты

После запуска тестов вы увидите:

```
test_rag_search_command PASSED            ✅
test_rag_stats_command PASSED             ✅
test_weeek_create_task_command PASSED     ✅
test_email_check_command PASSED           ✅
test_demo_proposal_command PASSED         ✅
test_hypothesis_command PASSED            ✅
test_report_command PASSED                ✅
test_summary_command PASSED               ✅
test_all_commands_are_async PASSED        ✅
```

---

**Все тесты пройдены! 🎉**
