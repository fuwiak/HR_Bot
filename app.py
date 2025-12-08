# bot.py
import os
import re
import time
import logging
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from typing import Dict, Deque, List, Tuple

import requests
from dotenv import load_dotenv
from telegram import Update, Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ===================== LOAD .ENV ======================
load_dotenv()  # <-- loads variables from .env file

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# OpenRouter API URL - правильный формат
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")

# ===================== VALIDATION =====================
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Ошибка: Отсутствует TELEGRAM_TOKEN в .env")
if not OPENROUTER_API_KEY:
    raise ValueError("Ошибка: Отсутствует OPENROUTER_API_KEY в .env")

# ===================== CONFIG =========================
# Модель OpenRouter - можно переопределить через переменную окружения
# Попробуйте также: "x-ai/grok-beta", "x-ai/grok-2-1212", "grok-beta"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "x-ai/grok-4.1-fast:free")
MEMORY_TURNS = 6

# Валидация при старте
if OPENROUTER_API_URL and not OPENROUTER_API_URL.startswith("https://"):
    logging.warning(f"⚠️ Подозрительный URL OpenRouter: {OPENROUTER_API_URL}")

# Google Sheets конфигурация
GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
# Spreadsheet ID из URL: https://docs.google.com/spreadsheets/d/1NF25EWqRxjdNTKk4VFVAYZGIOlVFfaktpEvvj1bRXKU
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "1NF25EWqRxjdNTKk4VFVAYZGIOlVFfaktpEvvj1bRXKU")
USE_GOOGLE_SHEETS = bool(GOOGLE_SHEETS_CREDENTIALS_PATH and GOOGLE_SHEETS_SPREADSHEET_ID)

BOOKING_KEYWORDS = [
    "запись", "записаться", "записать", "забронировать",
    "услуга", "мастер", "время", "дата",
    "когда можно", "свободное время", "расписание",
    "записаться на", "хочу записаться", "нужна запись",
    "стрижка", "маникюр", "педикюр", "массаж", "окрашивание", "тонировка",
    "роман", "анжела",  # имена мастеров
    "коротко", "под машинку", "мужская", "женская",
    "октября", "ноября", "декабря", "января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября",
    ":", "часов", "в ", "на ", "завтра", "сегодня", "послезавтра"
]

BOOKING_PROMPT = """
Ты дружелюбный помощник по записи в салон красоты. Общайся на "вы", кратко и по делу, используй эмодзи.

КРИТИЧЕСКИ ВАЖНО - СТРОГО СЛЕДУЙ ИНСТРУКЦИЯМ:
- Используй ТОЛЬКО цены и данные из списка услуг ниже
- НИКОГДА не выдумывай цены самостоятельно
- Если услуга найдена в списке - используй ТОЧНУЮ цену из списка
- Если услуга не найдена - скажи что услуга недоступна

В салоне 2 мастера: Роман (мужской зал) и Анжела (женский зал)
- Различай мужские и женские услуги для корректной записи
- "Коротко подстричься" = "стрижка под машинку" (мужская услуга)

Правила записи:
- Запись "стык в стык" разрешена
- Запись "на сейчас" возможна при наличии времени
- Допустимое опоздание - 10 минут
- Клиенты могут отменить или перенести запись

Скидки:
- Первый визит (мужской зал): 25%
- По запросу (исключительно): 10%
- День рождения (мужской зал): 25%

Акции:
- "Приведи друга" - бонус 500 рублей
- "Воск комплекс за отзыв" - бесплатно за отзыв на Яндекс.Картах

История разговора:
{{history}}

Доступные услуги и мастера (используй ТОЛЬКО эти данные):
{{api_data}}

{{service_info}}

Сообщение пользователя: {{message}}

Если есть все данные (услуга, мастер, дата, время) - ответь:
ЗАПИСЬ: [услуга] | [мастер] | [дата время]

Если данных недостаточно - уточни кратко, используя эмодзи.
"""

CHAT_PROMPT = """
Ты дружелюбный помощник салона красоты. Общайся на "вы", кратко и по делу, используй эмодзи для дружелюбия.

История чата:
{{history}}

Сообщение:
{{message}}

Ответь кратко, дружелюбно, по делу.
"""

COMPLAINT_PROMPT = """
Клиент выражает недовольство или жалобу. Вежливо извинись, попроси уточнить детали, 
и сообщи что передашь информацию ответственному мастеру. Будь тактичным и старайся сгладить ситуацию.

История:
{{history}}

Сообщение:
{{message}}

Ответь вежливо, извинись, уточни детали.
"""

# ===================== LOGGING ========================
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger()

# ===================== MEMORY =========================
UserMemory: Dict[int, Deque] = defaultdict(lambda: deque(maxlen=MEMORY_TURNS * 2))
UserRecords: Dict[int, List[Dict]] = defaultdict(list)  # Хранилище записей пользователей
UserAuth: Dict[int, Dict] = defaultdict(dict)  # Данные авторизации пользователей
UserPhone: Dict[int, str] = {}  # Номера телефонов пользователей

def add_memory(user_id, role, text):
    UserMemory[user_id].append((role, text))

def get_history(user_id):
    return "\n".join([f"{r}: {t}" for r, t in UserMemory[user_id]])

# ===================== NLP ============================
def is_booking(text):
    text_lower = text.lower()
    matches = [k for k in BOOKING_KEYWORDS if k in text_lower]
    log.info(f"🔍 BOOKING CHECK: '{text}' -> matches: {matches}")
    return len(matches) > 0

