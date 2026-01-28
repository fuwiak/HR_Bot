"""
Парсер для извлечения информации о записи из сообщений
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Dict

from telegram_bot.integrations.google_sheets import get_services, get_masters
from telegram_bot.nlp.text_utils import find_best_match

log = logging.getLogger(__name__)


def find_service_advanced(message: str) -> str:
    """Продвинутый поиск услуги с regex и нечетким поиском"""
    message_lower = message.lower()
    
    # Сначала пытаемся найти в реальных услугах из Google Sheets
    try:
        all_services = get_services()
        for service in all_services:
            service_title = service.get("title", "").lower()
            # Проверяем точное совпадение или частичное
            if service_title in message_lower or any(word in service_title for word in message_lower.split() if len(word) > 3):
                log.info(f"🔍 Найдена услуга в реальных данных: {service.get('title')}")
                return service.get("title")
    except Exception as e:
        log.debug(f"Не удалось получить услуги для поиска: {e}")
    
    # Расширенные варианты услуг с regex паттернами (fallback)
    service_patterns = {
        "консультация": [
            r'\bконсультац\w*\b',
            r'\bконсульт\w*\b',
        ],
        "собеседование": [
            r'\bсобеседован\w*\b',
            r'\bинтервью\w*\b',
        ],
        "онбординг": [
            r'\bонбординг\w*\b',
            r'\bадаптац\w*\b',
        ],
        "обучение": [
            r'\bобучен\w*\b',
            r'\bтренинг\w*\b',
        ],
        "оценка": [
            r'\bоценк\w*\b',
            r'\bаттестац\w*\b',
        ],
    }
    
    # Ищем по regex паттернам
    for service_key, patterns in service_patterns.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                # Пытаемся найти полное название услуги в реальных данных
                try:
                    all_services = get_services()
                    for real_service in all_services:
                        if service_key in real_service.get("title", "").lower():
                            return real_service.get("title")
                except:
                    pass
                return service_key
    
    return None


def find_master_advanced(message: str) -> str:
    """Продвинутый поиск мастера с regex и нечетким поиском"""
    message_lower = message.lower()
    
    # Regex паттерны для имен мастеров
    master_patterns = {
        "арина": [
            r'\bарин\w*\b',      # арина, арины, арине, арину, ариной
            r'\bаринк\w*\b',     # аринка, ариночка
        ],
        "екатерина": [
            r'\bекатерин\w*\b',  # екатерина, екатерины, екатерине, екатерину, екатериной
            r'\bкат\w*\b',       # катя, кати, кате, катю, катей, катенька
            r'\bкатюш\w*\b',     # катюша, катюши, катюше, катюшу, катюшей, катюшка
        ],
        "полина": [
            r'\bполин\w*\b',     # полина, полины, полине, полину, полиной
            r'\bполинк\w*\b',    # полинка, полиночка
        ]
    }
    
    # Ищем по regex паттернам
    for master, patterns in master_patterns.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                return master.title()
    
    # Fallback к нечеткому поиску
    master_variants = {
        "арина": ["арина", "арины", "арине", "арину", "ариной", "аринка", "ариночка"],
        "екатерина": ["екатерина", "екатерины", "екатерине", "екатерину", "екатериной", "катя", "кати", "кате", "катю", "катей", "катюша", "катюши", "катюше", "катюшу", "катюшей", "катенька", "катюшка"],
        "полина": ["полина", "полины", "полине", "полину", "полиной", "полинка", "полиночка"]
    }
    
    # Нечеткий поиск по словам
    words = message_lower.split()
    for word in words:
        all_variants = []
        for variants in master_variants.values():
            all_variants.extend(variants)
        
        best_match = find_best_match(word, all_variants, threshold=75)
        if best_match:
            for master, variants in master_variants.items():
                if best_match in variants:
                    return master.title()
    
    return None


def parse_booking_message(message: str, history: str) -> Dict:
    """Парсит сообщение пользователя и извлекает информацию о записи"""
    result = {
        "service": None,
        "master": None,
        "datetime": None,
        "has_all_info": False
    }
    
    message_lower = message.lower()
    
    # Получаем реальные услуги из Google Sheets
    try:
        all_services = get_services()
        service_titles = [s.get("title", "") for s in all_services]
        log.info(f"🔍 Поиск услуги среди {len(service_titles)} услуг: {service_titles[:5]}...")
    except Exception as e:
        log.error(f"❌ Ошибка получения услуг для парсинга: {e}")
        service_titles = []
    
    # Получаем реальных мастеров
    try:
        all_masters = get_masters()
        master_names = [m.get("name", "") for m in all_masters]
        log.info(f"🔍 Поиск мастера среди: {master_names}")
    except Exception as e:
        log.error(f"❌ Ошибка получения мастеров для парсинга: {e}")
        master_names = ["Анастасия Новосёлова"]  # Fallback
    
    # Ищем услугу в реальных данных
    if service_titles:
        for service_title in service_titles:
            service_lower = service_title.lower()
            # Проверяем, содержится ли название услуги в сообщении
            if service_lower in message_lower:
                result["service"] = service_title
                log.info(f"✅ Найдена услуга: {service_title}")
                break
            # Проверяем частичное совпадение (например, "бритье головы" vs "бритье")
            words = message_lower.split()
            for word in words:
                if word in service_lower or service_lower in word:
                    if len(word) > 3:  # Игнорируем короткие слова
                        result["service"] = service_title
                        log.info(f"✅ Найдена услуга (частичное совпадение): {service_title}")
                        break
            if result["service"]:
                break
    
    # Используем продвинутый поиск как fallback
    if not result["service"]:
        result["service"] = find_service_advanced(message)
        if result["service"]:
            log.info(f"✅ Найдена услуга через find_service_advanced: {result['service']}")
    
    # Ищем мастера в реальных данных
    for master_name in master_names:
        if master_name.lower() in message_lower:
            result["master"] = master_name
            log.info(f"✅ Найден мастер: {master_name}")
            break
    
    # Используем продвинутый поиск мастеров как fallback
    if not result["master"]:
        result["master"] = find_master_advanced(message)
        if result["master"]:
            log.info(f"✅ Найден мастер через find_master_advanced: {result['master']}")
    
    # Fallback для мастеров (если не нашли в реальных данных)
    if not result["master"]:
        if "анастасия" in message_lower or "новосёлова" in message_lower:
            result["master"] = "Анастасия Новосёлова"
    
    # Ищем дату и время
    # Паттерны для поиска времени
    time_patterns = [
        r'(\d{1,2}):(\d{2})',  # 12:00, 9:30
        r'(\d{1,2})\s*часов',  # 12 часов
        r'в\s*(\d{1,2}):(\d{2})',  # в 12:00
        r'на\s*(\d{1,2}):(\d{2})',  # на 12:00
    ]
    
    # Расширенные паттерны для поиска даты
    date_patterns = [
        # Точные даты с месяцами
        r'(\d{1,2})\s*октября',  # 26 октября
        r'(\d{1,2})\s*ноября',   # 26 ноября
        r'(\d{1,2})\s*декабря',  # 26 декабря
        r'(\d{1,2})\s*января',   # 26 января
        r'(\d{1,2})\s*февраля',  # 26 февраля
        r'(\d{1,2})\s*марта',    # 26 марта
        r'(\d{1,2})\s*апреля',   # 26 апреля
        r'(\d{1,2})\s*мая',      # 26 мая
        r'(\d{1,2})\s*июня',     # 26 июня
        r'(\d{1,2})\s*июля',     # 26 июля
        r'(\d{1,2})\s*августа',  # 26 августа
        r'(\d{1,2})\s*сентября', # 26 сентября
        
        # Относительные даты
        r'\bзавтра\b',           # завтра
        r'\bпослезавтра\b',      # послезавтра
        r'\bсегодня\b',          # сегодня
        
        # Даты в формате DD.MM или DD/MM
        r'(\d{1,2})[./](\d{1,2})',  # 26.10 или 26/10
        
        # Даты с годами
        r'(\d{1,2})[./](\d{1,2})[./](\d{4})',  # 26.10.2025 или 01.01.2026
    ]
    
    # КРИТИЧЕСКОЕ: Проверяем формат "DD.MM.YYYY HH:MM" или "DD/MM/YYYY HH:MM"
    date_time_pattern = r'(\d{1,2})[./](\d{1,2})[./](\d{4})\s+(\d{1,2}):(\d{2})'
    date_time_match = re.search(date_time_pattern, message)
    if date_time_match:
        day, month, year, hour, minute = date_time_match.groups()
        # Форматируем дату и время
        date_str = f"{day.zfill(2)}.{month.zfill(2)}.{year}"
        time_str = f"{hour.zfill(2)}:{minute}"
        result["datetime"] = f"{date_str} {time_str}"
        log.info(f"✅ Найдена дата и время в формате DD.MM.YYYY HH:MM: {result['datetime']}")
        result["has_all_info"] = result["service"] is not None and result["master"] is not None
        return result
    
    # Ищем время
    time_match = None
    for pattern in time_patterns:
        match = re.search(pattern, message_lower)
        if match:
            if len(match.groups()) == 2:
                hour, minute = match.groups()
                time_match = f"{hour.zfill(2)}:{minute.zfill(2)}"
            else:
                hour = match.group(1)
                time_match = f"{hour.zfill(2)}:00"
            break
    
    # Ищем дату
    date_match = None
    month_map = {
        'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
        'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
        'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
    }
    
    for pattern in date_patterns:
        match = re.search(pattern, message_lower)
        if match:
            if pattern == r'\bзавтра\b':
                # Завтра
                tomorrow = datetime.now() + timedelta(days=1)
                date_match = tomorrow.strftime("%Y-%m-%d")
            elif pattern == r'\bпослезавтра\b':
                # Послезавтра
                day_after_tomorrow = datetime.now() + timedelta(days=2)
                date_match = day_after_tomorrow.strftime("%Y-%m-%d")
            elif pattern == r'\bсегодня\b':
                # Сегодня
                today = datetime.now()
                date_match = today.strftime("%Y-%m-%d")
            elif pattern == r'(\d{1,2})[./](\d{1,2})[./](\d{4})':
                # DD.MM.YYYY или DD/MM/YYYY
                day, month, year = match.groups()
                date_match = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            elif pattern == r'(\d{1,2})[./](\d{1,2})':
                # DD.MM или DD/MM (текущий год)
                day, month = match.groups()
                current_year = datetime.now().year
                date_match = f"{current_year}-{month.zfill(2)}-{day.zfill(2)}"
            else:
                # Месяцы по названию
                day = match.group(1)
                month_name = pattern.split(r'\s*')[1].replace(')', '')
                month = month_map.get(month_name, '10')  # По умолчанию октябрь
                current_year = datetime.now().year
                date_match = f"{current_year}-{month}-{day.zfill(2)}"
            break
    
    # Если нашли и время и дату, формируем datetime
    if time_match and date_match:
        result["datetime"] = f"{date_match} {time_match}"
    
    # Проверяем, есть ли все данные
    result["has_all_info"] = all([result["service"], result["master"], result["datetime"]])
    
    return result
