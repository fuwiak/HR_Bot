# bot.py
import os
import re
import time
import logging
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from typing import Dict, Deque, List, Tuple

import requests
import aiohttp
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
from telegram import Document as TelegramDocument

# ===================== LOAD .ENV ======================
load_dotenv()  # <-- loads variables from .env file

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# OpenRouter API URL - правильный формат
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")

# Webhook конфигурация для Railway (масштабируемость и concurrent updates)
PORT = int(os.getenv("PORT", 8080))  # Railway автоматически предоставляет PORT (по умолчанию 8080)
# Railway предоставляет публичный домен через RAILWAY_PUBLIC_DOMAIN или можно указать вручную через WEBHOOK_URL
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
# Очищаем домен от протокола и слэшей (поддерживаем оба формата: с https:// и без)
if RAILWAY_PUBLIC_DOMAIN:
    RAILWAY_PUBLIC_DOMAIN = RAILWAY_PUBLIC_DOMAIN.replace("https://", "").replace("http://", "").rstrip("/")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
if not WEBHOOK_URL and RAILWAY_PUBLIC_DOMAIN:
    # Формируем WEBHOOK_URL из домена (всегда используем HTTPS)
    WEBHOOK_URL = f"https://{RAILWAY_PUBLIC_DOMAIN}"
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "true").lower() == "true"  # По умолчанию используем webhook

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

# Устаревший подход - оставлен для обратной совместимости, но не используется
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

🚨🚨🚨 КРИТИЧЕСКИ ВАЖНО - ОБЯЗАТЕЛЬНО СЛЕДУЙ 🚨🚨🚨

ПРАВИЛО №1: ВСЕ ЦЕНЫ И ДАННЫЕ ТОЛЬКО ИЗ СПИСКА НИЖЕ!
- НИКОГДА не выдумывай цены
- НИКОГДА не угадывай цены
- Если услуга есть в списке - используй ТОЧНУЮ цену из списка
- Если услуги нет в списке - скажи что услуга недоступна
- Если видишь блок "НАЙДЕНА УСЛУГА" - используй ТОЧНО эти данные, ничего не меняй!

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 СПИСОК ВСЕХ УСЛУГ ИЗ GOOGLE SHEETS (ЛИСТ "ЦЕННИК"):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{api_data}}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{service_info}}

Сообщение пользователя: {{message}}

ПОВТОРЯЮ: Используй ТОЛЬКО данные из списка выше! Не выдумывай!

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

# ===================== NEW PROMPTS FOR CONSULTING =====================

CONSULTING_PROMPT = """
Ты AI-ассистент консультанта Анастасии Новосёловой. Твоя задача - помогать в консалтинговой практике.

СТИЛЬ ОБЩЕНИЯ:
- Деловой, но дружелюбный
- Используй "вы" при обращении
- Структурируй ответы (списки, пункты)
- Используй эмодзи умеренно для дружелюбия

ОСНОВНЫЕ НАПРАВЛЕНИЯ:
- Подбор персонала (рекрутинг)
- Автоматизация HR-процессов
- Бизнес-анализ и консалтинг

ВАЖНО:
- Всегда используй информацию из базы знаний (RAG) если она предоставлена
- Не выдумывай кейсы или методики
- Если информации нет - честно скажи об этом
- Предлагай уточняющие вопросы для лучшего понимания задачи

Релевантная информация из базы знаний:
{{rag_context}}

История разговора:
{{history}}

Сообщение пользователя: {{message}}

Ответь по делу, используя информацию из базы знаний.
"""

# ===================== LOGGING ========================
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger()

# ===================== MEMORY =========================
UserMemory: Dict[int, Deque] = defaultdict(lambda: deque(maxlen=MEMORY_TURNS * 2))
UserRecords: Dict[int, List[Dict]] = defaultdict(list)  # Хранилище записей пользователей
UserAuth: Dict[int, Dict] = defaultdict(dict)  # Данные авторизации пользователей
UserPhone: Dict[int, str] = {}  # Номера телефонов пользователей
UserBookingData: Dict[int, Dict] = {}  # Частично собранные данные для записи (service, master, datetime)

def add_memory(user_id, role, text):
    UserMemory[user_id].append((role, text))

def get_history(user_id):
    return "\n".join([f"{r}: {t}" for r, t in UserMemory[user_id]])

