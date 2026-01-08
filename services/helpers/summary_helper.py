"""
Summary Helper Module
Суммаризация переписок по проектам и генерация отчетов
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

log = logging.getLogger()

# Импорты для LLM
try:
    from services.helpers.llm_helper import generate_with_fallback
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    log.warning("⚠️ LLM модуль недоступен")

# ===================== PROMPTS =====================

SUMMARY_PROMPT = """
Ты AI-ассистент консультанта. Сделай суммаризацию переписки по проекту.

Структура суммаризации:
1. Ключевые договоренности
2. Открытые вопросы
3. Следующий шаг
4. Важные детали и решения

Переписка:
{{conversation}}

Сделай краткую, но информативную суммаризацию.
"""

REPORT_PROMPT = """
Ты AI-ассистент консультанта. Сгенерируй отчет по проекту.

Структура отчета:
1. Краткое описание проекта
2. Выполненные этапы
3. Текущий статус
4. Ближайшие задачи
5. Риски и проблемы
6. Рекомендации

Данные проекта:
{{project_data}}

Сгенерируй структурированный отчет.
"""

# ===================== SUMMARIZATION =====================

async def summarize_project_conversation(
    conversations: List[Dict],
    project_name: Optional[str] = None
) -> str:
    """
    Суммаризация переписки по проекту
    
    Args:
        conversations: Список сообщений переписки
        project_name: Название проекта (опционально)
    
    Returns:
        Текст суммаризации
    """
    if not LLM_AVAILABLE:
        return "Сервис суммаризации временно недоступен."
    
    try:
        # Формируем текст переписки
        conversation_text = ""
        if project_name:
            conversation_text += f"Проект: {project_name}\n\n"
        
        for msg in conversations:
            role = msg.get("role", "user")
            content = msg.get("content", msg.get("text", ""))
            timestamp = msg.get("timestamp", msg.get("date", ""))
            
            conversation_text += f"[{timestamp}] {role}: {content}\n\n"
        
        prompt = SUMMARY_PROMPT.replace("{{conversation}}", conversation_text)
        
        messages = [{"role": "user", "content": prompt}]
        summary = await generate_with_fallback(
            messages,
            use_system_message=True,
            system_content="Ты помощник для суммаризации переписок. Делай краткие, но информативные выжимки.",
            max_tokens=2000,
            temperature=0.5
        )
        
        log.info(f"✅ Суммаризация создана (длина: {len(summary)} символов)")
        return summary
    except Exception as e:
        log.error(f"❌ Ошибка суммаризации: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return f"Ошибка при создании суммаризации: {str(e)}"

async def generate_report(project_data: Dict) -> str:
    """
    Генерация отчета по проекту
    
    Args:
        project_data: Данные проекта (статус, задачи, этапы и т.д.)
    
    Returns:
        Текст отчета
    """
    if not LLM_AVAILABLE:
        return "Сервис генерации отчетов временно недоступен."
    
    try:
        # Форматируем данные проекта для промпта
        project_text = f"""
Название проекта: {project_data.get('name', 'Не указано')}
Статус: {project_data.get('status', 'Не указан')}
Описание: {project_data.get('description', 'Не указано')}

Задачи:
"""
        tasks = project_data.get("tasks", [])
        for task in tasks:
            task_name = task.get("name", "Задача")
            task_status = task.get("status", "Не указан")
            task_due = task.get("due_date", "Не указан")
            project_text += f"- {task_name} (статус: {task_status}, дедлайн: {task_due})\n"
        
        prompt = REPORT_PROMPT.replace("{{project_data}}", project_text)
        
        messages = [{"role": "user", "content": prompt}]
        report = await generate_with_fallback(
            messages,
            use_system_message=True,
            system_content="Ты помощник для генерации отчетов. Создавай структурированные, информативные отчеты.",
            max_tokens=3000,
            temperature=0.6
        )
        
        log.info(f"✅ Отчет создан (длина: {len(report)} символов)")
        return report
    except Exception as e:
        log.error(f"❌ Ошибка генерации отчета: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return f"Ошибка при создании отчета: {str(e)}"

async def summarize_long_text(text: str, max_length: int = 500) -> str:
    """
    Суммаризация длинного текста (документов, писем)
    
    Args:
        text: Текст для суммаризации
        max_length: Максимальная длина суммаризации
    
    Returns:
        Краткая суммаризация текста
    """
    if not LLM_AVAILABLE:
        # Fallback: просто обрезаем текст
        return text[:max_length] + "..." if len(text) > max_length else text
    
    try:
        prompt = f"Сделай краткую суммаризацию следующего текста (не более {max_length} символов):\n\n{text}"
        
        messages = [{"role": "user", "content": prompt}]
        summary = await generate_with_fallback(
            messages,
            max_tokens=max_length + 100,
            temperature=0.5
        )
        
        # Обрезаем до нужной длины
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary
    except Exception as e:
        log.error(f"❌ Ошибка суммаризации текста: {e}")
        # Fallback
        return text[:max_length] + "..." if len(text) > max_length else text
























