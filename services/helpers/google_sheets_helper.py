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

# Загружаем конфигурацию из config.yaml
from pathlib import Path
import sys
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config import load_config

_gs_config = load_config("google_sheets")
_gs_settings = _gs_config.get("google_sheets", {})

# Конфигурация из config.yaml
GOOGLE_SHEETS_CREDENTIALS_PATH = _gs_settings.get("credentials_path") or os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
GOOGLE_SHEETS_CREDENTIALS_JSON = _gs_settings.get("credentials_json") or os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")  # JSON напрямую из переменной (для Railway)
# Spreadsheet ID из URL пользователя
GOOGLE_SHEETS_SPREADSHEET_ID = _gs_settings.get("spreadsheet_id") or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "1NF25EWqRxjdNTKk4VFVAYZGIOlVFfaktpEvvj1bRXKU")

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
            service_type = "HR-специалист" if any(s.get("type") == "men" for s in master_services) else "HR-специалист"
            
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
            
            # Получаем все данные - используем get_all_values() для получения всех строк
            all_values = worksheet.get_all_values()
            log.info(f"📋 Прочитано {len(all_values)} строк из листа 'Ценник'")
            if len(all_values) > 0:
                log.info(f"📋 Первая строка (заголовок): {all_values[0]}")
                # Логируем первые 10 строк для отладки
                log.info(f"📋 Первые 10 строк из Google Sheets:")
                for i, row in enumerate(all_values[:10], 1):
                    # Показываем первые 7 колонок (A-G)
                    row_preview = row[:7] if len(row) >= 7 else row
                    log.info(f"   Строка {i}: A='{row[0] if len(row) > 0 else ''}', B='{row[1] if len(row) > 1 else ''}', C='{row[2] if len(row) > 2 else ''}', D='{row[3] if len(row) > 3 else ''}', E='{row[4] if len(row) > 4 else ''}', F='{row[5] if len(row) > 5 else ''}', G='{row[6] if len(row) > 6 else ''}'")
            
            services = []
            current_type = None
            service_id = 1
            
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: В строке 1 заголовок "Мужской зал" в колонке A,
            # но в строках 2-15 колонка A пустая! Нужно использовать заголовок из строки 1.
            # Проверяем заголовок в строке 1
            if len(all_values) > 0:
                header_row = all_values[0]
                header_col_a = header_row[0].strip() if len(header_row) > 0 else ""
                if "Мужской" in header_col_a or "мужской" in header_col_a or "men" in header_col_a.lower():
                    current_type = "men"
                    log.info(f"📋 Найдена секция в заголовке: Отдел Романа (строка 1)")
                elif "Женский" in header_col_a or "женский" in header_col_a or "women" in header_col_a.lower():
                    current_type = "women"
                    log.info(f"📋 Найдена секция в заголовке: Отдел Анжелы (строка 1)")
            
            # Парсим данные (пропускаем заголовок, если есть)
            # ВАЖНО: Строка 1 - это заголовок, строка 2+ - данные
            for row_idx, row in enumerate(all_values[1:], start=2):  # Начинаем со 2-й строки (пропускаем заголовок)
                if not row or len(row) < 2:
                    continue
                
                # Колонка A: Тип услуги / Отдел (может быть заголовок секции)
                col_a = row[0].strip() if len(row) > 0 else ""
                # Колонка B: Услуга название
                service_name = row[1].strip() if len(row) > 1 else ""
                
                # КРИТИЧЕСКОЕ: Если колонка A содержит заголовок секции, обновляем current_type
                # Если колонка A пустая, используем последний установленный current_type
                if col_a:
                    if "Мужской" in col_a or "мужской" in col_a or "men" in col_a.lower():
                        current_type = "men"
                        log.debug(f"📋 Найдена секция: Отдел Романа (строка {row_idx})")
                    elif "Женский" in col_a or "женский" in col_a or "women" in col_a.lower():
                        current_type = "women"
                        log.debug(f"📋 Найдена секция: Отдел Анжелы (строка {row_idx})")
                    
                    # Если колонка A содержит заголовок секции, но услуга тоже есть в этой строке
                    # (в колонке B), обрабатываем услугу дальше
                    # Если услуги нет в этой строке, просто обновляем current_type и переходим к следующей строке
                    if not service_name:
                        continue  # Это заголовок секции без услуги, пропускаем
                
                # Если название услуги отсутствует, пропускаем строку
                if not service_name:
                    continue
                
                # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Если current_type не установлен, НЕ пропускаем!
                # Используем последний установленный current_type (из заголовка или предыдущей строки)
                if not current_type:
                    log.warning(f"⚠️ Пропущена услуга '{service_name}' (строка {row_idx}) - секция не определена (col_a='{col_a}')")
                    continue
                
                # КРИТИЧЕСКОЕ: Структура Google Sheets (согласно таблице):
                # Строка 1 (заголовок): A="Мужской зал", B="Услуга название", C="Мастер 1", D="Мастер 2", E="Цена", F="Время", G="Доп. услуги"
                # Строка 2 (данные): A="Мужской зал", B="Бритье головы", C="Роман", D=пусто, E="1700", F="60", G="Камуфляж..."
                # Значит: row[0]=A, row[1]=B, row[2]=C, row[3]=D, row[4]=E, row[5]=F, row[6]=G
                
                # Колонка C: Мастер 1 (row[2])
                master1 = row[2].strip() if len(row) > 2 else ""
                # Колонка D: Мастер 2 (может быть пусто) (row[3])
                master2 = row[3].strip() if len(row) > 3 else ""
                
                # Колонка E: Цена (может быть диапазон "1000–2500") (row[4]) - ВАЖНО: это row[4], не row[3]!
                price_str = row[4].strip() if len(row) > 4 else "0"
                price = parse_price(price_str)
                
                # Колонка F: Время оказания (в мин.) (row[5]) - ВАЖНО: это row[5], не row[4]!
                duration_str = row[5].strip() if len(row) > 5 else "0"
                try:
                    duration = int(duration_str) if duration_str else 0
                except ValueError:
                    duration = 0
                
                # Колонка G: Доп. услуги (row[6])
                additional_services = row[6].strip() if len(row) > 6 else ""
                
                # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ для "Бритье головы" для отладки
                if "бритье" in service_name.lower() and "голов" in service_name.lower():
                    log.info(f"🔍🔍🔍 ОБРАБОТКА 'Бритье головы' (строка {row_idx}):")
                    log.info(f"   row[0] (A, col_a): '{col_a}'")
                    log.info(f"   row[1] (B, service_name): '{service_name}'")
                    log.info(f"   row[2] (C, master1): '{master1}'")
                    log.info(f"   row[3] (D, master2): '{master2}'")
                    log.info(f"   row[4] (E, price_str): '{price_str}' -> parse_price() -> {price}₽")
                    log.info(f"   row[5] (F, duration_str): '{duration_str}' -> int() -> {duration} мин")
                    log.info(f"   row[6] (G, additional_services): '{additional_services}'")
                    log.info(f"   current_type: '{current_type}'")
                    log.info(f"   ОЖИДАЕТСЯ: price=1700, duration=60, master='Роман'")
                    if price != 1700:
                        log.error(f"   ❌❌❌ КРИТИЧЕСКАЯ ОШИБКА: price={price}, ожидается 1700! Проверьте row[4]!")
                    if duration != 60:
                        log.error(f"   ❌❌❌ КРИТИЧЕСКАЯ ОШИБКА: duration={duration}, ожидается 60! Проверьте row[5]!")
                    if "роман" not in master1.lower():
                        log.error(f"   ❌❌❌ КРИТИЧЕСКАЯ ОШИБКА: master1='{master1}', ожидается 'Роман'! Проверьте row[2]!")
                    else:
                        log.info(f"   ✅✅✅ ВСЕ ПРАВИЛЬНО: price={price}₽, duration={duration} мин, master='{master1}'")
                
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
            log.info(f"📊 Статистика: Отдел Романа - {len(men_services)} услуг, Отдел Анжелы - {len(women_services)} услуг")
            
            # КРИТИЧЕСКОЕ: Логируем ВСЕ услуги для диагностики
            log.info(f"📋 ВСЕ НАЙДЕННЫЕ УСЛУГИ ({len(services)} шт.):")
            for s in services:
                log.info(f"  Строка {s.get('row_number')}: '{s.get('title')}' ({s.get('type')}) - {s.get('price_str')}₽ - {s.get('duration')} мин - мастер: '{s.get('master')}'")
            
            # Логируем первые несколько услуг для проверки
            log.info("📋 Первые услуги из Мужского зала:")
            for s in men_services[:5]:
                log.info(f"  📋 {s.get('title')} - цена: '{s.get('price_str')}' ({s.get('price')}₽) - {s.get('duration')} мин - мастер: {s.get('master')}")
            
            log.info("📋 Первые услуги из Женского зала:")
            for s in women_services[:5]:
                log.info(f"  📋 {s.get('title')} - цена: '{s.get('price_str')}' ({s.get('price')}₽) - {s.get('duration')} мин - мастер: {s.get('master')}")
            
            # Проверяем конкретно "Бритье головы" и логируем ВСЕ услуги для отладки
            briтье_услуги = [s for s in services if "бритье" in s.get('title', '').lower() and "голов" in s.get('title', '').lower()]
            if briтье_услуги:
                for s in briтье_услуги:
                    log.info(f"  🔍 НАЙДЕНО 'Бритье головы': {s.get('title')} - цена: '{s.get('price_str')}' ({s.get('price')}₽) - строка {s.get('row_number')}")
            else:
                log.warning("⚠️ Услуга 'Бритье головы' не найдена!")
                log.warning(f"⚠️ Всего найдено услуг: {len(services)}")
                log.warning(f"⚠️ Услуги с 'бритье': {[s.get('title') for s in services if 'бритье' in s.get('title', '').lower()]}")
            
            # Логируем ВСЕ названия услуг для проверки (первые 30)
            log.info(f"📋 ВСЕ НАЙДЕННЫЕ УСЛУГИ ({len(services)} шт., показываю первые 30):")
            for s in services[:30]:
                log.info(f"  Строка {s.get('row_number')}: '{s.get('title')}' ({s.get('type')}) - {s.get('price_str')}₽")
            if len(services) > 30:
                log.info(f"  ... и еще {len(services) - 30} услуг")
            
            # Автоматически обновляем индекс в Qdrant в фоне (не блокируем чтение данных)
            try:
                import threading
                def update_qdrant_index():
                    try:
                        from services.rag.qdrant_helper import index_services as qdrant_index
                        if qdrant_index(services):
                            log.info(f"✅ Индекс Qdrant обновлен автоматически ({len(services)} услуг)")
                    except Exception as e:
                        log.warning(f"⚠️ Не удалось обновить индекс Qdrant: {e}")
                
                # Запускаем обновление индекса в фоне
                index_thread = threading.Thread(target=update_qdrant_index, daemon=True)
                index_thread.start()
            except Exception as e:
                log.warning(f"⚠️ Не удалось запустить обновление индекса Qdrant: {e}")
            
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


