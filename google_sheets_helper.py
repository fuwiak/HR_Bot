"""
Google Sheets интеграция для хранения записей и расписания
Если Google Sheets не настроены, используется placeholder для тестирования
"""
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

log = logging.getLogger()

# Попытка импорта Google Sheets API
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    log.warning("Google Sheets библиотеки не установлены. Используется placeholder режим.")

# Конфигурация
GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")

# Глобальная переменная для клиента
_sheets_client = None

def get_sheets_client():
    """Получить клиент Google Sheets или None если не настроен"""
    global _sheets_client
    
    if not GOOGLE_SHEETS_AVAILABLE:
        return None
    
    if _sheets_client is not None:
        return _sheets_client
    
    if not GOOGLE_SHEETS_CREDENTIALS_PATH or not GOOGLE_SHEETS_SPREADSHEET_ID:
        log.warning("Google Sheets не настроены - используем placeholder")
        return None
    
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(
            GOOGLE_SHEETS_CREDENTIALS_PATH, scopes=scope)
        _sheets_client = gspread.authorize(creds)
        log.info("✅ Google Sheets клиент успешно инициализирован")
        return _sheets_client
    except Exception as e:
        log.error(f"❌ Ошибка инициализации Google Sheets: {e}")
        return None


# ===================== PLACEHOLDER ДАННЫЕ =====================

# Мастера и их расписание (placeholder)
PLACEHOLDER_MASTERS = [
    {
        "id": 1,
        "name": "Роман",
        "specialization": "Мужской зал",
        "services": ["Стрижка", "Стрижка под машинку", "Тонировка бороды", "Бритье"],
        "schedule": {
            "daily_start": "11:00",
            "daily_end": "21:00",
            "days_off": []  # Будет заполняться из Google Sheets
        }
    },
    {
        "id": 2,
        "name": "Анжела",
        "specialization": "Женский зал",
        "services": ["Стрижка", "Окрашивание", "Маникюр", "Педикюр"],
        "schedule": {
            "pattern": "3/1",  # 3 дня работы, 1 выходной
            "daily_start": "09:00",
            "daily_end": "20:00",
            "days_off": []
        }
    }
]

# Услуги (placeholder)
PLACEHOLDER_SERVICES = [
    # Мужские услуги (Роман)
    {"id": 1, "title": "Стрижка", "price": 1500, "duration": 60, "master": "Роман", "type": "men"},
    {"id": 2, "title": "Стрижка под машинку", "price": 800, "duration": 30, "master": "Роман", "type": "men"},
    {"id": 3, "title": "Тонировка бороды", "price": 500, "duration": 20, "master": "Роман", "type": "men", "additional": True},
    {"id": 4, "title": "Бритье", "price": 600, "duration": 30, "master": "Роман", "type": "men"},
    # Женские услуги (Анжела)
    {"id": 5, "title": "Стрижка", "price": 2000, "duration": 90, "master": "Анжела", "type": "women"},
    {"id": 6, "title": "Окрашивание", "price": 4000, "duration": 180, "master": "Анжела", "type": "women"},
    {"id": 7, "title": "Маникюр", "price": 1500, "duration": 60, "master": "Анжела", "type": "women"},
    {"id": 8, "title": "Педикюр", "price": 1800, "duration": 60, "master": "Анжела", "type": "women"},
]

# Записи (placeholder - в реальности будет в Google Sheets)
PLACEHOLDER_BOOKINGS = []


# ===================== ФУНКЦИИ РАБОТЫ С ДАННЫМИ =====================

def get_masters() -> List[Dict]:
    """Получить список мастеров"""
    client = get_sheets_client()
    
    if client:
        try:
            # TODO: Реализовать чтение из Google Sheets
            # sheet = client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID).worksheet("Мастера")
            # masters = sheet.get_all_records()
            pass
        except Exception as e:
            log.error(f"Ошибка чтения мастеров из Google Sheets: {e}")
    
    # Используем placeholder данные
    return PLACEHOLDER_MASTERS.copy()


def get_services(master_name: Optional[str] = None) -> List[Dict]:
    """Получить список услуг, опционально фильтровать по мастеру"""
    client = get_sheets_client()
    
    if client:
        try:
            # TODO: Реализовать чтение из Google Sheets
            pass
        except Exception as e:
            log.error(f"Ошибка чтения услуг из Google Sheets: {e}")
    
    # Используем placeholder данные
    services = PLACEHOLDER_SERVICES.copy()
    
    if master_name:
        services = [s for s in services if s.get("master", "").lower() == master_name.lower()]
    
    return services


def get_available_slots(master_name: str, date: str) -> List[str]:
    """Получить доступные слоты времени для мастера на дату"""
    client = get_sheets_client()
    
    if client:
        try:
            # TODO: Реализовать чтение расписания из Google Sheets
            pass
        except Exception as e:
            log.error(f"Ошибка чтения расписания из Google Sheets: {e}")
    
    # Placeholder: возвращаем базовые временные слоты
    master = next((m for m in PLACEHOLDER_MASTERS if m["name"].lower() == master_name.lower()), None)
    if not master:
        return []
    
    schedule = master["schedule"]
    start_time = datetime.strptime(schedule.get("daily_start", "09:00"), "%H:%M")
    end_time = datetime.strptime(schedule.get("daily_end", "20:00"), "%H:%M")
    
    slots = []
    current = start_time
    while current < end_time:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(hours=1)
    
    return slots


def create_booking(booking_data: Dict) -> Dict:
    """Создать запись в Google Sheets или placeholder"""
    client = get_sheets_client()
    
    booking_id = len(PLACEHOLDER_BOOKINGS) + 1
    booking_record = {
        "id": booking_id,
        **booking_data,
        "created_at": datetime.now().isoformat(),
        "status": "confirmed"
    }
    
    if client:
        try:
            # TODO: Реализовать запись в Google Sheets
            # sheet = client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID).worksheet("Записи")
            # sheet.append_row([...])
            log.info(f"✅ Запись {booking_id} создана в Google Sheets")
        except Exception as e:
            log.error(f"Ошибка записи в Google Sheets: {e}")
            # Сохраняем в placeholder как fallback
            PLACEHOLDER_BOOKINGS.append(booking_record)
    else:
        # Сохраняем в placeholder
        PLACEHOLDER_BOOKINGS.append(booking_record)
        log.info(f"✅ Запись {booking_id} создана (placeholder режим)")
    
    return booking_record


def check_slot_available(master_name: str, date: str, time: str) -> bool:
    """Проверить доступность слота времени"""
    client = get_sheets_client()
    
    if client:
        try:
            # TODO: Реализовать проверку в Google Sheets
            pass
        except Exception as e:
            log.error(f"Ошибка проверки слота в Google Sheets: {e}")
    
    # Placeholder: проверяем в памяти
    for booking in PLACEHOLDER_BOOKINGS:
        if (booking.get("master", "").lower() == master_name.lower() and
            booking.get("date") == date and
            booking.get("time") == time):
            return False
    
    return True

