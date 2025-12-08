"""
Google Sheets интеграция для хранения записей и расписания
ВАЖНО: Используются ТОЛЬКО данные из Google Sheets, без fallback на placeholder.
Если Google Sheets недоступны - бот не может работать.
"""
import os
import json
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
GOOGLE_SHEETS_CREDENTIALS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")  # JSON напрямую из переменной (для Railway)
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
    
    if not GOOGLE_SHEETS_SPREADSHEET_ID:
        log.warning("Google Sheets не настроены - используем placeholder")
        return None
    
    # Проверяем наличие credentials (либо путь к файлу, либо JSON)
    if not GOOGLE_SHEETS_CREDENTIALS_PATH and not GOOGLE_SHEETS_CREDENTIALS_JSON:
        log.warning("Google Sheets не настроены - используем placeholder (нет credentials)")
        return None
    
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        # Приоритет: JSON из переменной окружения (для Railway), затем файл
        if GOOGLE_SHEETS_CREDENTIALS_JSON:
            log.info("📋 Используем credentials из переменной окружения GOOGLE_SHEETS_CREDENTIALS_JSON")
            creds_data = json.loads(GOOGLE_SHEETS_CREDENTIALS_JSON)
            creds = Credentials.from_service_account_info(creds_data, scopes=scope)
        elif GOOGLE_SHEETS_CREDENTIALS_PATH:
            log.info(f"📋 Используем credentials из файла: {GOOGLE_SHEETS_CREDENTIALS_PATH}")
            creds = Credentials.from_service_account_file(
                GOOGLE_SHEETS_CREDENTIALS_PATH, scopes=scope)
        else:
            log.warning("Google Sheets не настроены - нет credentials")
            return None
        
        _sheets_client = gspread.authorize(creds)
        log.info("✅ Google Sheets клиент успешно инициализирован")
        return _sheets_client
    except json.JSONDecodeError as e:
        log.error(f"❌ Ошибка парсинга JSON credentials: {e}")
        return None
    except Exception as e:
        log.error(f"❌ Ошибка инициализации Google Sheets: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return None


# ===================== ВАЖНО: PLACEHOLDER ДАННЫЕ УДАЛЕНЫ =====================
# Все данные ТОЛЬКО из Google Sheets. Бот не работает без доступа к таблице.
# Если Google Sheets недоступны - бот выдает ошибку, а не использует placeholder данные.


# ===================== ФУНКЦИИ РАБОТЫ С ДАННЫМИ =====================

def get_masters() -> List[Dict]:
    """Получить список мастеров из Google Sheets (ТОЛЬКО из Google Sheets, без fallback)"""
    client = get_sheets_client()
    
    if not client:
        error_msg = (
            "❌ КРИТИЧЕСКАЯ ОШИБКА: Google Sheets клиент не инициализирован!\n"
            "Не удалось получить список мастеров.\n"
            "Убедитесь, что Google Sheets настроены правильно."
        )
        log.error(error_msg)
        raise Exception(error_msg)
    
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
        
        if not masters:
            error_msg = "❌ КРИТИЧЕСКАЯ ОШИБКА: Не найдено ни одного мастера в Google Sheets!"
            log.error(error_msg)
            raise Exception(error_msg)
        
        log.info(f"✅ Получено {len(masters)} мастеров из Google Sheets")
        return masters
    except Exception as e:
        log.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА чтения мастеров из Google Sheets: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        raise


def get_services(master_name: Optional[str] = None) -> List[Dict]:
    """Получить список услуг из Google Sheets 'Ценник' (ТОЛЬКО из Google Sheets, без fallback)"""
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
            log.info(f"🔗 Подключение к Google Sheets (ID: {GOOGLE_SHEETS_SPREADSHEET_ID})")
            spreadsheet = client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet("Ценник")
            
            # Получаем все данные
            all_values = worksheet.get_all_values()
            log.info(f"📋 Прочитано {len(all_values)} строк из листа 'Ценник'")
            if len(all_values) > 0:
                log.info(f"📋 Первая строка (заголовок): {all_values[0]}")
            
            services = []
            current_type = None
            service_id = 1
            
            # Парсим данные (пропускаем заголовок, если есть)
            for row_idx, row in enumerate(all_values[1:], start=2):  # Начинаем со 2-й строки
                if not row or len(row) < 2:
                    continue
                
                # Колонка A: Мужской зал / Женский зал
                # Если в колонке A есть текст, это заголовок секции - обновляем current_type
                col_a = row[0].strip() if len(row) > 0 else ""
                if col_a:
                    if "Мужской" in col_a or "мужской" in col_a:
                        current_type = "men"
                        log.debug(f"📋 Найдена секция: Мужской зал (строка {row_idx})")
                    elif "Женский" in col_a or "женский" in col_a:
                        current_type = "women"
                        log.debug(f"📋 Найдена секция: Женский зал (строка {row_idx})")
                    # Если колонка A заполнена, но это не секция, пропускаем (это может быть подзаголовок)
                    continue
                
                # Если колонка A пустая, проверяем есть ли услуга в колонке B
                # Колонка B: Услуга название
                service_name = row[1].strip() if len(row) > 1 else ""
                if not service_name:
                    continue
                
                # Если current_type не установлен, пропускаем (пока не нашли секцию)
                if not current_type:
                    log.debug(f"⚠️ Пропущена услуга '{service_name}' (строка {row_idx}) - секция не определена")
                    continue
                
                # Колонка C: Мастер 1
                master1 = row[2].strip() if len(row) > 2 else ""
                # Колонка D: Мастер 2 (может быть пусто)
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
            
            if not services:
                error_msg = "❌ КРИТИЧЕСКАЯ ОШИБКА: Не найдено ни одной услуги в Google Sheets (лист 'Ценник')!"
                log.error(error_msg)
                raise Exception(error_msg)
            
            if not services:
                error_msg = "❌ КРИТИЧЕСКАЯ ОШИБКА: Не найдено ни одной услуги в Google Sheets (лист 'Ценник')!"
                log.error(error_msg)
                raise Exception(error_msg)
            
            # Обновляем кэш
            _services_cache = services
            _services_cache_time = datetime.now()
            log.info(f"✅ Получено {len(services)} услуг из Google Sheets")
            
            # Логируем статистику по типам услуг
            men_services = [s for s in services if s.get('type') == 'men']
            women_services = [s for s in services if s.get('type') == 'women']
            log.info(f"📊 Статистика: Мужской зал - {len(men_services)} услуг, Женский зал - {len(women_services)} услуг")
            
            # Логируем первые несколько услуг для проверки
            log.info("📋 Первые услуги из Мужского зала:")
            for s in men_services[:5]:
                log.info(f"  📋 {s.get('title')} - цена: '{s.get('price_str')}' ({s.get('price')}₽) - {s.get('duration')} мин - мастер: {s.get('master')}")
            
            log.info("📋 Первые услуги из Женского зала:")
            for s in women_services[:5]:
                log.info(f"  📋 {s.get('title')} - цена: '{s.get('price_str')}' ({s.get('price')}₽) - {s.get('duration')} мин - мастер: {s.get('master')}")
            
            # Проверяем конкретно "Бритье головы"
            briтье_услуги = [s for s in services if "бритье" in s.get('title', '').lower() and "голов" in s.get('title', '').lower()]
            if briтье_услуги:
                for s in briтье_услуги:
                    log.info(f"  🔍 НАЙДЕНО 'Бритье головы': {s.get('title')} - цена: '{s.get('price_str')}' ({s.get('price')}₽)")
            else:
                log.warning("⚠️ Услуга 'Бритье головы' не найдена!")
            
            # Автоматически обновляем индекс в Qdrant
            try:
                from qdrant_helper import index_services as qdrant_index
                if qdrant_index(services):
                    log.info("✅ Индекс Qdrant обновлен автоматически")
            except Exception as e:
                log.warning(f"⚠️ Не удалось обновить индекс Qdrant: {e}")
            
            if master_name:
                filtered_services = [s for s in services if master_name.lower() in (s.get("master1", "") + " " + s.get("master2", "")).lower()]
                if not filtered_services:
                    log.warning(f"⚠️ Не найдено услуг для мастера '{master_name}' в Google Sheets")
                return filtered_services
            
            return services
            
        except Exception as e:
            log.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА чтения услуг из Google Sheets: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            raise Exception(f"Не удалось прочитать услуги из Google Sheets: {e}")
    
    # КРИТИЧЕСКАЯ ОШИБКА: Google Sheets не настроены
    error_msg = (
        "❌ КРИТИЧЕСКАЯ ОШИБКА: Google Sheets не настроены или недоступны!\n"
        "Бот не может работать без доступа к таблице.\n"
        "Убедитесь, что установлены:\n"
        "- GOOGLE_SHEETS_CREDENTIALS_JSON (для Railway)\n"
        "- или GOOGLE_SHEETS_CREDENTIALS_PATH (для локальной разработки)"
    )
    log.error(error_msg)
    raise Exception(error_msg)


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
    """Получить доступные слоты времени для мастера на дату (из Google Sheets)"""
    client = get_sheets_client()
    
    if not client:
        error_msg = "❌ КРИТИЧЕСКАЯ ОШИБКА: Google Sheets не настроены для получения расписания!"
        log.error(error_msg)
        raise Exception(error_msg)
    
    try:
        # Получаем расписание мастера из реальных данных
        masters = get_masters()
        master = next((m for m in masters if m.get("name", "").lower() == master_name.lower()), None)
        
        if not master:
            error_msg = f"❌ ОШИБКА: Мастер '{master_name}' не найден в Google Sheets!"
            log.error(error_msg)
            raise Exception(error_msg)
        
        schedule = master.get("schedule", {})
        start_time = datetime.strptime(schedule.get("daily_start", "09:00"), "%H:%M")
        end_time = datetime.strptime(schedule.get("daily_end", "20:00"), "%H:%M")
        
        slots = []
        current = start_time
        while current < end_time:
            slots.append(current.strftime("%H:%M"))
            current += timedelta(hours=1)
        
        return slots
    except Exception as e:
        log.error(f"❌ Ошибка получения расписания из Google Sheets: {e}")
        raise


def create_booking(booking_data: Dict) -> Dict:
    """Создать запись в Google Sheets лист 'Запись' (ТОЛЬКО в Google Sheets, без fallback)"""
    import uuid
    client = get_sheets_client()
    
    booking_id = str(uuid.uuid4())  # Генерируем уникальный ID
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
            error_msg = f"❌ КРИТИЧЕСКАЯ ОШИБКА записи в Google Sheets: {e}"
            log.error(error_msg)
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            raise Exception(error_msg)
    else:
        error_msg = (
            "❌ КРИТИЧЕСКАЯ ОШИБКА: Google Sheets не настроены!\n"
            "Не удалось создать запись. Бот не может работать без доступа к таблице."
        )
        log.error(error_msg)
        raise Exception(error_msg)
    
    return booking_record


def check_slot_available(master_name: str, date: str, time: str) -> bool:
    """Проверить доступность слота времени в Google Sheets листе 'Запись' (ТОЛЬКО из Google Sheets)"""
    client = get_sheets_client()
    
    if not client:
        error_msg = "❌ КРИТИЧЕСКАЯ ОШИБКА: Google Sheets не настроены для проверки доступности!"
        log.error(error_msg)
        raise Exception(error_msg)
    
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
            error_msg = f"❌ КРИТИЧЕСКАЯ ОШИБКА проверки слота в Google Sheets: {e}"
            log.error(error_msg)
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            raise Exception(error_msg)
    
    # КРИТИЧЕСКАЯ ОШИБКА: Google Sheets не настроены
    error_msg = "❌ КРИТИЧЕСКАЯ ОШИБКА: Google Sheets не настроены для проверки доступности!"
    log.error(error_msg)
    raise Exception(error_msg)


def refresh_services_cache():
    """Принудительно обновить кэш услуг (вызывать при необходимости)"""
    global _services_cache, _services_cache_time
    _services_cache = None
    _services_cache_time = None
    log.info("🔄 Кэш услуг очищен")


