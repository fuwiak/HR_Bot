"""
Классификатор намерений - определение запросов на запись
"""
import logging
import re

from telegram_bot.integrations.google_sheets import get_services, get_masters
from telegram_bot.config import BOOKING_KEYWORDS

log = logging.getLogger(__name__)


def is_booking(text):
    """
    Улучшенная функция определения запроса на запись.
    Использует многоуровневый подход:
    1. Проверка наличия услуг из Google Sheets
    2. Проверка упоминания HR-специалистов
    3. Проверка временных маркеров (дата/время)
    4. Проверка ключевых слов (fallback)
    """
    text_lower = text.lower().strip()
    
    # Если сообщение слишком короткое (меньше 2 символов) - не запрос на запись
    if len(text_lower) < 2:
        return False
    
    score = 0  # Система scoring для определения вероятности запроса на запись
    reasons = []  # Причины, почему это может быть запрос на запись
    
    # 1. ПРОВЕРКА: Есть ли название услуги из Google Sheets (самый важный признак)
    try:
        all_services = get_services()
        log.debug(f"🔍 Проверка '{text}' среди {len(all_services)} услуг из Google Sheets")
        
        if not all_services:
            log.warning(f"⚠️ Список услуг пуст! Проверьте подключение к Google Sheets")
        else:
            # Логируем первые несколько услуг для отладки
            log.debug(f"🔍 Первые услуги: {[s.get('title') for s in all_services[:5]]}")
        
        for service in all_services:
            service_title = service.get("title", "").lower().strip()
            if not service_title:
                continue
                
            service_words = set(service_title.split())
            text_words = set(text_lower.split())
            
            # Точное совпадение - максимальный score
            if service_title == text_lower:
                score += 50
                reasons.append(f"точное совпадение услуги '{service.get('title')}'")
                log.info(f"🔍 BOOKING CHECK: '{text}' -> точное совпадение услуги '{service.get('title')}'")
                break
            
            # Полное вхождение названия услуги в текст
            elif service_title in text_lower:
                score += 40
                reasons.append(f"найдена услуга '{service.get('title')}'")
                log.info(f"🔍 BOOKING CHECK: '{text}' -> найдена услуга '{service.get('title')}'")
                break
            
            # Полное вхождение текста в название услуги
            elif text_lower in service_title:
                score += 35
                reasons.append(f"текст совпадает с услугой '{service.get('title')}'")
                log.info(f"🔍 BOOKING CHECK: '{text}' -> текст совпадает с услугой '{service.get('title')}'")
                break
            
            # Совпадение 2+ слов
            elif len(service_words & text_words) >= 2:
                score += 30
                reasons.append(f"частичное совпадение услуги '{service.get('title')}'")
                log.info(f"🔍 BOOKING CHECK: '{text}' -> частичное совпадение услуги '{service.get('title')}'")
                break
    except Exception as e:
        log.error(f"❌ Ошибка при проверке услуг для is_booking: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
    
    # 2. ПРОВЕРКА: Упоминание HR-специалистов
    try:
        all_masters = get_masters()
        for master in all_masters:
            master_name = master.get("name", "").lower()
            if master_name in text_lower:
                score += 15
                reasons.append(f"упоминание HR-специалиста '{master.get('name')}'")
                break
    except Exception as e:
        log.debug(f"Ошибка при проверке HR-специалистов для is_booking: {e}")
    
    # 3. ПРОВЕРКА: Временные маркеры (дата/время)
    time_markers = [
        "завтра", "сегодня", "послезавтра", "в ", "на ", "часов", ":", 
        "октября", "ноября", "декабря", "января", "февраля", "марта", 
        "апреля", "мая", "июня", "июля", "августа", "сентября",
        "утра", "утром", "вечера", "вечером", "дня", "днем", "ночи", "ночью",
        "утро", "вечер", "день"
    ]
    time_markers_found = 0
    for marker in time_markers:
        if marker in text_lower:
            time_markers_found += 1
            reasons.append(f"временной маркер '{marker}'")
    
    # Если найдено несколько временных маркеров - это явно запрос на запись
    if time_markers_found >= 2:
        score += 25  # Достаточно для порога
    elif time_markers_found >= 1:
        score += 15  # Один маркер тоже может быть запросом
    
    # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: Формат даты DD.MM.YYYY или DD/MM/YYYY с временем
    date_time_pattern = r'\d{1,2}[./]\d{1,2}[./]\d{4}\s+\d{1,2}:\d{2}'
    if re.search(date_time_pattern, text):
        score += 30
        reasons.append("формат даты и времени (DD.MM.YYYY HH:MM)")
        log.info(f"🔍 BOOKING CHECK: '{text}' -> найдена дата и время в формате DD.MM.YYYY HH:MM")
    
    # 4. ПРОВЕРКА: Ключевые слова записи (fallback)
    booking_keywords = [
        "запись", "записаться", "записать", "забронировать",
        "когда можно", "свободное время", "расписание",
        "записаться на", "хочу записаться", "нужна запись"
    ]
    for keyword in booking_keywords:
        if keyword in text_lower:
            score += 20
            reasons.append(f"ключевое слово '{keyword}'")
            break
    
    # 5. ПРОВЕРКА: Вопросы о услугах/ценах
    question_patterns = [
        "сколько стоит", "какая цена", "сколько стоит", "цена",
        "можно ли", "возможно ли", "есть ли"
    ]
    for pattern in question_patterns:
        if pattern in text_lower:
            score += 5
            reasons.append(f"вопрос о услуге/цене")
            break
    
    # Решение: если score >= 20, это запрос на запись
    is_booking_request = score >= 20
    
    if is_booking_request:
        log.info(f"🔍 BOOKING CHECK: '{text}' -> ДА (score={score}, причины: {', '.join(reasons)})")
    else:
        log.info(f"🔍 BOOKING CHECK: '{text}' -> НЕТ (score={score}, недостаточно признаков)")
    
    return is_booking_request