# ===================== NLP ============================
def is_booking(text):
    """
    Улучшенная функция определения запроса на запись.
    Использует многоуровневый подход:
    1. Проверка наличия услуг из Google Sheets
    2. Проверка упоминания мастеров
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
    
    # 2. ПРОВЕРКА: Упоминание мастеров
    try:
        all_masters = get_masters()
        for master in all_masters:
            master_name = master.get("name", "").lower()
            if master_name in text_lower:
                score += 15
                reasons.append(f"упоминание мастера '{master.get('name')}'")
                break
    except Exception as e:
        log.debug(f"Ошибка при проверке мастеров для is_booking: {e}")
    
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
    import re
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

async def openrouter_chat(messages, use_system_message=False, system_content=""):
    """
    Асинхронная отправка запроса в LLM через новый модуль llm_helper
    Использует DeepSeek (primary) с fallback на GigaChat
    """
    try:
        from llm_helper import generate_with_fallback
        return await generate_with_fallback(
            messages=messages,
            use_system_message=use_system_message,
            system_content=system_content,
            max_tokens=2000,
            temperature=0.7
        )
    except ImportError:
        log.warning("⚠️ llm_helper недоступен, используем старый метод")
        # Fallback на старый метод если новый модуль недоступен
        # (оставляем старый код как fallback, но обычно используем новый модуль)
        return "Извините, сервис временно недоступен."

# ===================== GOOGLE SHEETS INTEGRATION ===========
from google_sheets_helper import (
    get_masters as get_masters_from_sheets,
    get_services as get_services_from_sheets,
    create_booking as create_booking_in_sheets,
    check_slot_available,
    get_available_slots,
    get_user_bookings,
    delete_user_booking,
)

# ===================== QDRANT VECTOR DATABASE ===========
try:
    from qdrant_helper import search_service, index_services
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
    """Получить форматированные данные для AI (услуги и мастера) из Google Sheets листа 'Ценник'"""
    try:
        services = get_services()
        masters = get_masters()
        
        if not services:
            return "⚠️ Услуги временно недоступны. Данные загружаются..."
        
        data_text = "🚨 ВАЖНО: Это ТОЧНЫЕ данные из Google Sheets листа 'Ценник'. Используй ТОЛЬКО эти цены!\n\n"
        data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        data_text += "📋 ВСЕ УСЛУГИ САЛОНА (МУЖСКОЙ И ЖЕНСКИЙ ЗАЛ):\n"
        data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Разделяем по типам
        men_services = [s for s in services if s.get('type') == 'men']
        women_services = [s for s in services if s.get('type') == 'women']
        
        if men_services:
            data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            data_text += "👨 МУЖСКОЙ ЗАЛ (Мастер: Роман):\n"
            data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for service in men_services:
                name = service.get("title", "Без названия")
                price = service.get("price", 0)
                price_str = service.get("price_str", "")
                duration = service.get("duration", 0)
                
                data_text += f"• {name}"
                
                # Отображаем цену (приоритет строковому формату с диапазоном) - ЯВНО и ЧЕТКО
                if price_str and ("–" in price_str or "-" in price_str):
                    data_text += f" → ЦЕНА: {price_str} ₽"
                elif price > 0:
                    data_text += f" → ЦЕНА: {price} ₽"
                else:
                    data_text += f" → ЦЕНА: уточнить"
                
            if duration > 0:
                data_text += f" ({duration} мин)"
                
            data_text += "\n"
        
        if women_services:
            data_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            data_text += "👩 ЖЕНСКИЙ ЗАЛ (Мастер: Анжела):\n"
            data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for service in women_services:
                name = service.get("title", "Без названия")
                price = service.get("price", 0)
                price_str = service.get("price_str", "")
                duration = service.get("duration", 0)
                
                data_text += f"• {name}"
                
                # Отображаем цену (приоритет строковому формату с диапазоном) - ЯВНО и ЧЕТКО
                if price_str and ("–" in price_str or "-" in price_str):
                    data_text += f" → ЦЕНА: {price_str} ₽"
                elif price > 0:
                    data_text += f" → ЦЕНА: {price} ₽"
                else:
                    data_text += f" → ЦЕНА: уточнить"
                    
                if duration > 0:
                    data_text += f" ({duration} мин)"
                
                data_text += "\n"
        
        data_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        data_text += "👥 МАСТЕРА:\n"
        data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for master in masters:
            name = master.get("name", "Без имени")
            specialization = master.get("specialization", "")
            
            data_text += f"• {name}"
            if specialization:
                data_text += f" ({specialization})"
            data_text += "\n"
        
        data_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        data_text += "🚨 ПОВТОРЯЮ: Используй ТОЛЬКО цены из списка выше!\n"
        data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
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
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "без username"
    first_name = update.message.from_user.first_name or "без имени"
    
    # Логируем команду /start
    log.info(f"🚀 КОМАНДА /start: user_id={user_id}, username=@{username}, name={first_name}")
    
    keyboard = [
        [InlineKeyboardButton("📚 База знаний", callback_data="menu_knowledge_base")],
        [InlineKeyboardButton("📋 Проекты", callback_data="menu_projects")],
        [InlineKeyboardButton("🛠 Инструменты", callback_data="menu_tools")],
        [InlineKeyboardButton("💬 Чат с AI", callback_data="chat")],
        [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "✨ *Добро пожаловать! Я AI-ассистент Анастасии Новосёловой* ✨\n\n"
        "🎯 *Что я умею:*\n"
        "• 🔍 Искать в базе знаний (методики, кейсы, шаблоны)\n"
        "• 📝 Генерировать коммерческие предложения\n"
        "• 📊 Показывать статистику базы знаний\n"
        "• 📚 Просматривать документы в базе\n"
        "• 💬 Отвечать на вопросы с использованием базы знаний\n"
        "• 📋 Управлять проектами и задачами\n\n"
        "Выберите раздел:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 База знаний", callback_data="menu_knowledge_base")],
        [InlineKeyboardButton("📋 Проекты", callback_data="menu_projects")],
        [InlineKeyboardButton("🛠 Инструменты", callback_data="menu_tools")],
        [InlineKeyboardButton("💬 Чат с AI", callback_data="chat")],
        [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🏠 *Главное меню*\n\n"
        "📚 *База знаний* - поиск, документы, статистика\n"
        "📋 *Проекты* - управление проектами и задачами\n"
        "🛠 *Инструменты* - генерация КП, суммаризация\n"
        "💬 *Чат с AI* - общение с AI-помощником\n"
        "❓ *Помощь* - справочная информация",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Главное меню и подменю
    if query.data == "back_to_menu" or query.data == "menu_main":
        await show_main_menu(query)
        return
    
    # Подменю "База знаний"
    elif query.data == "menu_knowledge_base":
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск в базе знаний", callback_data="rag_search_menu")],
            [InlineKeyboardButton("📚 Список документов", callback_data="rag_docs")],
            [InlineKeyboardButton("📊 Статистика RAG", callback_data="rag_stats")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "📚 *База знаний*\n\n"
            "🔍 *Поиск* - семантический поиск по методикам, кейсам, шаблонам\n"
            "📚 *Документы* - список всех документов в базе\n"
            "📊 *Статистика* - информация о базе знаний",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Подменю "Проекты"
    elif query.data == "menu_projects":
        keyboard = [
            [InlineKeyboardButton("📋 Статус проектов", callback_data="status")],
            [InlineKeyboardButton("📝 Суммаризация проекта", callback_data="summary_menu")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "📋 *Проекты*\n\n"
            "📋 *Статус* - просмотр статуса проектов и задач\n"
            "📝 *Суммаризация* - краткая сводка по проекту",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Подменю "Инструменты"
    elif query.data == "menu_tools":
        keyboard = [
            [InlineKeyboardButton("📝 Сгенерировать КП", callback_data="generate_proposal")],
            [InlineKeyboardButton("📄 Быстрая суммаризация", callback_data="quick_summary_menu")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "🛠 *Инструменты*\n\n"
            "📝 *Генерация КП* - создать коммерческое предложение\n"
            "📄 *Суммаризация* - краткая сводка текста",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Подменю "Помощь"
    elif query.data == "menu_help":
        keyboard = [
            [InlineKeyboardButton("📖 Команды бота", callback_data="help_commands")],
            [InlineKeyboardButton("💡 Примеры использования", callback_data="help_examples")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "❓ *Помощь*\n\n"
            "📖 *Команды* - список всех команд\n"
            "💡 *Примеры* - примеры использования",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Обработчики помощи
    elif query.data == "help_commands":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_help")]]
        await query.edit_message_text(
            "📖 *Команды бота:*\n\n"
            "**Основные:**\n"
            "`/start` - главное меню\n"
            "`/menu` - главное меню\n\n"
            "**База знаний (RAG):**\n"
            "`/rag_search [запрос]` - поиск в базе знаний\n"
            "`/rag_stats` - статистика базы\n"
            "`/rag_docs` - список документов\n\n"
            "**WEEEK проекты:**\n"
            "`/weeek_projects` - список проектов\n"
            "`/weeek_task [проект] | [задача]` - создать задачу\n"
            "`/status` - статус проектов\n\n"
            "**Email:**\n"
            "`/email_check` - проверить новые письма\n"
            "`/email_draft [текст]` - черновик ответа\n\n"
            "**Генерация:**\n"
            "`/demo_proposal [запрос]` - КП\n"
            "`/hypothesis [описание]` - гипотезы\n"
            "`/report [проект]` - отчёт\n"
            "`/summary [проект]` - суммаризация\n\n"
            "**Загрузка документов:**\n"
            "`/upload` - инструкция по загрузке\n"
            "Отправьте PDF/Word/Excel файл для индексации",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    elif query.data == "help_examples":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_help")]]
        await query.edit_message_text(
            "💡 *Примеры использования:*\n\n"
            "🔍 *Поиск:*\n"
            "`/rag_search подбор персонала`\n"
            "`/rag_search автоматизация HR`\n\n"
            "📝 *Генерация КП:*\n"
            "`/demo_proposal нужна помощь с подбором HR-менеджера`\n\n"
            "📋 *Проекты:*\n"
            "`/status` - список проектов\n"
            "`/summary Проект X` - сводка по проекту",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Суммаризация
    elif query.data == "summary_menu":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
        await query.edit_message_text(
            "📝 *Суммаризация проекта*\n\n"
            "Используйте команду:\n"
            "`/summary [название проекта]`\n\n"
            "Например:\n"
            "`/summary Подбор HR-менеджера`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    elif query.data == "quick_summary_menu":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_tools")]]
        await query.edit_message_text(
            "📄 *Быстрая суммаризация*\n\n"
            "Отправьте текст для суммаризации, и я создам краткую сводку.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Новые обработчики для консалтингового меню
    elif query.data == "rag_search_menu":
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_knowledge_base")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "🔍 *Поиск в базе знаний*\n\n"
            "Используйте команду:\n"
            "`/rag_search [ваш запрос]`\n\n"
            "Например:\n"
            "`/rag_search подбор персонала`\n"
            "`/rag_search автоматизация HR процессов`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "generate_proposal":
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_tools")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "📝 *Генерация коммерческого предложения*\n\n"
            "Используйте команду:\n"
            "`/demo_proposal [запрос клиента]`\n\n"
            "Например:\n"
            "`/demo_proposal нужна помощь с подбором HR-менеджера`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "rag_stats":
        try:
            from qdrant_helper import get_collection_stats
            stats = await get_collection_stats()
            
            if "error" in stats:
                text = f"❌ Ошибка: {stats['error']}"
            else:
                text = f"📊 *Статистика RAG базы знаний*\n\n"
                text += f"Коллекция: `{stats.get('collection_name', 'N/A')}`\n"
                text += f"Существует: {'✅' if stats.get('exists') else '❌'}\n"
                if stats.get('exists'):
                    text += f"Документов: {stats.get('points_count', 0)}\n"
                    text += f"Размерность векторов: {stats.get('vector_size', 'N/A')}\n"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="menu_knowledge_base")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            log.error(f"❌ Ошибка получения статистики: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    elif query.data == "rag_docs":
        try:
            from qdrant_helper import list_documents
            docs = await list_documents(limit=20)
            
            if docs:
                text = f"📚 *Документы в базе знаний* (показано: {len(docs)})\n\n"
                for i, doc in enumerate(docs[:10], 1):
                    title = doc.get("title", "Без названия")
                    category = doc.get("category", "Неизвестно")
                    text += f"*{i}. {title}*\n"
                    text += f"   Категория: {category}\n\n"
                if len(docs) > 10:
                    text += f"... и еще {len(docs) - 10} документов"
            else:
                text = "❌ В базе знаний нет документов."
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="menu_knowledge_base")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
            ]
            await query.edit_message_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            log.error(f"❌ Ошибка получения списка документов: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    elif query.data == "status":
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "📋 *Статус проектов*\n\n"
            "Используйте команду:\n"
            "`/status`\n\n"
            "Для суммаризации проекта:\n"
            "`/summary [название проекта]`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "chat":
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
        await query.edit_message_text(
            "💬 *Чат с AI*\n\n"
            "Теперь вы можете писать сообщения для общения с AI-помощником.\n\n"
            "Ассистент использует базу знаний для формирования ответов.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    # Старые обработчики (для обратной совместимости, можно будет удалить)
    elif query.data == "services":
        await show_services(query)
    elif query.data == "masters":
        await show_masters(query)
    elif query.data == "my_records":
        await show_user_records(query)
    elif query.data == "book_appointment":
        await start_booking_process(query)
    elif query.data == "back_to_menu":
        await show_main_menu(query)
    elif query.data.startswith("delete_record_"):
        # Старый формат для обратной совместимости
        record_id = query.data.replace("delete_record_", "")
        try:
            record_id_int = int(record_id)
            await delete_user_record(query, str(record_id_int))
        except ValueError:
            await delete_user_record(query, record_id)
    elif query.data.startswith("delete_booking_"):
        # Новый формат с booking_id из Google Sheets
        booking_id = query.data.replace("delete_booking_", "")
        await delete_user_record(query, booking_id)
    elif query.data == "reset_session":
        await reset_user_session(query)
    elif query.data.startswith("delete_booking_"):
        # Новый формат с booking_id из Google Sheets
        booking_id = query.data.replace("delete_booking_", "")
        await delete_user_record(query, booking_id)
    elif query.data == "reset_session":
        await reset_user_session(query)
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
    """Показать записи пользователя из Google Sheets"""
    user_id = query.from_user.id
    
    # Получаем записи из Google Sheets
    try:
        bookings = get_user_bookings(user_id)
    except Exception as e:
        log.error(f"❌ Ошибка получения записей: {e}")
        bookings = []
    
    if not bookings:
        keyboard = [
            [InlineKeyboardButton("📝 Записаться", callback_data="book_appointment")],
            [InlineKeyboardButton("🔄 Начать заново", callback_data="reset_session")],
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
    
    # Показываем все записи (или первые 10, если их много)
    for i, booking in enumerate(bookings[:10], 1):
        date_time = booking.get("datetime", f"{booking.get('date', '')} {booking.get('time', '')}")
        master = booking.get("master", "Не указан")
        service = booking.get("service", "Не указана")
        price = booking.get("price", 0)
        booking_id = booking.get("id", "")
        
        text += f"📋 *Запись {i}:*\n"
        text += f"📅 Дата: {date_time}\n"
        text += f"👤 Мастер: *{master}*\n"
        text += f"💇 Услуга: *{service}*\n"
        if price > 0:
            text += f"💰 Цена: {price} ₽\n"
        text += f"🆔 ID: `{booking_id}`\n\n"
        
        # Добавляем кнопку удаления для каждой записи
        keyboard.append([
            InlineKeyboardButton(
                f"🗑 Удалить запись {i}", 
                callback_data=f"delete_booking_{booking_id}"
            )
        ])
    
    if len(bookings) > 10:
        text += f"\n... и еще {len(bookings) - 10} записей\n"
    
    keyboard.append([InlineKeyboardButton("🔄 Начать заново", callback_data="reset_session")])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text, 
        parse_mode='Markdown', 
        reply_markup=reply_markup
    )

async def delete_user_record(query: CallbackQuery, booking_id: str):
    """Удалить запись пользователя из Google Sheets (только свои записи)"""
    user_id = query.from_user.id
    
    try:
        # Удаляем из Google Sheets (проверка прав выполняется внутри функции)
        success = delete_user_booking(user_id, booking_id)
        
        if success:
            # Также удаляем из локального хранилища если есть
            try:
                remove_user_record(user_id, booking_id)
            except:
                pass  # Не критично, если нет в локальном хранилище
            
            keyboard = [
                [InlineKeyboardButton("📅 Мои записи", callback_data="my_records")],
                [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
            ]
            await query.edit_message_text(
                f"✅ Запись успешно удалена!\n\n"
                f"🆔 ID записи: `{booking_id}`",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.answer("❌ Не удалось удалить запись. Возможно, она уже удалена или не принадлежит вам.", show_alert=True)
            await show_user_records(query)
    except Exception as e:
        log.error(f"❌ Ошибка удаления записи: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await query.answer("❌ Ошибка при удалении записи. Попробуйте позже.", show_alert=True)
        await show_user_records(query)

async def reset_user_session(query: CallbackQuery):
    """Сбросить сессию пользователя (начать заново)"""
    user_id = query.from_user.id
    
    try:
        # Очищаем память разговора
        if user_id in UserMemory:
            UserMemory[user_id] = deque(maxlen=MEMORY_TURNS)
        
        # Очищаем локальные записи (но не удаляем из Google Sheets)
        if user_id in UserRecords:
            UserRecords[user_id] = []
        
        # Очищаем частично собранные данные для записи
        if user_id in UserBookingData:
            del UserBookingData[user_id]
        
        # Очищаем имя и телефон (опционально, можно оставить)
        # if user_id in UserName:
        #     del UserName[user_id]
        # if user_id in UserPhone:
        #     del UserPhone[user_id]
        
        keyboard = [
            [InlineKeyboardButton("📝 Записаться", callback_data="book_appointment")],
            [InlineKeyboardButton("📅 Мои записи", callback_data="my_records")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        
        await query.edit_message_text(
            "🔄 *Сессия сброшена*\n\n"
            "Вы можете начать новый диалог.\n\n"
            "💡 *Что дальше?*\n"
            "• Используйте кнопку \"📝 Записаться\"\n"
            "• Или напишите в чат \"хочу записаться\"\n"
            "• Просмотрите свои записи через \"📅 Мои записи\"",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        log.error(f"❌ Ошибка сброса сессии: {e}")
        await query.answer("❌ Ошибка при сбросе сессии", show_alert=True)

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
        [InlineKeyboardButton("📚 База знаний", callback_data="menu_knowledge_base")],
        [InlineKeyboardButton("📋 Проекты", callback_data="menu_projects")],
        [InlineKeyboardButton("🛠 Инструменты", callback_data="menu_tools")],
        [InlineKeyboardButton("💬 Чат с AI", callback_data="chat")],
        [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🏠 *Главное меню*\n\n"
        "📚 *База знаний* - поиск, документы, статистика\n"
        "📋 *Проекты* - управление проектами и задачами\n"
        "🛠 *Инструменты* - генерация КП, суммаризация\n"
        "💬 *Чат с AI* - общение с AI-помощником\n"
        "❓ *Помощь* - справочная информация",
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
    username = update.message.from_user.username or "без username"
    first_name = update.message.from_user.first_name or "без имени"
    
    # Логируем ВСЕ входящие сообщения для отладки
    log.info(f"📨 ВХОДЯЩЕЕ СООБЩЕНИЕ: user_id={user_id}, username=@{username}, name={first_name}, text='{text[:100]}'")
    
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

    # БЫСТРАЯ ПРОВЕРКА: Если есть мастер, время и услуга/цена - это точно запрос на запись
    # Это работает лучше чем сложный классификатор для очевидных случаев
    text_lower = text.lower()
    services_list = get_services()
    masters_list = get_masters()
    
    # Проверяем наличие мастера
    has_master = any(master.get("name", "").lower() in text_lower for master in masters_list)
    
    # Проверяем наличие времени (форматы: HH:MM, завтра, сегодня, дата)
    import re
    has_time = bool(
        re.search(r'\d{1,2}:\d{2}', text) or  # HH:MM
        re.search(r'\d{1,2}[./]\d{1,2}[./]\d{2,4}', text) or  # Дата
        "завтра" in text_lower or "сегодня" in text_lower or
        any(word in text_lower for word in ["час", "часа", "часов", "утра", "дня", "вечера"])
    )
    
    # Проверяем наличие услуги или цены
    has_service = any(service.get("title", "").lower() in text_lower for service in services_list)
    has_price = bool(re.search(r'\d+\s*[₽руб]', text) or re.search(r'\d{3,4}', text))  # Цена в формате 1700 или 1700₽
    
    # Если есть мастер + время + (услуга или цена) - это точно запрос на запись
    is_obvious_booking = has_master and has_time and (has_service or has_price)
    
    if is_obvious_booking:
        log.info(f"✅ ОЧЕВИДНЫЙ ЗАПРОС НА ЗАПИСЬ (быстрая проверка): мастер={has_master}, время={has_time}, услуга={has_service}, цена={has_price}")
        is_booking_result = True
        intent_details = {"method": "quick_check", "final_score": 1.0}
    else:
        # Используем улучшенный классификатор намерений только если быстрая проверка не сработала
        try:
            from intent_classifier import is_booking_intent
            # Используем LLM для классификации если доступен OpenRouter API
            use_llm = bool(OPENROUTER_API_KEY)
            is_booking_result, intent_details = is_booking_intent(
                text, 
                services=services_list, 
                masters=masters_list, 
                threshold=0.4,
                use_llm=use_llm,
                openrouter_api_key=OPENROUTER_API_KEY if use_llm else None,
                openrouter_url=OPENROUTER_API_URL if use_llm else None
            )
            log.info(f"🎯 INTENT CLASSIFIER: score={intent_details.get('final_score', 0):.3f}, method={intent_details.get('method', 'unknown')}")
        except ImportError:
            # Fallback на старый метод если новый классификатор недоступен
            is_booking_result = is_booking(text)
            intent_details = {}
            log.debug("⚠️ Новый классификатор намерений недоступен, используется старый метод")
        except Exception as e:
            log.error(f"❌ Ошибка классификатора намерений: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            is_booking_result = is_booking(text)
            intent_details = {}
    
    if is_booking_result:
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
            # КРИТИЧЕСКОЕ: Проверяем, есть ли сохраненные данные для записи
            # Если пользователь отвечает на вопрос бота (например, просто "Роман"), 
            # нужно использовать сохраненные данные и попытаться создать запись
            if user_id in UserBookingData and UserBookingData[user_id]:
                log.info(f"📋 Найдены сохраненные данные для записи: {UserBookingData[user_id]}")
                
                # Парсим текущее сообщение для извлечения новых данных
                history = get_recent_history(user_id, 50)
                parsed_data = parse_booking_message(text, history)
                
                # Обновляем сохраненные данные новыми (если они есть)
                if parsed_data.get("service"):
                    UserBookingData[user_id]["service"] = parsed_data.get("service")
                if parsed_data.get("master"):
                    UserBookingData[user_id]["master"] = parsed_data.get("master")
                if parsed_data.get("datetime"):
                    UserBookingData[user_id]["datetime"] = parsed_data.get("datetime")
                
                # Объединяем сохраненные данные с текущими
                combined_data = {
                    "service": UserBookingData[user_id].get("service") or parsed_data.get("service"),
                    "master": UserBookingData[user_id].get("master") or parsed_data.get("master"),
                    "datetime": UserBookingData[user_id].get("datetime") or parsed_data.get("datetime")
                }
                
                log.info(f"📋 Объединенные данные после ответа на вопрос: service={combined_data.get('service')}, master={combined_data.get('master')}, datetime={combined_data.get('datetime')}")
                
                # Если все данные собраны, создаем запись
                if combined_data.get("service") and combined_data.get("master") and combined_data.get("datetime"):
                    log.info(f"✅ Все данные собраны после ответа на вопрос! Создаем запись: {combined_data}")
                    try:
                        user_phone = UserPhone.get(user_id, "")
                        client_name = update.message.from_user.first_name or "Клиент"
                        
                        booking_record = create_real_booking(
                            user_id,
                            combined_data.get("service"),
                            combined_data.get("master"),
                            combined_data.get("datetime"),
                            client_name=client_name,
                            client_phone=user_phone
                        )
                        
                        log.info(f"✅ Запись создана после ответа на вопрос: {booking_record.get('id', 'N/A')}")
                        
                        # Очищаем сохраненные данные после успешного создания
                        if user_id in UserBookingData:
                            del UserBookingData[user_id]
                        
                        answer = f"🎉 *Запись успешно создана в системе!* 🎉\n\n"
                        answer += f"📅 *Услуга:* {combined_data.get('service')}\n"
                        answer += f"👤 *Мастер:* {combined_data.get('master')}\n"
                        answer += f"⏰ *Время:* {combined_data.get('datetime')}\n\n"
                        answer += "Спасибо за запись! Ждем вас в салоне! ✨"
                        response_sent = True
                        await update.message.reply_text(answer)
                        return
                    except Exception as e:
                        log.error(f"❌ Ошибка создания записи после ответа на вопрос: {e}")
                        import traceback
                        log.error(f"❌ Traceback: {traceback.format_exc()}")
                        # Продолжаем обычную обработку
                else:
                    # Данных все еще недостаточно, задаем вопросы
                    missing_fields = []
                    questions = []
                    
                    if not combined_data.get("service"):
                        missing_fields.append("услуга")
                        services = get_services()
                        services_list = ", ".join([s.get("title") for s in services[:5]])
                        questions.append(f"📋 *Какая услуга вам нужна?*\n\nНапример: {services_list}...")
                    
                    if not combined_data.get("master"):
                        missing_fields.append("мастер")
                        masters = get_masters()
                        masters_list = ", ".join([m.get("name") for m in masters])
                        questions.append(f"👤 *К какому мастеру хотите записаться?*\n\nДоступны: {masters_list}")
                    
                    if not combined_data.get("datetime"):
                        missing_fields.append("дата и время")
                        questions.append(f"📅 *На какое время записаться?*\n\nНапример: завтра 17:00, или 10.12.2025 15:00")
                    
                    if missing_fields:
                        question_text = f"❓ *Нужна дополнительная информация для записи*\n\n"
                        question_text += "\n".join(questions)
                        question_text += f"\n\n💡 Укажите недостающие данные: {', '.join(missing_fields)}"
                        answer = question_text
                        response_sent = True
                        await update.message.reply_text(answer)
                        return
            
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
                        
                        # Сначала ищем ТОЧНОЕ совпадение (приоритет)
                        best_match = None
                        best_score = 0
                        
                        for service in all_services:
                            service_title = service.get("title", "").lower()
                            service_words = set(service_title.split())
                            text_words = set(text_lower.split())
                            
                            # Вычисляем score совпадения
                            score = 0
                            
                            # Точное совпадение - максимальный приоритет
                            if service_title == text_lower:
                                score = 100
                            # Полное вхождение названия услуги в запрос
                            elif service_title in text_lower:
                                score = 80
                            # Полное вхождение запроса в название услуги
                            elif text_lower in service_title:
                                score = 70
                            # Совпадение всех слов
                            elif service_words == text_words:
                                score = 60
                            # Совпадение 2+ слов
                            elif len(service_words & text_words) >= 2:
                                score = 40 + len(service_words & text_words) * 10
                            # Частичное совпадение отдельных слов
                            elif any(word in service_title for word in text_lower.split() if len(word) > 3):
                                score = 20
                            
                            if score > best_score:
                                best_score = score
                                best_match = service
                        
                        # Используем лучший match, если score достаточно высокий
                        if best_match and best_score >= 20:
                            service = best_match
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
                            found_service_info += f"📊 SCORE: {best_score}\n"
                            found_service_info += f"\n❌ ЗАПРЕЩЕНО выдумывать цены! Используй ТОЛЬКО эту информацию!\n"
                            
                            log.info(f"✅ Найдена услуга детерминистически: {service.get('title')} - {price_info} (score: {best_score})")
                            log.info(f"   Детали: price={price}, price_str='{price_str}', duration={duration}, master='{master}'")
                except Exception as e:
                    log.error(f"❌ Ошибка поиска услуги: {e}")
                    import traceback
                    log.error(f"❌ Traceback: {traceback.format_exc()}")
                
                # Формируем промпт правильно
                msg = BOOKING_PROMPT.replace("{{api_data}}", api_data).replace("{{message}}", text).replace("{{history}}", history).replace("{{service_info}}", found_service_info)
                
                # Логируем полный промпт для отладки (первые 2000 символов)
                log.info(f"🤖 AI PROMPT длина: {len(msg)} символов")
                log.info(f"📝 ПРОМПТ (первые 2000 символов):\n{msg[:2000]}...")
                if found_service_info:
                    log.info(f"✅ Service info добавлена в промпт: {found_service_info[:200]}...")
                
                # Используем system message для более строгих инструкций
                system_msg = """Ты помощник салона красоты. КРИТИЧЕСКИ ВАЖНО: 
