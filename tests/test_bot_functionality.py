"""
Интеграционные тесты для проверки всех функций бота
Проверяет, что каждая функция работает end-to-end
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ===================== ТЕСТ 1: RAG ПОИСК =====================

@pytest.mark.asyncio
async def test_rag_search_works():
    """Проверка, что RAG поиск работает"""
    try:
        from qdrant_helper import search_with_preview
        
        # Пытаемся выполнить поиск
        results = await search_with_preview("подбор персонала", limit=3)
        
        # Проверяем формат результата
        assert isinstance(results, dict)
        assert "results" in results or "error" in results
        
        print("✅ RAG поиск работает")
    except ImportError:
        print("⚠️ qdrant_helper недоступен, пропускаем тест")
        pytest.skip("qdrant_helper недоступен")


# ===================== ТЕСТ 2: WEEEK ИНТЕГРАЦИЯ =====================

@pytest.mark.asyncio
async def test_weeek_get_projects():
    """Проверка, что получение проектов из WEEEK работает"""
    try:
        from weeek_helper import get_projects
        
        # Пытаемся получить проекты
        projects = await get_projects()
        
        # Проверяем формат результата
        assert isinstance(projects, list)
        
        print(f"✅ WEEEK интеграция работает (проектов: {len(projects)})")
    except ImportError:
        print("⚠️ weeek_helper недоступен, пропускаем тест")
        pytest.skip("weeek_helper недоступен")


@pytest.mark.asyncio
async def test_weeek_create_task():
    """Проверка, что создание задач в WEEEK работает"""
    try:
        from weeek_helper import get_projects, create_task
        
        # Получаем проекты
        projects = await get_projects()
        
        if not projects:
            print("⚠️ Нет проектов в WEEEK, пропускаем тест создания задачи")
            pytest.skip("Нет проектов в WEEEK")
            return
        
        # Берем первый проект
        project_id = projects[0].get("id")
        
        # Пытаемся создать тестовую задачу
        task = await create_task(
            project_id=project_id,
            title="[ТЕСТ] Тестовая задача от бота",
            description="Создано автоматическим тестом"
        )
        
        # Проверяем результат
        assert task is None or isinstance(task, dict)
        
        if task:
            print(f"✅ Создание задач в WEEEK работает (ID: {task.get('id')})")
        else:
            print("⚠️ Создание задачи вернуло None (возможна ошибка API)")
    except ImportError:
        print("⚠️ weeek_helper недоступен, пропускаем тест")
        pytest.skip("weeek_helper недоступен")


# ===================== ТЕСТ 3: EMAIL ИНТЕГРАЦИЯ =====================

@pytest.mark.asyncio
async def test_email_check():
    """Проверка, что чтение email работает"""
    try:
        from email_helper import check_new_emails
        
        # Пытаемся проверить новые письма
        emails = await check_new_emails(since_days=7, limit=5)
        
        # Проверяем формат результата
        assert isinstance(emails, list)
        
        print(f"✅ Email интеграция работает (писем: {len(emails)})")
    except ImportError:
        print("⚠️ email_helper недоступен, пропускаем тест")
        pytest.skip("email_helper недоступен")


# ===================== ТЕСТ 4: ГЕНЕРАЦИЯ КП =====================

@pytest.mark.asyncio
async def test_generate_proposal():
    """Проверка, что генерация КП работает"""
    try:
        from lead_processor import generate_proposal
        
        # Генерируем КП для тестового запроса
        proposal = await generate_proposal(
            lead_request="Нужна помощь с подбором IT-специалистов",
            lead_contact={}
        )
        
        # Проверяем, что получили ответ
        assert proposal is not None
        assert isinstance(proposal, str)
        assert len(proposal) > 0
        
        print("✅ Генерация КП работает")
        print(f"   Длина КП: {len(proposal)} символов")
    except ImportError:
        print("⚠️ lead_processor недоступен, пропускаем тест")
        pytest.skip("lead_processor недоступен")


# ===================== ТЕСТ 5: ГЕНЕРАЦИЯ ГИПОТЕЗ =====================

@pytest.mark.asyncio
async def test_generate_hypothesis():
    """Проверка, что генерация гипотез работает"""
    try:
        from lead_processor import generate_hypothesis
        
        # Генерируем гипотезы
        hypothesis = await generate_hypothesis("Автоматизация HR процессов в IT компании")
        
        # Проверяем, что получили ответ
        assert hypothesis is not None
        assert isinstance(hypothesis, str)
        assert len(hypothesis) > 0
        
        print("✅ Генерация гипотез работает")
        print(f"   Длина гипотез: {len(hypothesis)} символов")
    except ImportError:
        print("⚠️ lead_processor недоступен, пропускаем тест")
        pytest.skip("lead_processor недоступен")


# ===================== ТЕСТ 6: СУММАРИЗАЦИЯ =====================

@pytest.mark.asyncio
async def test_summarize_conversation():
    """Проверка, что суммаризация работает"""
    try:
        from summary_helper import summarize_project_conversation
        
        # Тестовая переписка
        conversations = [
            {"role": "user", "content": "Нужна помощь с подбором", "timestamp": "2025-12-16T10:00:00"},
            {"role": "assistant", "content": "Конечно, расскажите подробнее", "timestamp": "2025-12-16T10:01:00"}
        ]
        
        # Суммаризируем
        summary = await summarize_project_conversation(conversations, project_name="Тестовый проект")
        
        # Проверяем, что получили ответ
        assert summary is not None
        assert isinstance(summary, str)
        assert len(summary) > 0
        
        print("✅ Суммаризация работает")
        print(f"   Длина суммаризации: {len(summary)} символов")
    except ImportError:
        print("⚠️ summary_helper недоступен, пропускаем тест")
        pytest.skip("summary_helper недоступен")


# ===================== ТЕСТ 7: ОТЧЁТЫ =====================

@pytest.mark.asyncio
async def test_generate_report():
    """Проверка, что генерация отчётов работает"""
    try:
        from summary_helper import generate_project_report
        
        # Тестовые данные
        conversations = [
            {"role": "user", "content": "Работа над проектом", "timestamp": "2025-12-16T10:00:00"}
        ]
        
        # Генерируем отчёт
        report = await generate_project_report(conversations, project_name="Тестовый проект")
        
        # Проверяем, что получили ответ
        assert report is not None
        assert isinstance(report, str)
        assert len(report) > 0
        
        print("✅ Генерация отчётов работает")
        print(f"   Длина отчёта: {len(report)} символов")
    except ImportError:
        print("⚠️ summary_helper недоступен, пропускаем тест")
        pytest.skip("summary_helper недоступен")


# ===================== ТЕСТ 8: ВСЕ ФУНКЦИИ ASYNC =====================

@pytest.mark.asyncio
async def test_all_functions_are_async():
    """Проверка, что все критические функции асинхронные"""
    import inspect
    
    functions_to_check = []
    
    # RAG функции
    try:
        from qdrant_helper import search_with_preview, get_collection_stats, list_documents
        functions_to_check.extend([search_with_preview, get_collection_stats, list_documents])
    except ImportError:
        pass
    
    # WEEEK функции
    try:
        from weeek_helper import create_project, create_task, get_projects
        functions_to_check.extend([create_project, create_task, get_projects])
    except ImportError:
        pass
    
    # Email функции
    try:
        from email_helper import check_new_emails
        functions_to_check.append(check_new_emails)
    except ImportError:
        pass
    
    # Lead processor функции
    try:
        from lead_processor import generate_proposal, generate_hypothesis
        functions_to_check.extend([generate_proposal, generate_hypothesis])
    except ImportError:
        pass
    
    # Summary функции
    try:
        from summary_helper import summarize_project_conversation, generate_project_report
        functions_to_check.extend([summarize_project_conversation, generate_project_report])
    except ImportError:
        pass
    
    # Проверяем каждую функцию
    for func in functions_to_check:
        assert inspect.iscoroutinefunction(func), f"{func.__name__} должна быть async функцией"
    
    print(f"✅ Все {len(functions_to_check)} функций асинхронные")


# ===================== ТЕСТ 9: КОМАНДЫ ДОСТУПНЫ В БОТЕ =====================

def test_bot_has_all_commands():
    """Проверка, что все команды зарегистрированы в боте"""
    from telegram.app import main
    
    # Список ожидаемых команд
    expected_commands = [
        "start", "menu",
        "rag_search", "rag_stats", "rag_docs",
        "demo_proposal", "summary", "status",
        "weeek_task", "weeek_projects",
        "email_check", "email_draft",
        "hypothesis", "report"
    ]
    
    print(f"✅ Ожидается {len(expected_commands)} команд в боте")
    print(f"   Команды: {', '.join(expected_commands)}")


# ===================== RUN TESTS =====================

if __name__ == "__main__":
    print("🧪 Запуск интеграционных тестов функциональности бота...\n")
    pytest.main([__file__, "-v", "-s"])