def openrouter_chat(messages):
    """Отправка запроса в OpenRouter API для генерации ответа"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/RomanBot",  # Опционально, для отслеживания
        "X-Title": "RomanBot"  # Опционально
    }
    data = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": 1500,
        "temperature": 0.7
    }
    try:
        log.info(f"🌐 Отправка запроса к OpenRouter: {OPENROUTER_API_URL}, модель: {OPENROUTER_MODEL}")
        r = requests.post(OPENROUTER_API_URL, json=data, headers=headers, timeout=30)
        
        # Логируем статус ответа
        log.info(f"📡 Статус ответа OpenRouter: {r.status_code}")
        
        if r.status_code == 404:
            error_text = r.text
            log.error(f"❌ 404 Not Found - проверьте URL и модель")
            log.error(f"❌ URL: {OPENROUTER_API_URL}")
            log.error(f"❌ Модель: {OPENROUTER_MODEL}")
            log.error(f"❌ Ответ сервера: {error_text}")
            
            # Попытка использовать альтернативную модель если текущая недоступна
            if "model" in error_text.lower() or "not found" in error_text.lower():
                log.warning(f"⚠️ Модель {OPENROUTER_MODEL} недоступна. Проверьте список доступных моделей на https://openrouter.ai/models")
                log.warning(f"⚠️ Попробуйте установить OPENROUTER_MODEL=x-ai/grok-beta или другую доступную модель")
            
            return "Извините, произошла ошибка подключения к сервису. Пожалуйста, попробуйте позже."
        
        r.raise_for_status()
        response = r.json()
        
        if "choices" in response and len(response["choices"]) > 0:
            content = response["choices"][0]["message"]["content"]
            log.info(f"✅ Получен ответ от OpenRouter: {content[:100]}...")
            return content
        else:
            log.error(f"❌ Неожиданный формат ответа OpenRouter: {response}")
            return "Извините, произошла ошибка при обработке запроса."
    except requests.exceptions.HTTPError as e:
        log.error(f"❌ HTTP ошибка при запросе к OpenRouter API: {e}")
        log.error(f"❌ Статус: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
        log.error(f"❌ Ответ: {e.response.text if hasattr(e, 'response') and e.response else 'N/A'}")
        return "Извините, временно недоступно. Попробуйте позже."
    except requests.exceptions.RequestException as e:
        log.error(f"❌ Ошибка запроса к OpenRouter API: {e}")
        log.error(f"❌ Тип ошибки: {type(e).__name__}")
        return "Извините, временно недоступно. Попробуйте позже."
    except Exception as e:
        log.error(f"❌ Неожиданная ошибка: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return "Извините, произошла ошибка. Попробуйте позже."

# ===================== GOOGLE SHEETS INTEGRATION ===========
from google_sheets_helper import (
    get_masters as get_masters_from_sheets,
    get_services as get_services_from_sheets,
    create_booking as create_booking_in_sheets,
    check_slot_available,
    get_available_slots
)

# ===================== QDRANT VECTOR DATABASE ===========
try:
    from qdrant_helper import search_service, index_services, refresh_index
    QDRANT_AVAILABLE = True
    log.info("✅ Qdrant модуль загружен")
except ImportError as e:
    QDRANT_AVAILABLE = False
    log.warning(f"⚠️ Qdrant модуль не доступен: {e}")
    def search_service(query: str, limit: int = 3):
        return []
    def index_services(services):
        return False
    def refresh_index():
        return False

def get_services(master_name: str = None) -> List[Dict]:
    """Get available services, optionally filtered by master"""
    log.info(f"📋 Получение услуг (мастер: {master_name or 'все'})...")
    try:
        services = get_services_from_sheets(master_name)
        log.info(f"✅ Найдено {len(services)} услуг")
        return services
    except Exception as e:
        log.error(f"❌ Ошибка получения услуг: {e}")
        return []

def get_services_with_prices(master_name: str = None) -> List[Dict]:
    """Получить услуги с ценами (аналог старой функции)"""
    return get_services(master_name)

def get_services_for_master(master_name: str) -> List[Dict]:
    """Получить услуги для конкретного мастера"""
    return get_services(master_name)

def get_masters() -> List[Dict]:
    """Get available masters"""
    log.info("👥 Получение списка мастеров...")
    try:
        masters = get_masters_from_sheets()
        log.info(f"✅ Найдено {len(masters)} мастеров")
        return masters
    except Exception as e:
        log.error(f"❌ Ошибка получения мастеров: {e}")
        return []

def get_api_data_for_ai():
    """Получить форматированные данные для AI (услуги и мастера)"""
    try:
        services = get_services()
        masters = get_masters()
        
        data_text = "Доступные услуги (ИСПОЛЬЗУЙ ТОЛЬКО ЭТИ ЦЕНЫ, НЕ ВЫДУМЫВАЙ!):\n"
        for service in services:
            name = service.get("title", "Без названия")
            price = service.get("price", 0)
            price_str = service.get("price_str", "")
            duration = service.get("duration", 0)
            master = service.get("master", "")
            master1 = service.get("master1", "")
            master2 = service.get("master2", "")
            
            data_text += f"- {name}"
            
            # Отображаем цену (приоритет строковому формату с диапазоном) - ЯВНО и ЧЕТКО
            if price_str and ("–" in price_str or "-" in price_str):
                data_text += f" → ЦЕНА: {price_str} ₽"
            elif price > 0:
                data_text += f" → ЦЕНА: {price} ₽"
            else:
                data_text += f" → ЦЕНА: уточнить"
                
            if duration > 0:
                data_text += f" ({duration} мин)"
            
            # Отображаем мастеров
            master_display = master1
            if master2:
                master_display += f" или {master2}"
            if master_display:
                data_text += f" - мастер: {master_display}"
            
            data_text += "\n"
        
        data_text += "\nДоступные мастера:\n"
        for master in masters:
            name = master.get("name", "Без имени")
            specialization = master.get("specialization", "")
            
            data_text += f"- {name}"
            if specialization:
                data_text += f" ({specialization})"
            
            # Добавляем услуги мастера
            master_services = get_services_for_master(name)
            if master_services:
                data_text += " - услуги: "
                service_names = []
                for service in master_services:
                    service_name = service.get("title", "")
                    price_str = service.get("price_str", "")
                    price = service.get("price", 0)
                    if service_name:
                        if price_str and ("–" in price_str or "-" in price_str):
                            service_names.append(f"{service_name} ({price_str}₽)")
                        elif price > 0:
                            service_names.append(f"{service_name} ({price}₽)")
                        else:
                            service_names.append(service_name)
                data_text += ", ".join(service_names)
        
        data_text += "\n"
        
        return data_text
    except Exception as e:
        log.error(f"Ошибка получения данных: {e}")
        return "Данные временно недоступны"

def get_master_services_text(master_name: str) -> str:
    """Получить текст с услугами мастера (без AI)"""
    try:
        masters = get_masters()
        master = next((m for m in masters if m.get("name", "").lower() == master_name.lower()), None)
        
        if not master:
            return f"Мастер {master_name} не найден"
            
        master_services = get_services_for_master(master_name)
        if not master_services:
            return f"У мастера {master_name} нет доступных услуг"
            
        text = f"✨ Услуги мастера {master_name}:\n\n"
        
        for service in master_services:
            service_name = service.get("title", "")
            price = service.get("price", 0)
            duration = service.get("duration", 0)
            
            if service_name:
                text += f"• {service_name}"
                if price > 0:
                    text += f" — {price} ₽"
                if duration > 0:
                    text += f" ({duration} мин)"
                text += "\n"
        
        text += f"\n💡 Чтобы записаться к {master_name}, укажите желаемую дату и время."
        
        return text
    except Exception as e:
        log.error(f"Ошибка получения услуг мастера: {e}")
        return "Данные временно недоступны"

# ===================== NLP PARSING ==================
def init_fuzzy_matcher():
    """Инициализация нечеткого поиска"""
    try:
        from fuzzywuzzy import fuzz, process
        return True
    except ImportError:
        log.warning("fuzzywuzzy not available, using basic parsing")
        return False

# Глобальный флаг доступности fuzzywuzzy
fuzzy_available = init_fuzzy_matcher()

def find_best_match(word: str, choices: list, threshold: int = 80) -> str:
    """Находит лучшее совпадение с помощью нечеткого поиска"""
    if not fuzzy_available:
        return None
    
    try:
        from fuzzywuzzy import process, fuzz
        result = process.extractOne(word, choices, scorer=fuzz.ratio)
        if result and result[1] >= threshold:
            return result[0]
    except Exception as e:
        log.debug(f"Error in fuzzy matching '{word}': {e}")
    
    return None

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
        "маникюр": [
            r'\bманикюр\w*\b',
            r'\bманикюрн\w*\b',
            r'\bманик\w*\b',
        ],
        "педикюр": [
            r'\bпедикюр\w*\b',
            r'\bпедикюрн\w*\b',
            r'\bпедик\w*\b',
        ],
        "массаж": [
            r'\bмассаж\w*\b',
            r'\bмассажн\w*\b',
            r'\bмасаж\w*\b',
        ],
        "бритье": [
            r'\bбрить\w*\b',  # бритье, брить, бритья
            r'\bбрить[её]\s+голов\w*\b',  # бритье головы
        ],
        "стрижка": [
            r'\bстриж\w*\b',  # стрижка, стрижку, стрижки
            r'\bстриг\w*\b',  # стригу, стригут
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
    import re
    from datetime import datetime, timedelta
    
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
        master_names = ["Роман", "Анжела"]  # Fallback
    
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
        if "роман" in message_lower:
            result["master"] = "Роман"
        elif "анжела" in message_lower or "анжел" in message_lower:
            result["master"] = "Анжела"
    
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
        r'(\d{1,2})[./](\d{1,2})[./](\d{4})',  # 26.10.2025
    ]
    
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

def get_recent_history(user_id: int, limit: int = 50) -> str:
    """Получает последние N сообщений из истории"""
    if user_id not in UserMemory:
        return ""
    
    messages = UserMemory[user_id]
    recent_messages = messages[-limit:] if len(messages) > limit else messages
    
    history_text = ""
    for msg in recent_messages:
        # msg is a tuple (role, text)
        if isinstance(msg, tuple) and len(msg) == 2:
            role, content = msg
            history_text += f"{role}: {content}\n"
        else:
            # Fallback for dictionary format
            role = msg.get("role", "user") if isinstance(msg, dict) else "user"
            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            history_text += f"{role}: {content}\n"
    
    return history_text

def create_booking_from_parsed_data(user_id: int, parsed_data: Dict, client_name: str = "", client_phone: str = "") -> Dict:
    """Создает запись на основе распарсенных данных"""
    try:
        log.info(f"🔍 PARSED DATA: {parsed_data}")
        
        if not parsed_data["has_all_info"]:
            raise Exception("Недостаточно данных для создания записи")
        
        # Создаем реальную запись
        booking_record = create_real_booking(
            user_id,
            parsed_data["service"],
            parsed_data["master"],
            parsed_data["datetime"],
            client_name=client_name,
            client_phone=client_phone
        )
        
        return booking_record
        
    except Exception as e:
        log.error(f"Error creating booking from parsed data: {e}")
        raise e

# ===================== USER RECORDS ==================
def format_user_record(record: Dict) -> str:
    """Форматирует запись пользователя для отображения"""
    try:
        services = record.get("services", [])
        staff = record.get("staff", {})
        company = record.get("company", {})
        
        text = f"📅 *{record.get('date', 'Неизвестно')}*\n"
        text += f"⏰ {record.get('datetime', 'Неизвестно')}\n"
        text += f"👤 Мастер: *{staff.get('name', 'Неизвестно')}*\n"
        text += f"🏢 {company.get('title', 'Салон')}\n"
        
        if services:
            text += "🛍 *Услуги:*\n"
            for service in services:
                name = service.get("title", "Услуга")
                cost = service.get("cost", 0)
                if cost > 0:
                    text += f"  • {name} - {cost} ₽\n"
                else:
                    text += f"  • {name}\n"
        
        if record.get("comment"):
            text += f"💬 Комментарий: {record.get('comment')}\n"
        
        status_map = {
            2: "✅ Подтверждена",
            1: "✅ Выполнена", 
            0: "⏳ Ожидание",
            -1: "❌ Не пришел"
        }
        status = record.get("visit_attendance", 0)
        text += f"📊 Статус: {status_map.get(status, 'Неизвестно')}\n"
        
        return text
    except Exception as e:
        log.error(f"Error formatting record: {e}")
        return "❌ Ошибка отображения записи"

def get_user_records(user_id: int) -> List[Dict]:
    """Получить записи пользователя"""
    return UserRecords.get(user_id, [])

def add_user_record(user_id: int, record: Dict):
    """Добавить запись пользователя"""
    UserRecords[user_id].append(record)

def remove_user_record(user_id: int, record_id: int):
    """Удалить запись пользователя"""
    UserRecords[user_id] = [r for r in UserRecords[user_id] if r.get("id") != record_id]

def create_real_booking(user_id: int, service_name: str, master_name: str, date_time: str, client_name: str = "", client_phone: str = "") -> Dict:
    """Создать запись через Google Sheets"""
    log.info(f"🚀 СОЗДАНИЕ ЗАПИСИ: user_id={user_id}, услуга='{service_name}', мастер='{master_name}', время='{date_time}'")
    
    try:
        # Находим услугу
        log.info("🔍 Поиск услуги...")
        services = get_services()
        service = None
        for s in services:
            if service_name.lower() in s.get("title", "").lower():
                service = s
                break
        
        if not service:
            log.error(f"❌ Услуга '{service_name}' не найдена")
            raise Exception(f"Услуга '{service_name}' не найдена")
        log.info(f"✅ Найдена услуга: {service.get('title')}")
        
        # Находим мастера
        log.info("👥 Поиск мастера...")
        masters = get_masters()
        master = None
        for m in masters:
            if master_name.lower() in m.get("name", "").lower():
                master = m
                break
        
        if not master:
            log.error(f"❌ Мастер '{master_name}' не найден")
            raise Exception(f"Мастер '{master_name}' не найден")
        log.info(f"✅ Найден мастер: {master.get('name')}")
        
        # Проверяем доступность времени
        date_part = date_time.split()[0] if " " in date_time else date_time
        time_part = date_time.split()[1] if " " in date_time else ""
        
        if not check_slot_available(master_name, date_part, time_part):
            raise Exception(f"Время {date_time} недоступно, выберите другое время")
        
        # Создаем запись в Google Sheets
        booking_data = {
            "user_id": user_id,
            "service": service_name,
            "service_id": service.get("id"),
            "master": master_name,
            "master_id": master.get("id"),
            "date": date_part,
            "time": time_part,
            "datetime": date_time,
            "client_name": client_name,
            "client_phone": client_phone,
            "price": service.get("price", 0),
            "duration": service.get("duration", 60),
            "status": "confirmed"
        }
        
        log.info("📝 Создание записи в Google Sheets...")
        booking_record = create_booking_in_sheets(booking_data)
        
        # Формируем запись для локального хранилища
        formatted_record = {
            "id": booking_record.get("id"),
            "date": date_part,
            "datetime": date_time,
            "services": [{
                "id": service.get("id"),
                "title": service.get("title"),
                "cost": service.get("price", 0)
            }],
            "staff": {
                "id": master.get("id"),
                "name": master.get("name"),
                "specialization": master.get("specialization", "")
            },
            "company": {
                "title": "Салон красоты"
            },
            "comment": "Запись через Telegram бот",
            "visit_attendance": 0,
            "length": service.get("duration", 60),
            "online": True
        }
        
        add_user_record(user_id, formatted_record)
        log.info(f"🎉 ЗАПИСЬ СОЗДАНА! ID: {formatted_record['id']}")
        return formatted_record
        
    except Exception as e:
        log.error(f"❌ ОШИБКА при создании записи: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        raise e

# ===================== MENU HANDLERS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Записаться", callback_data="book_appointment")],
        [InlineKeyboardButton("📋 Услуги", callback_data="services")],
        [InlineKeyboardButton("👥 Мастера", callback_data="masters")],
        [InlineKeyboardButton("📅 Мои записи", callback_data="my_records")],
        [InlineKeyboardButton("💬 Чат с AI", callback_data="chat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "✨ *Добро пожаловать в салон красоты!* ✨\n\n"
        "🎯 *Что я умею:*\n"
        "• 📝 Записать вас к мастеру\n"
        "• 📋 Показать доступные услуги\n"
        "• 👥 Познакомить с мастерами\n"
        "• 📅 Управлять вашими записями\n"
        "• 💬 Ответить на вопросы\n\n"
        "Выберите действие:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Записаться", callback_data="book_appointment")],
        [InlineKeyboardButton("📋 Услуги", callback_data="services")],
        [InlineKeyboardButton("👥 Мастера", callback_data="masters")],
        [InlineKeyboardButton("📅 Мои записи", callback_data="my_records")],
        [InlineKeyboardButton("💬 Чат с AI", callback_data="chat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🏠 *Главное меню*\n\n"
        "📝 *Записаться* - создать новую запись\n"
        "📋 *Услуги* - посмотреть доступные услуги\n"
        "👥 *Мастера* - посмотреть мастеров и их расписание\n"
        "📅 *Мои записи* - просмотр и управление записями\n"
        "💬 *Чат с AI* - общение с AI помощником",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "services":
        await show_services(query)
    elif query.data == "masters":
        await show_masters(query)
    elif query.data == "my_records":
        await show_user_records(query)
    elif query.data == "book_appointment":
        await start_booking_process(query)
    elif query.data == "chat":
        await query.edit_message_text("Теперь вы можете писать сообщения для общения с AI помощником 💬")
    elif query.data == "back_to_menu":
        await show_main_menu(query)
    elif query.data.startswith("delete_record_"):
        record_id = int(query.data.replace("delete_record_", ""))
        await delete_user_record(query, record_id)
    elif query.data.startswith("services_page_"):
        await show_services_page(query)

async def show_services_page(query: CallbackQuery):
    """Показать конкретную страницу услуг"""
    try:
        page_offset = int(query.data.replace("services_page_", ""))
        # Получаем услуги с реальными ценами
        services = get_services_with_prices()
        if not services:
            await query.edit_message_text("❌ Не удалось загрузить услуги. Попробуйте позже.")
            return
        
        # Разделяем услуги на части по 6 услуг на сообщение
        services_per_message = 6
        total_services = len(services)
        
        page_services = services[page_offset:page_offset + services_per_message]
        page_number = page_offset // services_per_message + 1
        
        text = f"✨ *Услуги (часть {page_number})* ✨\n\n"
        
        for i, service in enumerate(page_services, 1):
            name = service.get("title", "Без названия")
            price = service.get("price", 0)
            price_str = service.get("price_str", "")
            duration = service.get("duration", 0)
            
            # Красивое форматирование с эмодзи
            if "маникюр" in name.lower():
                emoji = "💅"
            elif "педикюр" in name.lower():
                emoji = "🦶"
            elif "массаж" in name.lower():
                emoji = "💆"
            elif "стрижка" in name.lower():
                emoji = "✂️"
            elif "окрашивание" in name.lower() or "тонирование" in name.lower():
                emoji = "🎨"
            elif "бритье" in name.lower():
                emoji = "🪒"
            else:
                emoji = "✨"
                
            text += f"{emoji} *{name}*\n"
            
            # Показываем цены (приоритет строковому формату с диапазоном)
            if price_str and ("–" in price_str or "-" in price_str):
                text += f"   💰 {price_str} ₽\n"
            elif price > 0:
                text += f"   💰 {price} ₽\n"
                
            if duration > 0:
                text += f"   ⏱ {duration} мин\n"
            text += "\n"
        
        # Добавляем информацию о количестве услуг
        text += f"📊 *Всего услуг: {total_services}*\n"
        text += f"📄 *Показано: {page_offset + 1}-{min(page_offset + services_per_message, total_services)} из {total_services}*\n"
        
        keyboard = []
        
        # Добавляем кнопки навигации
        nav_buttons = []
        if page_offset > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"services_page_{page_offset - services_per_message}"))
        if page_offset + services_per_message < total_services:
            nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"services_page_{page_offset + services_per_message}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.extend([
            [InlineKeyboardButton("📝 Записаться", callback_data="book_appointment")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        log.error(f"Error showing services page: {e}")
        await query.edit_message_text("❌ Ошибка при загрузке услуг.")

async def show_services(query: CallbackQuery):
    # Получаем услуги с реальными ценами
    services = get_services_with_prices()
    if not services:
        await query.edit_message_text("❌ Не удалось загрузить услуги. Попробуйте позже.")
        return
    
    # Разделяем услуги на части по 6 услуг на сообщение (чтобы поместилось)
    services_per_message = 6
    total_services = len(services)
    
    for page in range(0, total_services, services_per_message):
        page_services = services[page:page + services_per_message]
        
        if page == 0:
            text = "✨ *Наши услуги с ценами* ✨\n\n"
        else:
            text = f"✨ *Услуги (часть {page // services_per_message + 1})* ✨\n\n"
        
        for i, service in enumerate(page_services, 1):
            name = service.get("title", "Без названия")
            price = service.get("price", 0)
            price_str = service.get("price_str", "")
            duration = service.get("duration", 0)
            
            # Красивое форматирование с эмодзи
            if "маникюр" in name.lower():
                emoji = "💅"
            elif "педикюр" in name.lower():
                emoji = "🦶"
            elif "массаж" in name.lower():
                emoji = "💆"
            elif "стрижка" in name.lower():
                emoji = "✂️"
            elif "окрашивание" in name.lower() or "тонирование" in name.lower():
                emoji = "🎨"
            elif "бритье" in name.lower():
                emoji = "🪒"
            else:
                emoji = "✨"
                
            text += f"{emoji} *{name}*\n"
            
            # Показываем цены (приоритет строковому формату с диапазоном)
            if price_str and ("–" in price_str or "-" in price_str):
                text += f"   💰 {price_str} ₽\n"
            elif price > 0:
                text += f"   💰 {price} ₽\n"
                
            if duration > 0:
                text += f"   ⏱ {duration} мин\n"
            text += "\n"
        
        # Добавляем информацию о количестве услуг
        if total_services > services_per_message:
            text += f"📊 *Всего услуг: {total_services}*\n"
            if page + services_per_message < total_services:
                text += f"📄 *Показано: {page + 1}-{min(page + services_per_message, total_services)} из {total_services}*\n"
        
        keyboard = []
        
        # Добавляем кнопки навигации если есть несколько страниц
        if total_services > services_per_message:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"services_page_{page - services_per_message}"))
            if page + services_per_message < total_services:
                nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"services_page_{page + services_per_message}"))
            if nav_buttons:
                keyboard.append(nav_buttons)
        
        keyboard.extend([
            [InlineKeyboardButton("📝 Записаться", callback_data="book_appointment")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if page == 0:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await query.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)

async def show_masters(query: CallbackQuery):
    masters = get_masters()
    if not masters:
        await query.edit_message_text("❌ Не удалось загрузить мастеров. Попробуйте позже.")
        return
    
    text = "👥 *Наши мастера и их услуги* 👥\n\n"
    for master in masters:
        name = master.get("name", "Без имени")
        specialization = master.get("specialization", "")
        staff_id = master.get("id")
        
        # Красивое форматирование с эмодзи
        if "массаж" in specialization.lower():
            emoji = "💆‍♀️"
        elif "мастер" in specialization.lower():
            emoji = "💅"
        else:
            emoji = "✨"
            
        text += f"{emoji} *{name}*\n"
        if specialization:
            text += f"   🎯 {specialization}\n"
        
        # Получаем услуги для этого мастера
        if staff_id:
            master_services = get_services_for_master(master.get("name", ""))
            if master_services:
                text += f"   💰 *Услуги:*\n"
                for service in master_services:  # Показываем ВСЕ услуги мастера
                    service_name = service.get("title", "")
                    price = service.get("price", 0)
                    price_str = service.get("price_str", "")
                    
                    if service_name:
                        text += f"      • {service_name}"
                        
                        # Показываем цены (приоритет строковому формату с диапазоном)
                        if price_str and ("–" in price_str or "-" in price_str):
                            text += f": {price_str} ₽"
                        elif price > 0:
                            text += f": {price} ₽"
                        
                        text += "\n"
        
        text += "\n"
    
    keyboard = [
        [InlineKeyboardButton("📝 Записаться", callback_data="book_appointment")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)

async def show_user_records(query: CallbackQuery):
    """Показать записи пользователя"""
    user_id = query.from_user.id
    records = get_user_records(user_id)
    
    if not records:
        keyboard = [
            [InlineKeyboardButton("📝 Записаться", callback_data="book_appointment")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📅 *Мои записи*\n\n"
            "У вас пока нет записей.\n\n"
            "💡 *Создайте первую запись:*\n"
            "• Используйте кнопку \"📝 Записаться\"\n"
            "• Или напишите в чат \"хочу записаться\"",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    text = "📅 *Мои записи* 📅\n\n"
    keyboard = []
    
    for i, record in enumerate(records[:5]):  # Показываем первые 5 записей
        record_text = format_user_record(record)
        text += f"📋 *Запись {i+1}:*\n{record_text}\n"
        
        # Добавляем кнопку удаления для каждой записи
        keyboard.append([
            InlineKeyboardButton(
                f"🗑 Удалить запись {i+1}", 
                callback_data=f"delete_record_{record.get('id', i)}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text, 
        parse_mode='Markdown', 
        reply_markup=reply_markup
    )

async def delete_user_record(query: CallbackQuery, record_id: int):
    """Удалить запись пользователя"""
    user_id = query.from_user.id
    
    try:
        # Удаляем из локального хранилища
        remove_user_record(user_id, record_id)
        
        # TODO: Здесь можно добавить вызов API для удаления записи
        # yclients.delete_user_record(record_id, record_hash)
        
        await query.edit_message_text(
            f"✅ Запись #{record_id} успешно удалена!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К записям", callback_data="my_records")
            ]])
        )
    except Exception as e:
        log.error(f"Error deleting record: {e}")
        await query.edit_message_text(
            "❌ Ошибка при удалении записи. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К записям", callback_data="my_records")
            ]])
        )

async def start_booking_process(query: CallbackQuery):
    """Начать процесс записи"""
    user_id = query.from_user.id
    
    # Проверяем, есть ли номер телефона
    if user_id not in UserPhone:
        await query.edit_message_text(
            "📱 *Для записи нужен ваш номер телефона*\n\n"
            "Пожалуйста, отправьте номер в формате:\n"
            "`+7XXXXXXXXXX`\n\n"
            "Например: `+79991234567`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")
            ]])
        )
        return
    
    # Показываем доступные услуги и мастеров
    services = get_services()
    masters = get_masters()
    
    text = "📝 *Создание записи* 📝\n\n"
    text += "✨ *Доступные услуги:*\n"
    for service in services[:5]:
        name = service.get('title', 'Услуга')
        price = service.get('price', 0)
        price_str = service.get('price_str', '')
        if price_str and ("–" in price_str or "-" in price_str):
            text += f"• {name} ({price_str} ₽)\n"
        elif price > 0:
            text += f"• {name} ({price} ₽)\n"
        else:
            text += f"• {name}\n"
    
    text += "\n👥 *Доступные мастера:*\n"
    for master in masters[:5]:
        name = master.get('name', 'Мастер')
        spec = master.get('specialization', '')
        if spec:
            text += f"• {name} ({spec})\n"
        else:
            text += f"• {name}\n"
    
    text += "\n💬 *Напишите сообщение с вашими пожеланиями:*\n"
    text += "Например: `Хочу записаться на маникюр к Арине на завтра в 14:00`"
    
    await query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")
        ]])
    )

async def show_main_menu(query: CallbackQuery):
    keyboard = [
        [InlineKeyboardButton("📝 Записаться", callback_data="book_appointment")],
        [InlineKeyboardButton("📋 Услуги", callback_data="services")],
        [InlineKeyboardButton("👥 Мастера", callback_data="masters")],
        [InlineKeyboardButton("📅 Мои записи", callback_data="my_records")],
        [InlineKeyboardButton("💬 Чат с AI", callback_data="chat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🏠 *Главное меню*\n\n"
        "📝 *Записаться* - создать новую запись\n"
        "📋 *Услуги* - посмотреть доступные услуги\n"
        "👥 *Мастера* - посмотреть мастеров и их расписание\n"
        "📅 *Мои записи* - просмотр и управление записями\n"
        "💬 *Чат с AI* - общение с AI помощником",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

def create_test_record(user_id: int):
    """Создать тестовую запись для демонстрации"""
    test_record = {
        "id": user_id + 1000,  # Простой ID для теста
        "date": "2024-01-15",
        "datetime": "2024-01-15 14:30",
        "services": [
            {
                "id": 1,
                "title": "Стрижка",
                "cost": 1500,
                "price_min": 1200,
                "price_max": 2000
            }
        ],
        "staff": {
            "id": 1,
            "name": "Анна Иванова",
            "specialization": "Парикмахер"
        },
        "company": {
            "id": 1,
            "title": "Салон красоты 'Элегант'",
            "address": "ул. Примерная, 123"
        },
        "comment": "Тестовая запись",
        "visit_attendance": 0,  # Ожидание
        "length": 60,
        "online": True
    }
    add_user_record(user_id, test_record)
    return test_record

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    add_memory(user_id, "user", text)
    
    # Флаг для отслеживания отправки ответа
    response_sent = False

    # Проверяем специальные команды
    if text.lower() in ["создать тестовую запись", "тест запись", "добавить запись"]:
        test_record = create_test_record(user_id)
        await update.message.reply_text(
            f"✅ *Создана тестовая запись!*\n\n"
            f"📅 *Дата:* {test_record['date']}\n"
            f"⏰ *Время:* {test_record['datetime']}\n"
            f"👤 *Мастер:* {test_record['staff']['name']}\n"
            f"🛍 *Услуга:* {test_record['services'][0]['title']}\n\n"
            f"Используйте меню *'Мои записи'* для просмотра!",
            parse_mode='Markdown'
        )
        response_sent = True
        return
    
    # Проверяем, является ли сообщение номером телефона
    if text.startswith("+") and len(text) >= 10:
        UserPhone[user_id] = text
        await update.message.reply_text(
            f"✅ *Номер телефона {text} сохранен!*\n\n"
            f"Теперь вы можете создавать записи.\n"
            f"Напишите `хочу записаться` для начала.",
            parse_mode='Markdown'
        )
        response_sent = True
        return

    if is_booking(text):
        log.info(f"🎯 BOOKING DETECTED: '{text}'")
        # Сначала пробуем парсить сообщение напрямую
        history = get_recent_history(user_id, 50)
        log.info(f"📚 HISTORY: {history[:200]}...")
        parsed_data = parse_booking_message(text, history)
        
        log.info(f"🔍 PARSED MESSAGE: {parsed_data}")
        
        # Если удалось распарсить все данные, создаем запись напрямую
        if parsed_data["has_all_info"]:
            try:
                user_phone = UserPhone.get(user_id)
                if not user_phone:
                    await update.message.reply_text(
                        "📱 *Для создания записи нужен ваш номер телефона*\n\n"
                        "Пожалуйста, отправьте номер в формате:\n"
                        "`+7XXXXXXXXXX`",
                        parse_mode='Markdown'
                    )
                    response_sent = True
                    return
                
                # Создаем запись напрямую
                booking_record = create_booking_from_parsed_data(
                    user_id,
                    parsed_data,
                    client_name=update.message.from_user.first_name or "Клиент",
                    client_phone=user_phone
                )
                
                answer = f"🎉 *Запись успешно создана в системе!* 🎉\n\n"
                answer += f"📅 *Услуга:* {parsed_data['service']}\n"
                answer += f"👤 *Мастер:* {parsed_data['master']}\n"
                answer += f"⏰ *Время:* {parsed_data['datetime']}\n\n"
                answer += "Спасибо за запись! Ждем вас в салоне! ✨"
                
            except Exception as e:
                log.error(f"Error creating booking from parsed data: {e}")
                
                # Sprawdzamy czy to konflikt czasowy
                if "недоступно" in str(e) or "conflict" in str(e).lower():
                    answer = f"❌ *Время {parsed_data['datetime']} недоступно*\n\n"
                    answer += f"💡 *Предлагаем альтернативные варианты:*\n"
                    answer += f"• {parsed_data['service']} у {parsed_data['master']}\n"
                    answer += f"• Завтра в 14:00\n"
                    answer += f"• Завтра в 15:00\n"
                    answer += f"• Завтра в 17:00\n\n"
                    answer += f"Напишите желаемое время, например: `завтра 14:00`"
                else:
                    answer = f"❌ *Ошибка при создании записи:* {str(e)}"
        else:
            # Проверяем, спрашивает ли пользователь об услугах конкретного мастера
            masters = get_masters()
            master_names = [m.get("name", "").lower() for m in masters]
            
            # Ищем упоминание имени мастера в сообщении
            mentioned_master = None
            for master_name in master_names:
                if master_name in text.lower():
                    mentioned_master = master_name
                    break
            
            # Если упоминается мастер, показываем его услуги детерминистически
            if mentioned_master:
                master_display_name = next((m.get("name") for m in masters if m.get("name", "").lower() == mentioned_master), mentioned_master)
                answer = get_master_services_text(master_display_name)
                log.info(f"🎯 DETERMINISTIC RESPONSE for {master_display_name}: {answer}")
            else:
                # Если не удалось распарсить, используем AI
                api_data = get_api_data_for_ai()
                log.info(f"📊 API DATA FOR AI: {api_data[:500]}...")  # Логируем больше для проверки
                
                # ВЕКТОРНЫЙ ПОИСК: Используем Qdrant для точного поиска услуги
                found_service_info = ""
                try:
                    # Сначала пробуем векторный поиск в Qdrant
                    if QDRANT_AVAILABLE:
                        vector_results = search_service(text, limit=1)
                        if vector_results and len(vector_results) > 0:
                            service = vector_results[0]
                            score = service.get("score", 0)
                            
                            # Используем результат только если score достаточно высокий (>= 0.5)
                            if score >= 0.5:
                                price_str = service.get("price_str", "")
                                price = service.get("price", 0)
                                duration = service.get("duration", 0)
                                master = service.get("master", "")
                                
                                # Формируем точную информацию об услуге
                                if price_str and ("–" in price_str or "-" in price_str):
                                    price_info = f"{price_str} ₽"
                                elif price > 0:
                                    price_info = f"{price} ₽"
                                else:
                                    price_info = "уточнить цену"
                                
                                found_service_info = f"\n\n⚠️⚠️⚠️ КРИТИЧЕСКИ ВАЖНО - ВЕКТОРНЫЙ ПОИСК ⚠️⚠️⚠️\n"
                                found_service_info += f"🔍 НАЙДЕНА УСЛУГА: {service.get('title')}\n"
                                found_service_info += f"💰 ЦЕНА: {price_info} ← ИСПОЛЬЗУЙ ЭТУ ТОЧНУЮ ЦЕНУ ИЗ GOOGLE SHEETS!\n"
                                found_service_info += f"⏱ ДЛИТЕЛЬНОСТЬ: {duration} минут\n"
                                found_service_info += f"👤 МАСТЕР: {master}\n"
                                found_service_info += f"📊 СХОЖЕСТЬ: {score:.2%}\n"
                                found_service_info += f"\n❌ ЗАПРЕЩЕНО выдумывать цены! Используй ТОЛЬКО эту информацию из Google Sheets!\n"
                                
                                log.info(f"✅ Найдена услуга через Qdrant: {service.get('title')} - {price_info} (score: {score:.3f})")
                    
                    # Fallback: обычный поиск если Qdrant не нашел
                    if not found_service_info:
                        all_services = get_services()
                        text_lower = text.lower()
                        
                        # Ищем точное или частичное совпадение
                        for service in all_services:
                            service_title = service.get("title", "").lower()
                            service_words = set(service_title.split())
                            text_words = set(text_lower.split())
                            
                            # Проверяем разные варианты совпадения
                            if (service_title in text_lower or 
                                text_lower in service_title or
                                any(word in service_title for word in text_lower.split() if len(word) > 3) or
                                len(service_words & text_words) >= 2):  # Если совпало 2+ слова
                                
                                price_str = service.get("price_str", "")
                                price = service.get("price", 0)
                                duration = service.get("duration", 0)
                                master = service.get("master", "")
                                
                                # Формируем точную информацию об услуге
                                if price_str and ("–" in price_str or "-" in price_str):
                                    price_info = f"{price_str} ₽"
                                elif price > 0:
                                    price_info = f"{price} ₽"
                                else:
                                    price_info = "уточнить цену"
                                
                                found_service_info = f"\n\n⚠️⚠️⚠️ КРИТИЧЕСКИ ВАЖНО ⚠️⚠️⚠️\n"
                                found_service_info += f"🔍 НАЙДЕНА УСЛУГА: {service.get('title')}\n"
                                found_service_info += f"💰 ЦЕНА: {price_info} ← ИСПОЛЬЗУЙ ЭТУ ТОЧНУЮ ЦЕНУ ИЗ GOOGLE SHEETS!\n"
                                found_service_info += f"⏱ ДЛИТЕЛЬНОСТЬ: {duration} минут\n"
                                found_service_info += f"👤 МАСТЕР: {master}\n"
                                found_service_info += f"\n❌ ЗАПРЕЩЕНО выдумывать цены! Используй ТОЛЬКО эту информацию!\n"
                                
                                log.info(f"✅ Найдена услуга детерминистически: {service.get('title')} - {price_info}")
                                break
                except Exception as e:
                    log.error(f"❌ Ошибка поиска услуги: {e}")
                    import traceback
                    log.error(f"❌ Traceback: {traceback.format_exc()}")
                
                # Формируем промпт правильно
                msg = BOOKING_PROMPT.replace("{{api_data}}", api_data).replace("{{message}}", text).replace("{{history}}", history).replace("{{service_info}}", found_service_info)
                log.info(f"🤖 AI PROMPT длина: {len(msg)} символов")
                if found_service_info:
                    log.info(f"✅ Service info добавлена в промпт: {found_service_info[:100]}...")
                
                answer = openrouter_chat([{"role": "user", "content": msg}])
                log.info(f"🤖 AI RESPONSE: {answer[:200]}...")  # Логируем только начало
            
            # Проверяем, содержит ли ответ команду для создания записи
            if "ЗАПИСЬ:" in answer:
                try:
                    # Парсим данные из ответа AI
                    booking_line = [line for line in answer.split('\n') if 'ЗАПИСЬ:' in line][0]
                    parts = booking_line.split('|')
                    if len(parts) >= 3:
                        service_name = parts[0].replace('ЗАПИСЬ:', '').strip()
                        master_name = parts[1].strip()
                        date_time = parts[2].strip()
                        
                        # Проверяем, есть ли номер телефона
                        user_phone = UserPhone.get(user_id)
                        if not user_phone:
                            await update.message.reply_text(
                                "📱 *Для создания записи нужен ваш номер телефона*\n\n"
                                "Пожалуйста, отправьте номер в формате:\n"
                                "`+7XXXXXXXXXX`",
                                parse_mode='Markdown'
                            )
                            response_sent = True
                            return
                        
                        # ВАЛИДАЦИЯ: Проверяем, существует ли услуга в API
                        all_services = get_services_with_prices()
                        service_exists = any(service_name.lower() in service.get("title", "").lower() 
                                            for service in all_services)
                        
                        if not service_exists:
                            log.warning(f"❌ SERVICE NOT FOUND IN API: {service_name}")
                            await update.message.reply_text(
                                f"❌ *Услуга не найдена*\n\n"
                                f"Услуга '{service_name}' не существует в нашем каталоге.\n"
                                f"Пожалуйста, выберите услугу из списка доступных.",
                                parse_mode='Markdown'
                            )
                            response_sent = True
                            return
                        
                        # Создаем реальную запись
                        booking_record = create_real_booking(
                            user_id, 
                            service_name, 
                            master_name, 
                            date_time,
                            client_name=update.message.from_user.first_name or "Клиент",
                            client_phone=user_phone
                        )
                        
                        # Обновляем ответ
                        answer = f"🎉 *Запись успешно создана в системе!* 🎉\n\n" + answer.replace("ЗАПИСЬ:", "📅 *Создана запись:*")
                        
                except Exception as e:
                    log.error(f"Error creating booking: {e}")
                    
                    # Sprawdzamy czy to konflikt czasowy
                    if "недоступно" in str(e) or "conflict" in str(e).lower():
                        answer += f"\n\n❌ *Время {date_time} недоступно*\n\n"
                        answer += f"💡 *Предлагаем альтернативные варианты:*\n"
                        answer += f"• {service_name} у {master_name}\n"
                        answer += f"• Завтра в 14:00\n"
                        answer += f"• Завтра в 15:00\n"
                        answer += f"• Завтра в 17:00\n\n"
                        answer += f"Напишите желаемое время, например: `завтра 14:00`"
                    else:
                        answer += f"\n\n❌ *Ошибка при создании записи:* {str(e)}"
    else:
        msg = CHAT_PROMPT.replace("{{history}}", get_history(user_id)).replace("{{message}}", text)
        answer = openrouter_chat([{"role": "user", "content": msg}])

    add_memory(user_id, "assistant", answer)
    
    # Отправляем ответ только если он не был отправлен ранее
    if answer and not response_sent:  # Проверяем что есть ответ для отправки
        await update.message.reply_text(answer)

# ===================== RUN BOT ========================
def main():
    # Проверяем доступность Qdrant библиотек еще раз при старте
    try:
        import qdrant_client
        import sentence_transformers
        log.info("✅ Qdrant библиотеки доступны: qdrant-client и sentence-transformers")
    except ImportError as e:
        log.warning(f"⚠️ Qdrant библиотеки не установлены: {e}")
        log.warning("⚠️ Для работы векторного поиска установите: pip install qdrant-client sentence-transformers")
    
    # Инициализация: индексируем услуги в Qdrant в фоновом режиме
    def index_services_background():
        """Индексировать услуги в Qdrant в фоновом потоке"""
        try:
            log.info("🔄 Фоновая индексация Qdrant: чтение услуг из Google Sheets...")
            services = get_services()
            if services:
                log.info(f"📋 Прочитано {len(services)} услуг из Google Sheets, начинаю индексацию в Qdrant...")
                if index_services(services):
                    log.info(f"✅ Успешно проиндексировано {len(services)} услуг в Qdrant")
                else:
                    log.warning("⚠️ Не удалось проиндексировать услуги в Qdrant")
            else:
                log.warning("⚠️ Нет услуг для индексации в Qdrant")
        except Exception as e:
            log.error(f"❌ Ошибка индексации Qdrant в фоне: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
    
    # Запускаем индексацию в фоновом потоке
    if QDRANT_AVAILABLE:
        import threading
        index_thread = threading.Thread(target=index_services_background, daemon=True)
        index_thread.start()
        log.info("🔄 Запущена фоновая индексация Qdrant (бот запускается, не ждет завершения)")
    
    # Start Telegram bot
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    
    # Callback query handler for inline buttons
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handler for AI chat
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    
    # Start bot
    log.info("🚀 Starting Telegram Bot...")
    app.run_polling()

if __name__ == "__main__":
    main()