- Используй ТОЛЬКО цены из предоставленного списка услуг
- НИКОГДА не выдумывай цены
- Если услуга есть в списке - используй ТОЧНУЮ цену
- Если видишь блок "НАЙДЕНА УСЛУГА" - используй ТОЧНО эти данные"""
                
                answer = await openrouter_chat([{"role": "user", "content": msg}], use_system_message=True, system_content=system_msg)
                log.info(f"🤖 AI RESPONSE: {answer[:300]}...")  # Логируем больше для проверки
            
            # ИНТЕГРАЦИЯ СЦЕНАРИЙ 3: Обработка лида через Telegram (до обычной логики)
            # Проверяем, является ли это потенциальным лидом (не запись на услугу)
            is_lead_query = not any(keyword in text_lower for keyword in [
                "запись", "записаться", "записать", "мастер", "маникюр", "стрижка", 
                "педикюр", "окрашивание", "роман", "анжела", "хочу записаться"
            ])
            
            # Если это похоже на бизнес-запрос, обрабатываем через Сценарий 3
            if is_lead_query and len(text) > 20:  # Игнорируем короткие сообщения
                try:
                    from scenario_workflows import process_telegram_lead
                    lead_result = await process_telegram_lead(
                        user_message=text,
                        user_id=user_id,
                        user_name=first_name,
                        telegram_bot=context.bot
                    )
                    
                    # Если лид был обработан и создан проект, логируем
                    if lead_result.get("success") and lead_result.get("weeek_project_created"):
                        log.info(f"✅ [Сценарий 3] Лид обработан, проект создан в WEEEK")
                        # Продолжаем обычную обработку для отправки ответа пользователю
                except Exception as e:
                    log.warning(f"⚠️ Ошибка обработки через Сценарий 3: {e}, продолжаем обычную обработку")
            
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
        # Проверяем, является ли это общим вопросом (не связанным с HR/бизнесом)
        general_question_keywords = [
            "how are you", "как дела", "как поживаешь", "привет", "hello", "hi",
            "что нового", "what's new", "как жизнь", "how's life"
        ]
        is_general_question = any(keyword in text.lower() for keyword in general_question_keywords)
        
        if is_general_question:
            # Отвечаем на общие вопросы с напоминанием о HR контексте
            answer = (
                "Привет! У меня всё отлично, спасибо! 😊\n\n"
                "Напоминаю, что я AI-ассистент Анастасии Новосёловой, специализируюсь на:\n"
                "• Подборе персонала (рекрутинг)\n"
                "• Автоматизации HR-процессов\n"
                "• Бизнес-анализе и консалтинге\n\n"
                "Чем могу помочь в рамках HR консалтинга? 💼"
            )
            log.info("💬 Общий вопрос обработан с напоминанием о HR контексте")
        else:
            # Обычная обработка через RAG и LLM
            # Обычная обработка через RAG и LLM
            msg = CONSULTING_PROMPT.replace("{{history}}", get_history(user_id)).replace("{{message}}", text)
            
            # Пытаемся использовать RAG для контекста
            rag_context = ""
            try:
                if QDRANT_AVAILABLE:
                    from rag_chain import RAGChain
                    rag_chain = RAGChain()
                    rag_result = await rag_chain.query(text, use_rag=True, top_k=3)
                    if rag_result.get("context_docs"):
                        context_text = "\n".join([doc.get("content", "")[:200] for doc in rag_result["context_docs"][:3]])
                        rag_context = f"Релевантная информация из базы знаний:\n{context_text}\n\n"
            except Exception as e:
                log.warning(f"⚠️ Ошибка RAG поиска: {e}")
            
            msg = msg.replace("{{rag_context}}", rag_context)
            
            # Используем generate_with_fallback для надежности
            try:
                from llm_helper import generate_with_fallback
                answer = await generate_with_fallback([{"role": "user", "content": msg}], use_system_message=True, system_content="Ты AI-ассистент HR консультанта. Отвечай профессионально и по делу.")
            except Exception as e:
                log.error(f"❌ Ошибка вызова generate_with_fallback: {e}")
                answer = None
            
            # Если LLM недоступен, используем fallback ответ
            if not answer or answer.strip() == "":
                answer = (
                    "Извините, сейчас у меня технические проблемы с подключением к AI.\n\n"
                    "Но я могу помочь вам с вопросами по:\n"
                    "• Подбору персонала\n"
                    "• HR-процессам\n"
                    "• Бизнес-консалтингу\n\n"
                    "Попробуйте переформулировать вопрос или обратитесь позже."
                )

    add_memory(user_id, "assistant", answer)
    
    # КРИТИЧЕСКОЕ: Проверяем ответ AI на подтверждение записи
    # Если AI подтвердил запись (даже если is_booking() вернул False), создаем запись автоматически
    if answer and not response_sent:
        answer_lower = answer.lower()
        confirmation_keywords = [
            "записали", "записала", "записан", "записана", "записано",
            "подтверждена", "подтвержден", "подтверждено", "подтвердил",
            "запись создана", "запись оформлена", "запись подтверждена"
        ]
        
        is_confirmed = any(keyword in answer_lower for keyword in confirmation_keywords)
        
        if is_confirmed:
            log.info(f"✅ AI подтвердил запись в ответе: '{answer[:100]}...'")
            
            # Пытаемся извлечь данные из истории и ответа AI
            history = get_recent_history(user_id, 50)
            parsed_data = parse_booking_message(text, history)
            
            log.info(f"🔍 Начальные данные из parse_booking_message: service={parsed_data.get('service')}, master={parsed_data.get('master')}, datetime={parsed_data.get('datetime')}")
            
            # КРИТИЧЕСКОЕ: Всегда пытаемся извлечь данные из ответа AI, даже если parse_booking_message не нашел их
            import re
            
            # Извлекаем мастера из ответа AI
            if not parsed_data.get("master"):
                masters = get_masters()
                for master in masters:
                    master_name = master.get("name", "")
                    if master_name.lower() in answer_lower:
                        parsed_data["master"] = master_name
                        log.info(f"✅ Найден мастер из ответа AI: {master_name}")
                        break
            
            # Извлекаем услугу из истории или ответа AI (КРИТИЧЕСКИ ВАЖНО!)
            if not parsed_data.get("service"):
                services = get_services()
                history_lower = history.lower()
                answer_lower_lower = answer_lower
                
                # Сначала ищем точное совпадение в истории (приоритет)
                found_service = None
                for service in services:
                    service_title = service.get("title", "").lower()
                    # Точное совпадение
                    if service_title in history_lower:
                        found_service = service.get("title")
                        log.info(f"✅ Найдена услуга из истории (точное совпадение): {found_service}")
                        break
                
                # Если не нашли, ищем частичное совпадение в истории
                if not found_service:
                    for service in services:
                        service_title = service.get("title", "").lower()
                        # Разбиваем название услуги на слова и ищем каждое слово
                        service_words = service_title.split()
                        for word in service_words:
                            if len(word) > 3 and word in history_lower:  # Игнорируем короткие слова
                                found_service = service.get("title")
                                log.info(f"✅ Найдена услуга из истории (частичное совпадение '{word}'): {found_service}")
                                break
                        if found_service:
                            break
                
                # Если не нашли в истории, ищем в ответе AI
                if not found_service:
                    for service in services:
                        service_title = service.get("title", "").lower()
                        if service_title in answer_lower_lower:
                            found_service = service.get("title")
                            log.info(f"✅ Найдена услуга из ответа AI: {found_service}")
                            break
                
                # Если все еще не нашли, ищем в исходном сообщении пользователя
                if not found_service:
                    text_lower = text.lower()
                    for service in services:
                        service_title = service.get("title", "").lower()
                        if service_title in text_lower:
                            found_service = service.get("title")
                            log.info(f"✅ Найдена услуга из исходного сообщения: {found_service}")
                            break
                
                # Если нашли услугу, сохраняем её
                if found_service:
                    parsed_data["service"] = found_service
                else:
                    log.warning(f"⚠️ Услуга не найдена ни в истории, ни в ответе AI, ни в сообщении пользователя")
            
            # Извлекаем дату/время из ответа AI
            if not parsed_data.get("datetime"):
                # Парсим дату/время из ответа AI
                date_time_pattern = r'(\d{1,2})[./](\d{1,2})[./](\d{4})\s+(\d{1,2}):(\d{2})'
                match = re.search(date_time_pattern, answer)
                if match:
                    day, month, year, hour, minute = match.groups()
                    parsed_data["datetime"] = f"{day.zfill(2)}.{month.zfill(2)}.{year} {hour.zfill(2)}:{minute}"
                    log.info(f"✅ Найдена дата/время из ответа AI (формат DD.MM.YYYY): {parsed_data['datetime']}")
                else:
                    # Пробуем найти относительные даты в ответе
                    if "завтра" in answer_lower:
                        tomorrow = datetime.now() + timedelta(days=1)
                        time_match = re.search(r'(\d{1,2}):?(\d{2})?', answer)
                        if time_match:
                            hour = time_match.group(1)
                            minute = time_match.group(2) or "00"
                            parsed_data["datetime"] = f"{tomorrow.strftime('%d.%m.%Y')} {hour.zfill(2)}:{minute.zfill(2)}"
                            log.info(f"✅ Найдена дата/время из ответа AI (завтра): {parsed_data['datetime']}")
                    elif "сегодня" in answer_lower:
                        today = datetime.now()
                        time_match = re.search(r'(\d{1,2}):?(\d{2})?', answer)
                        if time_match:
                            hour = time_match.group(1)
                            minute = time_match.group(2) or "00"
                            parsed_data["datetime"] = f"{today.strftime('%d.%m.%Y')} {hour.zfill(2)}:{minute.zfill(2)}"
                            log.info(f"✅ Найдена дата/время из ответа AI (сегодня): {parsed_data['datetime']}")
            
            # КРИТИЧЕСКОЕ: Если услуга не найдена, но есть мастер и время, используем последнюю упомянутую услугу из истории
            if not parsed_data.get("service") and parsed_data.get("master") and parsed_data.get("datetime"):
                # Ищем последнюю упомянутую услугу в полной истории чата
                services = get_services()
                history_full = get_history(user_id)  # Полная история, не только последние 50 символов
                history_full_lower = history_full.lower()
                
                # Ищем все упоминания услуг в истории и берем последнюю
                last_mentioned_service = None
                last_position = -1
                for service in services:
                    service_title = service.get("title", "").lower()
                    position = history_full_lower.rfind(service_title)  # Ищем последнее вхождение
                    if position > last_position:
                        last_position = position
                        last_mentioned_service = service.get("title")
                
                if last_mentioned_service:
                    parsed_data["service"] = last_mentioned_service
                    log.info(f"✅ Использована последняя упомянутая услуга из полной истории: {last_mentioned_service}")
                else:
                    log.warning(f"⚠️ Не удалось найти услугу даже в полной истории чата")
            
            # Если есть все данные, создаем запись
            log.info(f"🔍 Финальная проверка данных для создания записи: service={parsed_data.get('service')}, master={parsed_data.get('master')}, datetime={parsed_data.get('datetime')}")
            
            # Создаем запись если есть все необходимые данные
            if parsed_data.get("service") and parsed_data.get("master") and parsed_data.get("datetime"):
                try:
                    user_phone = UserPhone.get(user_id, "")
                    client_name = update.message.from_user.first_name or "Клиент"
                    
                    log.info(f"🚀 СОЗДАНИЕ ЗАПИСИ из подтверждения AI: service={parsed_data.get('service')}, master={parsed_data.get('master')}, datetime={parsed_data.get('datetime')}, phone={user_phone or 'не указан'}")
                    
                    # Создаем запись даже без номера телефона (можно добавить позже)
                    booking_record = create_real_booking(
                        user_id,
                        parsed_data.get("service"),
                        parsed_data.get("master"),
                        parsed_data.get("datetime"),
                        client_name=client_name,
                        client_phone=user_phone
                    )
                    log.info(f"✅ Запись автоматически создана из подтверждения AI: {booking_record.get('id', 'N/A')}")
                    
                    # Обновляем ответ, чтобы показать что запись создана
                    if "🎉" not in answer:
                        answer = f"🎉 *Запись успешно создана в системе!* 🎉\n\n{answer}"
                except Exception as e:
                    log.error(f"❌ Ошибка автоматического создания записи из подтверждения AI: {e}")
                    import traceback
                    log.error(f"❌ Traceback: {traceback.format_exc()}")
                    # Не меняем ответ пользователю, чтобы не показывать ошибку
            else:
                log.warning(f"⚠️ Недостаточно данных для создания записи: service={parsed_data.get('service')}, master={parsed_data.get('master')}, datetime={parsed_data.get('datetime')}")
                
                # МЕХАНИЗМ СБОРА ДАННЫХ: Сохраняем частично собранные данные и задаем вопросы
                # Объединяем данные из текущего сообщения с уже сохраненными
                if user_id not in UserBookingData:
                    UserBookingData[user_id] = {}
                
                # Обновляем сохраненные данные новыми (если они есть)
                if parsed_data.get("service"):
                    UserBookingData[user_id]["service"] = parsed_data.get("service")
                if parsed_data.get("master"):
                    UserBookingData[user_id]["master"] = parsed_data.get("master")
                if parsed_data.get("datetime"):
                    UserBookingData[user_id]["datetime"] = parsed_data.get("datetime")
                
                # Объединяем сохраненные данные с текущими
                combined_data = {
                    "service": UserBookingData[user_id].get("service") or parsed_data.get("service"),
                    "master": UserBookingData[user_id].get("master") or parsed_data.get("master"),
                    "datetime": UserBookingData[user_id].get("datetime") or parsed_data.get("datetime")
                }
                
                log.info(f"📋 Объединенные данные: service={combined_data.get('service')}, master={combined_data.get('master')}, datetime={combined_data.get('datetime')}")
                
                # Определяем недостающие данные и задаем вопросы
                missing_fields = []
                questions = []
                
                if not combined_data.get("service"):
                    missing_fields.append("услуга")
                    services = get_services()
                    services_list = ", ".join([s.get("title") for s in services[:5]])  # Первые 5 услуг
                    questions.append(f"📋 *Какая услуга вам нужна?*\n\nНапример: {services_list}...")
                
                if not combined_data.get("master"):
                    missing_fields.append("мастер")
                    masters = get_masters()
                    masters_list = ", ".join([m.get("name") for m in masters])
                    questions.append(f"👤 *К какому мастеру хотите записаться?*\n\nДоступны: {masters_list}")
                
                if not combined_data.get("datetime"):
                    missing_fields.append("дата и время")
                    questions.append(f"📅 *На какое время записаться?*\n\nНапример: завтра 17:00, или 10.12.2025 15:00")
                
                # Если все еще недостаточно данных, задаем вопросы
                if missing_fields:
                    question_text = f"❓ *Нужна дополнительная информация для записи*\n\n"
                    question_text += "\n".join(questions)
                    question_text += f"\n\n💡 Укажите недостающие данные: {', '.join(missing_fields)}"
                    
                    # Если ответ AI уже был сформирован, добавляем вопрос к нему
                    if answer:
                        answer = f"{answer}\n\n{question_text}"
                    else:
                        answer = question_text
                    
                    log.info(f"❓ Заданы вопросы о недостающих данных: {missing_fields}")
                else:
                    # Все данные собраны! Создаем запись
                    log.info(f"✅ Все данные собраны! Создаем запись: {combined_data}")
                    try:
                        user_phone = UserPhone.get(user_id, "")
                        client_name = update.message.from_user.first_name or "Клиент"
                        
                        booking_record = create_real_booking(
                            user_id,
                            combined_data.get("service"),
                            combined_data.get("master"),
                            combined_data.get("datetime"),
                            client_name=client_name,
                            client_phone=user_phone
                        )
                        
                        log.info(f"✅ Запись создана после сбора данных: {booking_record.get('id', 'N/A')}")
                        
                        # Очищаем сохраненные данные после успешного создания
                        if user_id in UserBookingData:
                            del UserBookingData[user_id]
                        
                        # Обновляем ответ
                        if answer:
                            answer = f"🎉 *Запись успешно создана в системе!* 🎉\n\n{answer}"
                        else:
                            answer = f"🎉 *Запись успешно создана!* 🎉\n\n"
                            answer += f"📅 *Услуга:* {combined_data.get('service')}\n"
                            answer += f"👤 *Мастер:* {combined_data.get('master')}\n"
                            answer += f"⏰ *Время:* {combined_data.get('datetime')}\n\n"
                            answer += "Спасибо за запись! Ждем вас в салоне! ✨"
                    except Exception as e:
                        log.error(f"❌ Ошибка создания записи после сбора данных: {e}")
                        import traceback
                        log.error(f"❌ Traceback: {traceback.format_exc()}")
                        if not answer:
                            answer = f"❌ Произошла ошибка при создании записи. Попробуйте еще раз."
    
    # Отправляем ответ только если он не был отправлен ранее
    if answer and not response_sent:  # Проверяем что есть ответ для отправки
            await update.message.reply_text(answer)

# ===================== NEW COMMANDS FOR DEMONSTRATION =====================

async def rag_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rag_search - поиск в RAG базе знаний"""
    query = " ".join(context.args) if context.args else "помощь"
    
    try:
        from qdrant_helper import search_with_preview
        results = await search_with_preview(query, limit=5)
        
        if results.get("results"):
            text = f"🔍 *Результаты поиска в RAG базе:*\n\n"
            text += f"Запрос: {query}\n"
            text += f"Найдено: {results['total_results']} результатов\n\n"
            
            for i, result in enumerate(results["results"][:5], 1):
                title = result.get("title", "Документ")
                score = result.get("score", 0)
                text += f"*{i}. {title}* (релевантность: {score:.2f})\n"
                snippet = result.get("text", result.get("content", ""))[:200]
                if snippet:
                    text += f"   {snippet}...\n\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ По запросу '{query}' ничего не найдено в базе знаний.")
    except Exception as e:
        log.error(f"❌ Ошибка поиска в RAG: {e}")
        await update.message.reply_text(f"❌ Ошибка поиска: {str(e)}")

