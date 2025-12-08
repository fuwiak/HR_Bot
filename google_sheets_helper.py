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
    log.warning("⚠️ Google Sheets библиотеки не установлены. Используется placeholder режим.")

# Конфигурация
GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
# Spreadsheet ID из URL пользователя
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "1NF25EWqRxjdNTKk4VFVAYZGIOlVFfaktpEvvj1bRXKU")

# Кэш для данных (чтобы не читать каждый раз)
_services_cache = None
_services_cache_time = None
CACHE_TIMEOUT = 300  # 5 минут кэширования

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
    """Получить список мастеров из Google Sheets или placeholder"""
    client = get_sheets_client()
    
    if client:
        try:
            # Получаем мастеров из услуг (уникальные имена из колонок Мастер 1 и Мастер 2)
            services = get_services()
            master_names = set()
            
            for service in services:
                master1 = service.get("master1", "").strip()
                master2 = service.get("master2", "").strip()
                if master1:
                    master_names.add(master1)
                if master2:
                    master_names.add(master2)
            
            masters = []
            for idx, name in enumerate(sorted(master_names), 1):
                # Определяем тип зала по услугам
                master_services = [s for s in services if s.get("master1") == name or s.get("master2") == name]
                service_type = "Мужской зал" if any(s.get("type") == "men" for s in master_services) else "Женский зал"
                
                masters.append({
                    "id": idx,
                    "name": name,
                    "specialization": service_type,
                    "schedule": {
                        "daily_start": "11:00" if name == "Роман" else "09:00",
                        "daily_end": "21:00" if name == "Роман" else "20:00"
                    }
                })
            
            if masters:
                log.info(f"✅ Получено {len(masters)} мастеров из Google Sheets")
                return masters
        except Exception as e:
            log.error(f"❌ Ошибка чтения мастеров из Google Sheets: {e}")
    
    # Используем placeholder данные
    return PLACEHOLDER_MASTERS.copy()