def get_user_bookings(user_id: int) -> List[Dict]:
    """Получить все записи пользователя из Google Sheets"""
    client = get_sheets_client()
    
    if not client:
        log.error("❌ Google Sheets не настроены для получения записей")
        return []
    
    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)
        try:
            worksheet = spreadsheet.worksheet("Запись")
        except gspread.exceptions.WorksheetNotFound:
            log.info("📝 Лист 'Запись' не найден, записей нет")
            return []
        
        # Получаем все записи (пропускаем заголовок)
        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:
            return []
        
        user_bookings = []
        # Структура: ["Дата создания", "ID записи", "Дата", "Время", "Мастер", "Услуга", 
        #            "Имя клиента", "Телефон", "Цена", "Статус", "Комментарий"]
        for row_idx, row in enumerate(all_values[1:], start=2):  # Пропускаем заголовок
            if len(row) < 11:
                continue
            
            # Извлекаем user_id из комментария (формат: "Запись через Telegram бот (user_id: 123456)")
            comment = row[10].strip() if len(row) > 10 else ""
            row_user_id = None
            if "user_id:" in comment.lower():
                try:
                    user_id_part = comment.split("user_id:")[1].split(")")[0].strip()
                    row_user_id = int(user_id_part)
                except (ValueError, IndexError):
                    pass
            
            # Проверяем, что запись принадлежит пользователю
            if row_user_id == user_id:
                booking_id = row[1].strip() if len(row) > 1 else ""
                status = row[9].strip() if len(row) > 9 else "confirmed"
                
                # Пропускаем отмененные записи
                if "отмен" in status.lower() or "cancel" in status.lower():
                    continue
                
                booking = {
                    "id": booking_id,
                    "date": row[2].strip() if len(row) > 2 else "",
                    "time": row[3].strip() if len(row) > 3 else "",
                    "datetime": f"{row[2].strip()} {row[3].strip()}" if len(row) > 3 else row[2].strip(),
                    "master": row[4].strip() if len(row) > 4 else "",
                    "service": row[5].strip() if len(row) > 5 else "",
                    "client_name": row[6].strip() if len(row) > 6 else "",
                    "client_phone": row[7].strip() if len(row) > 7 else "",
                    "price": int(row[8]) if len(row) > 8 and row[8].strip().isdigit() else 0,
                    "status": status,
                    "created_at": row[0].strip() if len(row) > 0 else "",
                    "row_number": row_idx  # Номер строки в Google Sheets для удаления
                }
                user_bookings.append(booking)
        
        # Сортируем по дате (новые сначала)
        user_bookings.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        log.info(f"✅ Найдено {len(user_bookings)} записей для user_id={user_id}")
        return user_bookings
        
    except Exception as e:
        log.error(f"❌ Ошибка получения записей пользователя из Google Sheets: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return []


def delete_user_booking(user_id: int, booking_id: str) -> bool:
    """Удалить запись пользователя из Google Sheets (только свои записи)"""
    client = get_sheets_client()
    
    if not client:
        log.error("❌ Google Sheets не настроены для удаления записи")
        return False
    
    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)
        try:
            worksheet = spreadsheet.worksheet("Запись")
        except gspread.exceptions.WorksheetNotFound:
            log.warning("📝 Лист 'Запись' не найден")
            return False
        
        # Получаем все записи
        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:
            return False
        
        # Ищем запись с нужным ID и проверяем, что она принадлежит пользователю
        for row_idx, row in enumerate(all_values[1:], start=2):  # Пропускаем заголовок
            if len(row) < 11:
                continue
            
            row_booking_id = row[1].strip() if len(row) > 1 else ""
            if row_booking_id != booking_id:
                continue
            
            # Проверяем, что запись принадлежит пользователю
            comment = row[10].strip() if len(row) > 10 else ""
            row_user_id = None
            if "user_id:" in comment.lower():
                try:
                    user_id_part = comment.split("user_id:")[1].split(")")[0].strip()
                    row_user_id = int(user_id_part)
                except (ValueError, IndexError):
                    pass
            
            if row_user_id != user_id:
                log.warning(f"⚠️ Попытка удалить чужую запись: user_id={user_id}, booking_id={booking_id}")
                return False
            
            # Удаляем строку (используем delete_rows, индексация с 1)
            worksheet.delete_rows(row_idx)
            log.info(f"✅ Запись {booking_id} успешно удалена из Google Sheets (строка {row_idx})")
            return True
        
        log.warning(f"⚠️ Запись {booking_id} не найдена")
        return False
        
    except Exception as e:
        log.error(f"❌ Ошибка удаления записи из Google Sheets: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return False


