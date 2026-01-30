"""
Calendar Helper
Получение доступных дат из календаря для планирования проектов
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

log = logging.getLogger()

# Попытка импорта WEEEK helper
try:
    from services.helpers.weeek_helper import get_tasks, get_project_deadlines
    WEEEK_AVAILABLE = True
except ImportError:
    WEEEK_AVAILABLE = False
    log.warning("⚠️ WEEEK helper недоступен")


async def get_available_dates(days_ahead: int = 60) -> Dict:
    """
    Получить информацию о доступных датах для планирования проектов
    
    Args:
        days_ahead: Количество дней вперед для проверки (по умолчанию 60)
    
    Returns:
        Словарь с информацией о доступных датах:
        {
            "available_weeks": ["неделя 1", "неделя 2", ...],
            "busy_periods": ["2024-02-15 - 2024-02-20", ...],
            "earliest_start": "2024-02-01",
            "recommended_start": "2024-02-15"
        }
    """
    result = {
        "available_weeks": [],
        "busy_periods": [],
        "earliest_start": None,
        "recommended_start": None
    }
    
    if not WEEEK_AVAILABLE:
        log.warning("⚠️ WEEEK недоступен, возвращаю базовую информацию о датах")
        # Возвращаем базовую информацию без проверки занятости
        today = datetime.now()
        earliest = (today + timedelta(days=7)).strftime("%d.%m.%Y")
        recommended = (today + timedelta(days=14)).strftime("%d.%m.%Y")
        
        result["earliest_start"] = earliest
        result["recommended_start"] = recommended
        result["available_weeks"] = [
            f"неделя с {earliest}",
            f"неделя с {recommended}"
        ]
        return result
    
    try:
        # Получаем задачи с дедлайнами на ближайшие дни
        tasks = await get_project_deadlines(days_ahead=days_ahead)
        
        today = datetime.now()
        busy_dates = set()
        
        # Собираем занятые даты из задач
        for task in tasks:
            due_date_str = task.get("due_date", "")
            if due_date_str:
                try:
                    # Парсим дату в разных форматах
                    if "T" in due_date_str:
                        due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00")).date()
                    elif "." in due_date_str:
                        # Формат dd.mm.yyyy
                        due_date = datetime.strptime(due_date_str, "%d.%m.%Y").date()
                    else:
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                    
                    # Помечаем дату и несколько дней вокруг как занятые
                    for i in range(-2, 3):  # 2 дня до и 2 дня после
                        busy_date = due_date + timedelta(days=i)
                        if busy_date >= today.date():
                            busy_dates.add(busy_date)
                except Exception as e:
                    log.warning(f"⚠️ Ошибка парсинга даты {due_date_str}: {e}")
        
        # Находим свободные периоды
        current_date = today.date()
        end_date = current_date + timedelta(days=days_ahead)
        
        # Группируем занятые даты в периоды
        busy_periods = []
        if busy_dates:
            sorted_dates = sorted(busy_dates)
            start_period = sorted_dates[0]
            end_period = sorted_dates[0]
            
            for date in sorted_dates[1:]:
                if date == end_period + timedelta(days=1):
                    end_period = date
                else:
                    if start_period == end_period:
                        busy_periods.append(start_period.strftime("%d.%m.%Y"))
                    else:
                        busy_periods.append(f"{start_period.strftime('%d.%m.%Y')} - {end_period.strftime('%d.%m.%Y')}")
                    start_period = date
                    end_period = date
            
            # Добавляем последний период
            if start_period == end_period:
                busy_periods.append(start_period.strftime("%d.%m.%Y"))
            else:
                busy_periods.append(f"{start_period.strftime('%d.%m.%Y')} - {end_period.strftime('%d.%m.%Y')}")
        
        result["busy_periods"] = busy_periods
        
        # Находим ближайшую свободную дату (минимум через неделю)
        earliest_start = current_date + timedelta(days=7)
        while earliest_start in busy_dates and earliest_start <= end_date:
            earliest_start += timedelta(days=1)
        
        # Рекомендуемая дата начала (минимум через 2 недели)
        recommended_start = current_date + timedelta(days=14)
        while recommended_start in busy_dates and recommended_start <= end_date:
            recommended_start += timedelta(days=1)
        
        result["earliest_start"] = earliest_start.strftime("%d.%m.%Y")
        result["recommended_start"] = recommended_start.strftime("%d.%m.%Y")
        
        # Формируем список доступных недель
        week_start = earliest_start
        week_count = 0
        while week_start <= end_date and week_count < 8:  # Максимум 8 недель
            if week_start not in busy_dates:
                result["available_weeks"].append(f"неделя с {week_start.strftime('%d.%m.%Y')}")
                week_count += 1
            week_start += timedelta(days=7)
        
        log.info(f"✅ Получена информация о календаре: earliest={result['earliest_start']}, recommended={result['recommended_start']}, busy_periods={len(busy_periods)}")
        
    except Exception as e:
        log.error(f"❌ Ошибка получения информации о календаре: {e}")
        # Fallback на базовую информацию
        today = datetime.now()
        earliest = (today + timedelta(days=7)).strftime("%d.%m.%Y")
        recommended = (today + timedelta(days=14)).strftime("%d.%m.%Y")
        
        result["earliest_start"] = earliest
        result["recommended_start"] = recommended
        result["available_weeks"] = [
            f"неделя с {earliest}",
            f"неделя с {recommended}"
        ]
    
    return result


async def format_calendar_info_for_prompt(calendar_info: Optional[Dict] = None) -> str:
    """
    Форматирует информацию о календаре для использования в промпте
    
    Args:
        calendar_info: Информация о календаре из get_available_dates()
    
    Returns:
        Отформатированная строка для промпта
    """
    if not calendar_info:
        calendar_info = await get_available_dates()
    
    lines = []
    
    if calendar_info.get("earliest_start"):
        lines.append(f"Ближайшая доступная дата начала проекта: {calendar_info['earliest_start']}")
    
    if calendar_info.get("recommended_start"):
        lines.append(f"Рекомендуемая дата начала проекта: {calendar_info['recommended_start']}")
    
    if calendar_info.get("available_weeks"):
        lines.append(f"Доступные недели для старта: {', '.join(calendar_info['available_weeks'][:4])}")
    
    if calendar_info.get("busy_periods"):
        lines.append(f"Занятые периоды (учитывать при планировании): {', '.join(calendar_info['busy_periods'][:3])}")
    
    if lines:
        return "\n".join(lines)
    else:
        return "Информация о календаре недоступна. Используй примерные сроки в неделях."