def get_services(master_name: Optional[str] = None) -> List[Dict]:
    """Получить список услуг из Google Sheets 'Ценник' или placeholder"""
    global _services_cache, _services_cache_time
    
    client = get_sheets_client()
    
    # Проверяем кэш
    if _services_cache and _services_cache_time:
        cache_age = (datetime.now() - _services_cache_time).total_seconds()
        if cache_age < CACHE_TIMEOUT:
            log.debug(f"📋 Используем кэш услуг (возраст: {cache_age:.0f} сек)")
            services = _services_cache.copy()
            if master_name:
                services = [s for s in services if master_name.lower() in (s.get("master1", "") + " " + s.get("master2", "")).lower()]
            return services
    
    if client:
        try:
            spreadsheet = client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet("Ценник")
            
            # Получаем все данные
            all_values = worksheet.get_all_values()
            log.info(f"📋 Прочитано {len(all_values)} строк из листа 'Ценник'")
            
            services = []
            current_type = None
            service_id = 1
            
            # Парсим данные (пропускаем заголовок, если есть)
            for row_idx, row in enumerate(all_values[1:], start=2):  # Начинаем со 2-й строки
                if not row or len(row) < 2:
                    continue
                
                # Колонка A: Мужской зал / Женский зал
                col_a = row[0].strip() if len(row) > 0 else ""
                if col_a:
                    if "Мужской" in col_a or "мужской" in col_a:
                        current_type = "men"
                    elif "Женский" in col_a or "женский" in col_a:
                        current_type = "women"
                
                # Колонка B: Услуга название
                service_name = row[1].strip() if len(row) > 1 else ""
                if not service_name or not current_type:
                    continue
                
                # Колонка C: Мастер 1
                master1 = row[2].strip() if len(row) > 2 else ""
                # Колонка D: Мастер 2
                master2 = row[3].strip() if len(row) > 3 else ""
                
                # Колонка E: Цена (может быть диапазон "1000–2500")
                price_str = row[4].strip() if len(row) > 4 else "0"
                price = parse_price(price_str)
                
                # Колонка F: Время оказания (в мин.)
                duration_str = row[5].strip() if len(row) > 5 else "0"
                try:
                    duration = int(duration_str) if duration_str else 0
                except ValueError:
                    duration = 0
                
                # Колонка G: Доп. услуги
                additional_services = row[6].strip() if len(row) > 6 else ""
                
                service = {
                    "id": service_id,
                    "title": service_name,
                    "price": price,
                    "price_str": price_str,  # Сохраняем оригинальную строку для отображения
                    "duration": duration,
                    "master1": master1,
                    "master2": master2,
                    "master": master1 or master2,  # Основной мастер
                    "type": current_type,
                    "additional_services": additional_services,
                    "row_number": row_idx
                }
                
                services.append(service)
                service_id += 1
            
            # Обновляем кэш
            _services_cache = services
            _services_cache_time = datetime.now()
            log.info(f"✅ Получено {len(services)} услуг из Google Sheets")
            
            if master_name:
                services = [s for s in services if master_name.lower() in (s.get("master1", "") + " " + s.get("master2", "")).lower()]
            
            return services
            
        except Exception as e:
            log.error(f"❌ Ошибка чтения услуг из Google Sheets: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
    
    # Используем placeholder данные
    services = PLACEHOLDER_SERVICES.copy()
    if master_name:
        services = [s for s in services if s.get("master", "").lower() == master_name.lower()]
    
    return services


def parse_price(price_str: str) -> int:
    """Парсит цену из строки (может быть "1000", "1000–2500", "от 1000" и т.д.)"""
    if not price_str:
        return 0
    
    # Убираем пробелы и заменяем дефисы на тире
    price_str = price_str.replace("–", "-").replace("—", "-").strip()
    
    # Если есть диапазон, берем минимальное значение
    if "-" in price_str:
        parts = price_str.split("-")
        try:
            return int(parts[0].strip())
        except ValueError:
            return 0
    
    # Пытаемся извлечь число
    import re
    numbers = re.findall(r'\d+', price_str)
    if numbers:
        try:
            return int(numbers[0])
        except ValueError:
            return 0
    
    return 0


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
    """Создать запись в Google Sheets лист 'Запись' или placeholder"""
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
            spreadsheet = client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)
            
            # Пытаемся получить лист "Запись", если нет - создаем
            try:
                worksheet = spreadsheet.worksheet("Запись")
            except gspread.exceptions.WorksheetNotFound:
                log.info("📝 Лист 'Запись' не найден, создаю новый...")
                worksheet = spreadsheet.add_worksheet(title="Запись", rows=1000, cols=10)
                # Добавляем заголовки
                headers = ["Дата создания", "ID записи", "Дата", "Время", "Мастер", "Услуга", 
                          "Имя клиента", "Телефон", "Цена", "Статус", "Комментарий"]
                worksheet.append_row(headers)
            
            # Формируем строку для записи
            now = datetime.now()
            row_data = [
                now.strftime("%Y-%m-%d %H:%M:%S"),  # Дата создания
                booking_id,  # ID записи
                booking_data.get("date", ""),  # Дата записи
                booking_data.get("time", ""),  # Время записи
                booking_data.get("master", ""),  # Мастер
                booking_data.get("service", ""),  # Услуга
                booking_data.get("client_name", ""),  # Имя клиента
                booking_data.get("client_phone", ""),  # Телефон
                booking_data.get("price", 0),  # Цена
                booking_data.get("status", "confirmed"),  # Статус
                f"Запись через Telegram бот (user_id: {booking_data.get('user_id', 'N/A')})"  # Комментарий
            ]
            
            # Добавляем новую строку
            worksheet.append_row(row_data)
            log.info(f"✅ Запись {booking_id} успешно создана в Google Sheets (лист 'Запись')")
            
            # Инвалидируем кэш услуг при необходимости
            global _services_cache
            _services_cache = None
            
        except Exception as e:
            log.error(f"❌ Ошибка записи в Google Sheets: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            # Сохраняем в placeholder как fallback
            PLACEHOLDER_BOOKINGS.append(booking_record)
            log.warning("⚠️ Запись сохранена в placeholder (fallback)")
    else:
        # Сохраняем в placeholder
        PLACEHOLDER_BOOKINGS.append(booking_record)
        log.info(f"✅ Запись {booking_id} создана (placeholder режим)")
    
    return booking_record


def check_slot_available(master_name: str, date: str, time: str) -> bool:
    """Проверить доступность слота времени в Google Sheets листе 'Запись'"""
    client = get_sheets_client()
    
    if client:
        try:
            spreadsheet = client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)
            try:
                worksheet = spreadsheet.worksheet("Запись")
            except gspread.exceptions.WorksheetNotFound:
                # Листа еще нет - значит свободно
                return True
            
            # Получаем все записи (пропускаем заголовок)
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:
                return True
            
            # Проверяем конфликты по мастеру, дате и времени
            for row in all_values[1:]:  # Пропускаем заголовок
                if len(row) < 5:
                    continue
                row_master = row[4].strip() if len(row) > 4 else ""  # Колонка E - Мастер
                row_date = row[2].strip() if len(row) > 2 else ""  # Колонка C - Дата
                row_time = row[3].strip() if len(row) > 3 else ""  # Колонка D - Время
                row_status = row[9].strip() if len(row) > 9 else "confirmed"  # Колонка J - Статус
                
                # Пропускаем отмененные записи
                if "отмен" in row_status.lower() or "cancel" in row_status.lower():
                    continue
                
                if (row_master.lower() == master_name.lower() and
                    row_date == date and
                    row_time == time):
                    log.info(f"⚠️ Слот занят: {master_name} {date} {time}")
                    return False
            
            return True
            
        except Exception as e:
            log.error(f"❌ Ошибка проверки слота в Google Sheets: {e}")
            # При ошибке считаем что свободно (можно записаться)
            return True
    
    # Placeholder: проверяем в памяти
    for booking in PLACEHOLDER_BOOKINGS:
        if (booking.get("master", "").lower() == master_name.lower() and
            booking.get("date") == date and
            booking.get("time") == time):
            return False
    
    return True


def refresh_services_cache():
    """Принудительно обновить кэш услуг (вызывать при необходимости)"""
    global _services_cache, _services_cache_time
    _services_cache = None
    _services_cache_time = None
    log.info("🔄 Кэш услуг очищен")