async def rag_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rag_stats - статистика RAG базы знаний"""
    try:
        from qdrant_helper import get_collection_stats
        stats = await get_collection_stats()
        
        if "error" in stats:
            await update.message.reply_text(f"❌ Ошибка: {stats['error']}")
            return
        
        text = f"📊 *Статистика RAG базы знаний*\n\n"
        text += f"Коллекция: `{stats.get('collection_name', 'N/A')}`\n"
        text += f"Существует: {'✅' if stats.get('exists') else '❌'}\n"
        
        if stats.get('exists'):
            text += f"Документов: {stats.get('points_count', 0)}\n"
            text += f"Размерность векторов: {stats.get('vector_size', 'N/A')}\n"
            text += f"Метрика расстояния: {stats.get('distance', 'N/A')}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        log.error(f"❌ Ошибка получения статистики: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def rag_docs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rag_docs - список документов в базе знаний"""
    limit = int(context.args[0]) if context.args and context.args[0].isdigit() else 20
    
    try:
        from qdrant_helper import list_documents
        docs = await list_documents(limit=limit)
        
        if docs:
            text = f"📚 *Документы в базе знаний* (показано: {len(docs)})\n\n"
            
            for i, doc in enumerate(docs[:limit], 1):
                title = doc.get("title", "Без названия")
                category = doc.get("category", "Неизвестно")
                text += f"*{i}. {title}*\n"
                text += f"   Категория: {category}\n\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ В базе знаний нет документов.")
    except Exception as e:
        log.error(f"❌ Ошибка получения списка документов: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def demo_proposal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /demo_proposal - генерация КП для демонстрации"""
    request_text = " ".join(context.args) if context.args else ""
    
    if not request_text:
        await update.message.reply_text(
            "❌ Укажите запрос клиента.\n"
            "Использование: `/demo_proposal нужна помощь с подбором персонала`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from lead_processor import generate_proposal
        
        await update.message.reply_text("⏳ Генерирую коммерческое предложение...")
        
        proposal = await generate_proposal(request_text, lead_contact={})
        
        # Разбиваем длинное сообщение на части если нужно
        if len(proposal) > 4000:
            # Отправляем по частям
            parts = [proposal[i:i+4000] for i in range(0, len(proposal), 4000)]
            for part in parts:
                await update.message.reply_text(f"*Черновик КП:*\n\n{part}", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"*Черновик КП:*\n\n{proposal}", parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка генерации КП: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка генерации КП: {str(e)}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status - статус проектов"""
    try:
        from weeek_helper import get_project_deadlines
        
        # Получаем проекты с ближайшими дедлайнами
        upcoming_tasks = await get_project_deadlines(days_ahead=7)
        
        if upcoming_tasks:
            text = "📋 *Статус проектов и задачи*\n\n"
            text += f"Задачи с дедлайнами на ближайшие 7 дней:\n\n"
            
            for task in upcoming_tasks[:10]:  # Показываем первые 10
                task_name = task.get("name", "Задача")
                due_date = task.get("due_date", "Не указан")
                status = task.get("status", "Не указан")
                text += f"• *{task_name}*\n"
                text += f"  Дедлайн: {due_date}\n"
                text += f"  Статус: {status}\n\n"
        else:
            text = "📋 *Статус проектов*\n\n"
            text += "Нет задач с ближайшими дедлайнами.\n\n"
            text += "Используйте WEEEK для управления проектами."
        
        await update.message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        log.error(f"❌ Ошибка получения статуса: {e}")
        await update.message.reply_text(
            "📋 *Статус проектов*\n\n"
            "Используйте WEEEK для управления проектами и задачами.",
            parse_mode='Markdown'
        )

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /summary - суммаризация проекта"""
    project_name = " ".join(context.args) if context.args else "текущий"
    
    try:
        from summary_helper import summarize_project_conversation
        
        # Здесь должна быть логика получения переписки по проекту
        # Пока заглушка
        conversations = [
            {
                "role": "user",
                "content": "Пример сообщения из переписки",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        await update.message.reply_text(f"⏳ Суммаризирую переписку по проекту '{project_name}'...")
        
        summary = await summarize_project_conversation(conversations, project_name=project_name)
        
        await update.message.reply_text(f"*Суммаризация проекта '{project_name}':*\n\n{summary}", parse_mode='Markdown')
    except Exception as e:
        log.error(f"❌ Ошибка суммаризации: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def weeek_create_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weeek_task - создание задачи в Weeek"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Укажите название проекта и задачу.\n"
            "Использование: `/weeek_task [проект] | [задача]`\n\n"
            "Пример: `/weeek_task Подбор HR | Согласовать КП`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from weeek_helper import create_task, get_projects
        
        # Парсим аргументы (формат: проект | задача)
        full_text = " ".join(context.args)
        if "|" in full_text:
            parts = full_text.split("|", 1)
            project_name = parts[0].strip()
            task_name = parts[1].strip()
        else:
            await update.message.reply_text(
                "❌ Неправильный формат. Используйте: `/weeek_task [проект] | [задача]`",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_text(f"⏳ Создаю задачу '{task_name}' в проекте '{project_name}'...")
        
        # Получаем список проектов для поиска ID
        projects = await get_projects()
        project_id = None
        for project in projects:
            if project_name.lower() in project.get("name", "").lower():
                project_id = project.get("id")
                break
        
        if not project_id:
            await update.message.reply_text(
                f"❌ Проект '{project_name}' не найден в WEEEK.\n"
                f"Используйте `/weeek_projects` для просмотра списка проектов.",
                parse_mode='Markdown'
            )
            return
        
        task = await create_task(
            project_id=project_id,
            title=task_name,
            description=f"Создано через Telegram бот"
        )
        
        if task:
            await update.message.reply_text(
                f"✅ *Задача создана в WEEEK!*\n\n"
                f"Проект: {project_name}\n"
                f"Задача: {task_name}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Не удалось создать задачу в WEEEK")
    except Exception as e:
        log.error(f"❌ Ошибка создания задачи в Weeek: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def weeek_projects_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weeek_projects - список проектов в Weeek"""
    try:
        from weeek_helper import get_projects
        
        await update.message.reply_text("⏳ Получаю список проектов из WEEEK...")
        
        projects = await get_projects()
        
        if projects:
            text = f"📋 *Проекты в WEEEK* (всего: {len(projects)})\n\n"
            for i, project in enumerate(projects[:20], 1):
                name = project.get("name", "Без названия")
                status = project.get("status", "Не указан")
                text += f"{i}. *{name}*\n"
                text += f"   Статус: {status}\n\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Проектов не найдено или WEEEK недоступен")
    except Exception as e:
        log.error(f"❌ Ошибка получения проектов: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def email_check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /email_check - проверка новых писем"""
    try:
        from email_helper import check_new_emails
        
        await update.message.reply_text("⏳ Проверяю новые письма...")
        
        emails = await check_new_emails(since_days=1, limit=5)
        
        if emails:
            text = f"📧 *Новые письма* (последние {len(emails)})\n\n"
            for i, email_data in enumerate(emails, 1):
                from_addr = email_data.get("from", "Неизвестно")
                subject = email_data.get("subject", "Без темы")
                date = email_data.get("date", "")
                text += f"{i}. *От:* {from_addr}\n"
                text += f"   *Тема:* {subject}\n"
                text += f"   *Дата:* {date}\n\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text("📧 Новых писем нет или email недоступен")
    except Exception as e:
        log.error(f"❌ Ошибка проверки email: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def email_draft_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /email_draft - подготовка ответа на письмо"""
    request_text = " ".join(context.args) if context.args else ""
    
    if not request_text:
        await update.message.reply_text(
            "❌ Укажите тему письма или запрос клиента.\n"
            "Использование: `/email_draft [текст запроса]`\n\n"
            "Пример: `/email_draft нужна помощь с подбором персонала`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from lead_processor import generate_proposal
        
        await update.message.reply_text("⏳ Готовлю черновик ответа на письмо...")
        
        # Генерируем ответ используя generate_proposal
        draft = await generate_proposal(request_text, lead_contact={})
        
        text = f"📧 *Черновик ответа на письмо:*\n\n{draft}\n\n"
        text += "💡 Отредактируйте черновик и отправьте через WEEEK или почтовый клиент."
        
        # Разбиваем длинное сообщение если нужно
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        log.error(f"❌ Ошибка подготовки черновика: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def hypothesis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /hypothesis - генерация гипотез для проекта"""
    project_context = " ".join(context.args) if context.args else ""
    
    if not project_context:
        await update.message.reply_text(
            "❌ Укажите контекст проекта.\n"
            "Использование: `/hypothesis [описание проекта/задачи]`\n\n"
            "Пример: `/hypothesis автоматизация HR процессов в IT компании`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from lead_processor import generate_hypothesis
        
        await update.message.reply_text("⏳ Генерирую гипотезы...")
        
        hypothesis = await generate_hypothesis(project_context)
        
        text = f"💡 *Гипотезы для проекта:*\n\n{hypothesis}"
        
        # Разбиваем длинное сообщение если нужно
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        log.error(f"❌ Ошибка генерации гипотез: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /report - генерация отчёта по проекту"""
    project_name = " ".join(context.args) if context.args else ""
    
    if not project_name:
        await update.message.reply_text(
            "❌ Укажите название проекта.\n"
            "Использование: `/report [название проекта]`\n\n"
            "Пример: `/report Подбор HR-менеджера`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from summary_helper import generate_project_report
        
        await update.message.reply_text(f"⏳ Генерирую отчёт по проекту '{project_name}'...")
        
        # Получаем информацию о проекте из WEEEK
        from weeek_helper import get_projects
        projects = await get_projects()
        project_data = None
        for project in projects:
            if project_name.lower() in project.get("name", "").lower():
                project_data = project
                break
        
        if not project_data:
            await update.message.reply_text(f"❌ Проект '{project_name}' не найден в WEEEK")
            return
        
        # Пример данных для отчета (в будущем можно получать из WEEEK)
        conversations = [{"role": "user", "content": f"Работа над проектом {project_name}"}]
        
        report = await generate_project_report(conversations, project_name=project_name)
        
        text = f"📊 *Отчёт по проекту '{project_name}':*\n\n{report}"
        
        # Разбиваем длинное сообщение если нужно
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        log.error(f"❌ Ошибка генерации отчёта: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def upload_document_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /upload - инструкция по загрузке документов"""
    await update.message.reply_text(
        "📤 *Загрузка документов в базу знаний*\n\n"
        "Отправьте мне документ в одном из форматов:\n"
        "• PDF (.pdf)\n"
        "• Word (.docx, .doc)\n"
        "• Excel (.xlsx, .xls)\n"
        "• Текст (.txt)\n\n"
        "Документ будет автоматически обработан и загружен в Qdrant Cloud.\n"
        "После загрузки вы сможете задавать вопросы по этому документу.\n\n"
        "💡 *Совет:* Дайте документу понятное имя файла для удобства поиска.",
        parse_mode='Markdown'
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки документов через Telegram"""
    try:
        document = update.message.document
        user_id = update.message.from_user.id
        username = update.message.from_user.username or "unknown"
        
        # Проверяем размер файла (макс 20MB)
        if document.file_size > 20 * 1024 * 1024:
            await update.message.reply_text(
                "❌ Файл слишком большой. Максимальный размер: 20 МБ"
            )
            return
        
        file_name = document.file_name
        file_extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
        
        # Проверяем формат файла
        supported_formats = ['pdf', 'docx', 'doc', 'xlsx', 'xls', 'txt']
        if file_extension not in supported_formats:
            await update.message.reply_text(
                f"❌ Формат `.{file_extension}` не поддерживается.\n\n"
                f"Поддерживаемые форматы: {', '.join(supported_formats)}",
                parse_mode='Markdown'
            )
            return
        
        log.info(f"📤 Получен документ от пользователя {username} (ID: {user_id}): {file_name}")
        
        # Отправляем статус
        status_msg = await update.message.reply_text(
            f"⏳ Загружаю документ `{file_name}`...\n"
            f"Размер: {document.file_size / 1024:.1f} КБ",
            parse_mode='Markdown'
        )
        
        # Скачиваем файл
        file = await context.bot.get_file(document.file_id)
        
        # Создаем временную директорию если не существует
        import tempfile
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file_name)
        
        await file.download_to_drive(file_path)
        log.info(f"✅ Файл скачан: {file_path}")
        
        # Обновляем статус
        await status_msg.edit_text(
            f"⏳ Обрабатываю документ `{file_name}`...\n"
            f"Извлекаю текст и создаю чанки...",
            parse_mode='Markdown'
        )
        
        # Обрабатываем документ
        text_content = await extract_text_from_file(file_path, file_extension)
        
        if not text_content or len(text_content.strip()) < 50:
            await status_msg.edit_text(
                f"❌ Не удалось извлечь текст из документа `{file_name}`.\n"
                f"Проверьте, что документ содержит текст.",
                parse_mode='Markdown'
            )
            # Удаляем временный файл
            try:
                os.remove(file_path)
                os.rmdir(temp_dir)
            except:
                pass
            return
        
        log.info(f"✅ Извлечено {len(text_content)} символов из {file_name}")
        
        # Загружаем в Qdrant
        await status_msg.edit_text(
            f"⏳ Загружаю в базу знаний...\n"
            f"Индексирую чанки в Qdrant Cloud...",
            parse_mode='Markdown'
        )
        
        result = await upload_to_qdrant(
            text_content=text_content,
            file_name=file_name,
            user_id=user_id,
            username=username
        )
        
        # Удаляем временный файл
        try:
            os.remove(file_path)
            os.rmdir(temp_dir)
        except Exception as e:
            log.warning(f"⚠️ Не удалось удалить временный файл: {e}")
        
        if result['success']:
            await status_msg.edit_text(
                f"✅ *Документ загружен в базу знаний!*\n\n"
                f"📄 Файл: `{file_name}`\n"
                f"📊 Создано чанков: {result['chunks_count']}\n"
                f"🆔 ID документа: `{result['doc_id']}`\n\n"
                f"Теперь вы можете задавать вопросы по этому документу:\n"
                f"• Просто напишите вопрос в чате\n"
                f"• Или используйте `/rag_search [запрос]`",
                parse_mode='Markdown'
            )
            log.info(f"✅ Документ {file_name} успешно загружен (ID: {result['doc_id']})")
        else:
            await status_msg.edit_text(
                f"❌ Ошибка загрузки документа:\n{result['error']}",
                parse_mode='Markdown'
            )
            log.error(f"❌ Ошибка загрузки {file_name}: {result['error']}")
            
    except Exception as e:
        log.error(f"❌ Ошибка обработки документа: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке документа:\n{str(e)}"
        )

async def extract_text_from_file(file_path: str, file_extension: str) -> str:
    """Извлечение текста из различных форматов файлов"""
    try:
        if file_extension == 'pdf':
            # PDF
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n\n"
            return text
        
        elif file_extension in ['docx', 'doc']:
            # Word документы
            try:
                import docx
                doc = docx.Document(file_path)
                text = "\n\n".join([para.text for para in doc.paragraphs])
                return text
            except ImportError:
                log.error("❌ python-docx не установлен. Установите: pip install python-docx")
                return ""
        
        elif file_extension in ['xlsx', 'xls']:
            # Excel
            import pandas as pd
            df = pd.read_excel(file_path, sheet_name=None)  # Читаем все листы
            text = ""
            for sheet_name, sheet_df in df.items():
                text += f"=== Лист: {sheet_name} ===\n\n"
                text += sheet_df.to_string(index=False) + "\n\n"
            return text
        
        elif file_extension == 'txt':
            # Текстовый файл
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        else:
            return ""
    
    except Exception as e:
        log.error(f"❌ Ошибка извлечения текста из {file_path}: {e}")
        return ""

async def upload_to_qdrant(text_content: str, file_name: str, user_id: int, username: str) -> dict:
    """Загрузка документа в Qdrant с чанкингом"""
    try:
        from qdrant_loader import QdrantLoader
        from qdrant_helper import get_embedding
        import uuid
        
        # Создаем уникальный ID для документа
        doc_id = str(uuid.uuid4())
        
        # Инициализируем QdrantLoader
        loader = QdrantLoader()
        
        # Разбиваем текст на чанки
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            from text_splitter import RecursiveCharacterTextSplitter
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = text_splitter.split_text(text_content)
        log.info(f"📄 Создано {len(chunks)} чанков из документа {file_name}")
        
        # Создаем документы для загрузки
        documents = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 10:  # Пропускаем очень короткие чанки
                continue
            
            doc = {
                "id": f"{doc_id}_chunk_{i}",
                "text": chunk,
                "metadata": {
                    "source": file_name,
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "uploaded_by": username,
                    "user_id": user_id,
                    "category": "user_upload",
                    "title": file_name
                }
            }
            documents.append(doc)
        
        # Загружаем в Qdrant через loader
        points = []
        for doc in documents:
            # Получаем эмбеддинг для чанка
            embedding = await get_embedding(doc["text"])
            if embedding is None:
                log.warning(f"⚠️ Не удалось получить эмбеддинг для чанка {doc['id']}")
                continue
            
            from qdrant_client.models import PointStruct
            point = PointStruct(
                id=doc["id"],
                vector=embedding,
                payload={
                    "text": doc["text"],
                    "source": doc["metadata"]["source"],
                    "doc_id": doc["metadata"]["doc_id"],
                    "chunk_index": doc["metadata"]["chunk_index"],
                    "uploaded_by": doc["metadata"]["uploaded_by"],
                    "user_id": doc["metadata"]["user_id"],
                    "category": doc["metadata"]["category"],
                    "title": doc["metadata"]["title"]
                }
            )
            points.append(point)
        
        # Загружаем в Qdrant
        if points:
            loader.client.upsert(
                collection_name=loader.collection_name,
                points=points
            )
            log.info(f"✅ Загружено {len(points)} чанков в Qdrant")
            
            return {
                "success": True,
                "chunks_count": len(points),
                "doc_id": doc_id
            }
        else:
            return {
                "success": False,
                "error": "Не удалось создать эмбеддинги для документа"
            }
    
    except Exception as e:
        log.error(f"❌ Ошибка загрузки в Qdrant: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }

# ===================== RUN BOT ========================
def main():
    # Проверяем доступность Qdrant библиотек еще раз при старте
    try:
        import qdrant_client
        log.info("✅ Qdrant библиотеки доступны: qdrant-client")
    except ImportError as e:
        log.warning(f"⚠️ Qdrant библиотеки не установлены: {e}")
        log.warning("⚠️ Для работы векторного поиска установите: pip install qdrant-client")
    
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
    
    # Start Telegram bot с поддержкой concurrent updates для масштабирования
    # concurrent_updates=True позволяет обрабатывать до 100+ одновременных пользователей
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).concurrent_updates(True).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    
    # New commands for demonstration
    app.add_handler(CommandHandler("rag_search", rag_search_command))
    app.add_handler(CommandHandler("rag_stats", rag_stats_command))
    app.add_handler(CommandHandler("rag_docs", rag_docs_command))
    app.add_handler(CommandHandler("demo_proposal", demo_proposal_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("status", status_command))
    
    # WEEEK commands
    app.add_handler(CommandHandler("weeek_task", weeek_create_task_command))
    app.add_handler(CommandHandler("weeek_projects", weeek_projects_command))
    
    # Email commands
    app.add_handler(CommandHandler("email_check", email_check_command))
    app.add_handler(CommandHandler("email_draft", email_draft_command))
    
    # Additional commands
    app.add_handler(CommandHandler("hypothesis", hypothesis_command))
    app.add_handler(CommandHandler("report", report_command))
    
    # Document upload command and handler
    app.add_handler(CommandHandler("upload", upload_document_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Callback query handler for inline buttons
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handler for AI chat (должен быть последним!)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    
    # Запуск бота: webhook для production (Railway) или polling для локальной разработки
    async def start_bot():
        """Асинхронный запуск бота с webhook или polling"""
        if USE_WEBHOOK and WEBHOOK_URL:
            # Используем webhook для production (лучше для масштабирования)
            webhook_path = f"/webhook/{TELEGRAM_BOT_TOKEN}"
            full_webhook_url = f"{WEBHOOK_URL.rstrip('/')}{webhook_path}"
            
            log.info(f"🌐 Настройка webhook: {full_webhook_url}")
            log.info(f"🔌 Порт: {PORT}")
            
            # Инициализируем и запускаем приложение
            # Проверяем, что приложение еще не запущено
            if not app.running:
                await app.initialize()
                await app.start()
            else:
                log.warning("⚠️ Приложение уже запущено, пропускаем повторный запуск")
            
            # Устанавливаем webhook
            await app.bot.set_webhook(
                url=full_webhook_url,
                drop_pending_updates=True,
                max_connections=100  # Максимум одновременных соединений для обработки обновлений
            )
            
            log.info(f"✅ Webhook установлен: {full_webhook_url}")
            
            # Запускаем фоновые задачи мониторинга (после инициализации бота)
            try:
                from integrate_scenarios import start_background_tasks
                start_background_tasks(
                    telegram_bot=app.bot,
                    enable_hrtime=True,
                    enable_email=True,
                    enable_deadlines=True
                )
                log.info("✅ Фоновые задачи мониторинга запущены")
            except Exception as e:
                log.warning(f"⚠️ Не удалось запустить фоновые задачи: {e}")
            
            # Запускаем HTTP сервер для приема webhook запросов
            await app.updater.start_webhook(
                listen="0.0.0.0",
                port=PORT,
                webhook_url=full_webhook_url,
                url_path=webhook_path
            )
            
            log.info(f"✅ Бот запущен с webhook на порту {PORT}")
            log.info(f"📡 Webhook URL: {full_webhook_url}")
            log.info("🚀 Готов к обработке обновлений от Telegram (concurrent_updates=True)")
            
            # Держим бота запущенным (бесконечное ожидание)
            try:
                await asyncio.Event().wait()
            except (asyncio.CancelledError, KeyboardInterrupt):
                log.info("⏹️  Получен сигнал остановки...")
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
        else:
            # Используем polling для локальной разработки
            log.info("🔄 Используем polling (локальная разработка)")
            
            # Инициализируем и запускаем приложение
            # Проверяем, что приложение еще не запущено
            if not app.running:
                await app.initialize()
                await app.start()
            else:
                log.warning("⚠️ Приложение уже запущено, пропускаем повторный запуск")
            
            # Запускаем фоновые задачи мониторинга (после инициализации бота)
            try:
                from integrate_scenarios import start_background_tasks
                start_background_tasks(
                    telegram_bot=app.bot,
                    enable_hrtime=True,
                    enable_email=True,
                    enable_deadlines=True
                )
                log.info("✅ Фоновые задачи мониторинга запущены")
            except Exception as e:
                log.warning(f"⚠️ Не удалось запустить фоновые задачи: {e}")
            log.info("💡 Для production установите USE_WEBHOOK=true и WEBHOOK_URL")
            
            # Удаляем webhook если он был установлен ранее
            try:
                webhook_info = await app.bot.get_webhook_info()
                if webhook_info.url:
                    log.warning(f"⚠️ Обнаружен webhook: {webhook_info.url}. Удаляем для polling...")
                    await app.bot.delete_webhook(drop_pending_updates=True)
                    log.info("✅ Webhook удален")
            except Exception as e:
                log.error(f"❌ Ошибка проверки webhook: {e}")
            
            # Запускаем polling (приложение уже инициализировано и запущено выше)
            await app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            log.info("✅ Бот запущен с polling (concurrent_updates=True)")
            log.info("🚀 Готов к обработке обновлений от Telegram")
            
            # Держим бота запущенным
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                pass
    
    # Запускаем бота
    log.info("🚀 Запуск Telegram Bot...")
    log.info(f"⚙️  Режим: {'WEBHOOK' if USE_WEBHOOK and WEBHOOK_URL else 'POLLING'}")
    log.info(f"🔄 Concurrent updates: ВКЛЮЧЕН (поддержка 100+ одновременных пользователей)")
    
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        log.info("⏹️  Остановка бота по запросу пользователя...")
    except RuntimeError as e:
        if "already running" in str(e).lower():
            log.warning("⚠️ Приложение уже запущено, возможно перезапуск контейнера")
            # Ждем завершения существующего процесса
            import time
            time.sleep(5)
        else:
            raise
    except Exception as e:
        log.error(f"❌ Критическая ошибка при запуске бота: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    main()
