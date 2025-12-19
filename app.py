# bot.py
import os
import re
import time
import json
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
- НИКОГДА не используй Markdown форматирование (звездочки **, подчеркивания __ и т.д.) - пиши обычным текстом

КРИТИЧЕСКИ ВАЖНО - ПРАВИЛА ПРЕДЛОЖЕНИЯ УСЛУГ:
- ✅ Предлагай ТОЛЬКО Анастасию Новосёлову как консультанта/тренера/специалиста
- ❌ НИКОГДА не предлагай других тренеров, консультантов или специалистов
- ❌ НИКОГДА не говори "подберу тренера", "найду консультанта", "подберу специалиста"
- ❌ НИКОГДА не предлагай альтернативных вариантов или других людей
- ✅ Если спрашивают про тренера/консультанта, отвечай: "Я могу предложить услуги Анастасии Новосёловой"
- ✅ Всегда представляйся при приветствии: "Здравствуйте! Я AI-ассистент Анастасии Новосёловой. Чем могу помочь?"
- ✅ Вежливо прощайся при прощании: "До свидания! Буду рад помочь снова"

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

Ответь по делу, используя информацию из базы знаний. НЕ используй Markdown форматирование!
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
UserWeeekWorkspace: Dict[int, str] = {}  # WEEEK Workspace ID для каждого пользователя

# ===================== EMAIL MONITORING =====================
# ID администраторов для уведомлений о новых письмах (можно указать несколько через запятую)
ADMIN_USER_IDS_STR = os.getenv("TELEGRAM_ADMIN_IDS", os.getenv("TELEGRAM_ADMIN_ID", "5305427956"))
# Парсим список ID администраторов
ADMIN_USER_IDS = [int(uid.strip()) for uid in ADMIN_USER_IDS_STR.split(",") if uid.strip().isdigit()]
# Для обратной совместимости оставляем ADMIN_USER_ID (первый из списка)
ADMIN_USER_ID = ADMIN_USER_IDS[0] if ADMIN_USER_IDS else 5305427956
# Хранилище обработанных email ID (чтобы не дублировать уведомления)
processed_email_ids: set = set()
email_check_interval = int(os.getenv("EMAIL_CHECK_INTERVAL", "10"))  # 10 секунд по умолчанию
# Хранилище состояния ответа на email для каждого пользователя
email_reply_state: Dict[int, Dict] = {}  # {user_id: {'email_id': ..., 'to': ..., 'subject': ...}}

# ===================== EMAIL SUBSCRIBERS =====================
# Файл для хранения подписчиков на уведомления о почте
EMAIL_SUBSCRIBERS_FILE = "email_subscribers.json"

def load_email_subscribers() -> set:
    """Загрузить список подписчиков из файла"""
    try:
        if os.path.exists(EMAIL_SUBSCRIBERS_FILE):
            with open(EMAIL_SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('subscribers', []))
    except Exception as e:
        log.warning(f"⚠️ Ошибка загрузки подписчиков: {e}")
    return set()

def save_email_subscribers(subscribers: set):
    """Сохранить список подписчиков в файл"""
    try:
        data = {'subscribers': list(subscribers)}
        with open(EMAIL_SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.error(f"❌ Ошибка сохранения подписчиков: {e}")

def add_email_subscriber(user_id: int):
    """Добавить пользователя в список подписчиков"""
    subscribers = load_email_subscribers()
    subscribers.add(user_id)
    save_email_subscribers(subscribers)
    log.info(f"✅ Пользователь {user_id} подписан на уведомления о почте")

def remove_email_subscriber(user_id: int):
    """Удалить пользователя из списка подписчиков"""
    subscribers = load_email_subscribers()
    subscribers.discard(user_id)
    save_email_subscribers(subscribers)
    log.info(f"❌ Пользователь {user_id} отписан от уведомлений о почте")

def get_email_subscribers() -> set:
    """Получить список всех подписчиков"""
    subscribers = load_email_subscribers()
    # Всегда добавляем администраторов
    subscribers.update(ADMIN_USER_IDS)
    return subscribers

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
    
    # Автоматически подписываем пользователя на уведомления о почте
    add_email_subscriber(user_id)
    
    keyboard = [
        [InlineKeyboardButton("📚 База знаний", callback_data="menu_knowledge_base")],
        [InlineKeyboardButton("📋 Проекты", callback_data="menu_projects")],
        [InlineKeyboardButton("🛠 Инструменты", callback_data="menu_tools")],
        [InlineKeyboardButton("📧 Ответить на последний мейл", callback_data="email_reply_last")],
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
        "• 📋 Управлять проектами и задачами\n"
        "• 📧 Отвечать на последний мейл\n\n"
        "Выберите раздел:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 База знаний", callback_data="menu_knowledge_base")],
        [InlineKeyboardButton("📋 Проекты", callback_data="menu_projects")],
        [InlineKeyboardButton("🛠 Инструменты", callback_data="menu_tools")],
        [InlineKeyboardButton("📧 Ответить на последний мейл", callback_data="email_reply_last")],
        [InlineKeyboardButton("💬 Чат с AI", callback_data="chat")],
        [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🏠 *Главное меню*\n\n"
        "📚 *База знаний* - поиск, документы, статистика\n"
        "📋 *Проекты* - управление проектами и задачами\n"
        "🛠 *Инструменты* - генерация КП, суммаризация\n"
        "📧 *Ответить на последний мейл* - быстрый ответ на последнее письмо\n"
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
            [InlineKeyboardButton("📋 Мои проекты", callback_data="weeek_list_projects")],
            [InlineKeyboardButton("➕ Создать задачу", callback_data="weeek_create_task_menu")],
            [InlineKeyboardButton("📊 Статус проектов", callback_data="status")],
            [InlineKeyboardButton("📝 Суммаризация", callback_data="summary_menu")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "📋 *Управление проектами (WEEEK)*\n\n"
            "📋 *Мои проекты* - список всех проектов\n"
            "➕ *Создать задачу* - добавить задачу в проект\n"
            "📊 *Статус* - задачи с ближайшими дедлайнами\n"
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
    
    # Обработчики WEEEK
    elif query.data == "weeek_list_projects":
        await show_weeek_projects(query)
        return
    
    elif query.data == "weeek_create_task_menu":
        await show_weeek_create_task_menu(query)
        return
    
    elif query.data.startswith("weeek_select_project_"):
        project_id = query.data.replace("weeek_select_project_", "")
        context.user_data["selected_project_id"] = project_id
        await query.edit_message_text(
            "✅ Проект выбран!\n\n"
            "Теперь отправьте название задачи (текстовым сообщением).\n\n"
            "Например: `Согласовать КП с клиентом`",
            parse_mode='Markdown'
        )
        context.user_data["waiting_for_task_name"] = True
        return
    
    elif query.data.startswith("weeek_view_project_"):
        await show_weeek_project_details(query, context)
        return
    
    elif query.data.startswith("weeek_update_select_project_"):
        await show_weeek_tasks_for_update(query, context)
        return
    
    elif query.data.startswith("weeek_edit_task_"):
        await show_weeek_task_edit_menu(query, context)
        return
    
    elif query.data.startswith("weeek_edit_field_"):
        await handle_weeek_edit_field(query, context)
        return
    
    elif query.data.startswith("weeek_complete_"):
        await handle_weeek_complete_task(query, context)
        return
    
    elif query.data.startswith("weeek_delete_"):
        await handle_weeek_delete_task(query, context)
        return
    
    elif query.data.startswith("weeek_set_priority_"):
        await handle_weeek_set_priority(query, context)
        return
    
    elif query.data.startswith("weeek_set_type_"):
        await handle_weeek_set_type(query, context)
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
            "`/weeek_info` - workspace info + список проектов с ID\n"
            "`/weeek_projects` - список проектов\n"
            "`/weeek_create_project [название]` - создать проект\n"
            "`/weeek_tasks [id] [фильтры]` - задачи проекта\n"
            "   Фильтры: all, completed, active, high, low\n"
            "`/weeek_task [проект] | [задача]` - создать задачу\n"
            "`/weeek_update` - обновить задачу (интерактивно)\n"
            "`/status` - статус проектов\n\n"
            "**Яндекс.Диск:**\n"
            "`/yadisk_list [путь]` - список файлов\n"
            "`/yadisk_search [запрос]` - поиск файлов\n"
            "`/yadisk_recent` - последние файлы\n\n"
            "**Email:**\n"
            "`/email_check` - проверить новые письма\n"
            "`/email_draft [текст]` - черновик ответа\n\n"
            "**Генерация:**\n"
            "`/demo_proposal [запрос]` - КП\n"
            "`/hypothesis [описание]` - гипотезы\n"
            "`/report [проект]` - отчет по проекту\n"
            "`/summary [проект]` - суммаризация проекта\n"
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
    
    # Обработчики для действий с письмами
    elif query.data == "email_reply_last":
        # Обработка кнопки "Ответить на последний мейл"
        await handle_email_reply_last(query)
    elif query.data.startswith("email_reply_"):
        email_id = query.data.replace("email_reply_", "")
        await handle_email_reply(query, email_id)
    elif query.data.startswith("email_proposal_"):
        email_id = query.data.replace("email_proposal_", "")
        await handle_email_proposal(query, email_id)
    elif query.data.startswith("email_task_"):
        email_id = query.data.replace("email_task_", "")
        await handle_email_task(query, email_id)
    elif query.data.startswith("email_done_"):
        email_id = query.data.replace("email_done_", "")
        await handle_email_done(query, email_id)
    elif query.data.startswith("email_full_"):
        email_id = query.data.replace("email_full_", "")
        await handle_email_full(query, email_id)
    elif query.data.startswith("email_send_reply_"):
        email_id = query.data.replace("email_send_reply_", "")
        await handle_email_send_reply(query, email_id)
    elif query.data.startswith("email_task_create_"):
        # Формат: email_task_create_{email_id}_{project_id}
        parts = query.data.replace("email_task_create_", "").split("_", 1)
        if len(parts) == 2:
            email_id = parts[0]
            project_id = int(parts[1])
            await handle_email_create_task(query, email_id, project_id)
    elif query.data.startswith("email_cancel_"):
        email_id = query.data.replace("email_cancel_", "")
        await handle_email_cancel(query, email_id)

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

async def show_weeek_projects(query: CallbackQuery):
    """Показать список проектов из WEEEK"""
    try:
        from weeek_helper import get_projects

        await query.edit_message_text("⏳ Загружаю проекты из WEEEK...")

        projects = await get_projects()

        if not projects:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
            await query.edit_message_text(
                "❌ Проектов не найдено или WEEEK недоступен.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        keyboard = []
        for project in projects[:10]:  # Показываем первые 10
            project_title = project.get("title", "Без названия")
            project_id = project.get("id", "")
            keyboard.append([
                InlineKeyboardButton(
                    f"📁 {project_title}",
                    callback_data=f"weeek_view_project_{project_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")])
        
        text = f"📋 *Проекты в WEEEK* (всего: {len(projects)})\n\n"
        text += "Выберите проект для просмотра:"
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        log.error(f"❌ Ошибка получения проектов: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
        await query.edit_message_text(
            f"❌ Ошибка загрузки проектов: {str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def show_weeek_create_task_menu(query: CallbackQuery):
    """Показать меню создания задачи"""
    try:
        from weeek_helper import get_projects

        await query.edit_message_text("⏳ Загружаю проекты...")

        projects = await get_projects()

        if not projects:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
            await query.edit_message_text(
                "❌ Проектов не найдено.\n\n"
                "Сначала создайте проект в WEEEK.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        keyboard = []
        for project in projects[:15]:  # Показываем до 15 проектов
            project_title = project.get("title", "Без названия")
            project_id = project.get("id", "")
            keyboard.append([
                InlineKeyboardButton(
                    f"➕ {project_title}",
                    callback_data=f"weeek_select_project_{project_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")])
        
        await query.edit_message_text(
            "➕ *Создание задачи*\n\n"
            "Выберите проект, в который хотите добавить задачу:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]
        await query.edit_message_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def show_weeek_project_details(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Показать детали проекта"""
    try:
        project_id = query.data.replace("weeek_view_project_", "")
        
        from weeek_helper import get_project
        
        await query.edit_message_text("⏳ Загружаю информацию о проекте...")
        
        project = await get_project(project_id)
        
        if not project:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="weeek_list_projects")]]
            await query.edit_message_text(
                "❌ Не удалось загрузить информацию о проекте",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        project_name = project.get("name", "Без названия")
        project_status = project.get("status", "Не указан")
        project_desc = project.get("description", "Описание отсутствует")
        
        text = f"📁 *{project_name}*\n\n"
        text += f"Статус: {project_status}\n"
        text += f"Описание: {project_desc}\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Создать задачу", callback_data=f"weeek_select_project_{project_id}")],
            [InlineKeyboardButton("🔙 К списку проектов", callback_data="weeek_list_projects")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="weeek_list_projects")]]
        await query.edit_message_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def show_weeek_tasks_for_update(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Показать список задач проекта для обновления"""
    try:
        project_id = query.data.replace("weeek_update_select_project_", "")
        
        from weeek_helper import get_tasks, get_project
        
        await query.edit_message_text("⏳ Загружаю задачи...")
        
        # Получаем информацию о проекте
        project = await get_project(project_id)
        project_name = project.get("name", f"Проект {project_id}") if project else f"Проект {project_id}"
        
        # Получаем задачи
        result = await get_tasks(project_id=int(project_id), completed=False, per_page=15)
        
        if not result["success"] or not result["tasks"]:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            await query.edit_message_text(
                f"📁 *{project_name}*\n\n"
                "❌ Активных задач не найдено.\n\n"
                "Сначала создайте задачи в этом проекте.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Показываем список задач
        keyboard = []
        for task in result["tasks"]:
            title = task.get("title", "Без названия")
            task_id = task.get("id", "")
            priority = task.get("priority", 0)
            priority_emoji = ["🟢", "🟡", "🔴", "⏸"][priority]
            
            # Обрезаем длинные названия
            display_title = title[:40] + "..." if len(title) > 40 else title
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{priority_emoji} {display_title}",
                    callback_data=f"weeek_edit_task_{task_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        
        await query.edit_message_text(
            f"🔄 *Обновление задачи*\n\n"
            f"Проект: *{project_name}*\n"
            f"Шаг 2/3: Выберите задачу для редактирования:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        import traceback
        log.error(traceback.format_exc())
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        await query.edit_message_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def show_weeek_task_edit_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню редактирования задачи"""
    try:
        task_id = query.data.replace("weeek_edit_task_", "")
        
        from weeek_helper import get_task
        
        await query.edit_message_text("⏳ Загружаю задачу...")
        
        task = await get_task(task_id)
        
        if not task:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            await query.edit_message_text(
                "❌ Не удалось загрузить задачу",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Сохраняем task_id в контексте
        context.user_data["editing_task_id"] = task_id
        
        title = task.get("title", "Без названия")
        description = task.get("description", "Нет описания")
        priority = task.get("priority", 0)
        priority_names = ["🟢 Низкий", "🟡 Средний", "🔴 Высокий", "⏸ В ожидании"]
        priority_str = priority_names[priority] if 0 <= priority <= 3 else "Не указан"
        task_type = task.get("type", "action")
        type_names = {"action": "📋 Задача", "meet": "👥 Встреча", "call": "📞 Звонок"}
        type_str = type_names.get(task_type, "Задача")
        completed = task.get("completed", False)
        status_str = "✅ Завершена" if completed else "🔄 Активна"
        
        text = f"✏️ *Редактирование задачи*\n\n"
        text += f"📝 *Название:* {title}\n\n"
        text += f"📄 *Описание:*\n{description}\n\n"
        text += f"🎯 *Приоритет:* {priority_str}\n"
        text += f"🏷 *Тип:* {type_str}\n"
        text += f"📊 *Статус:* {status_str}\n\n"
        text += f"ID: `{task_id}`"
        
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить название", callback_data=f"weeek_edit_field_title_{task_id}")],
            [InlineKeyboardButton("📝 Изменить описание", callback_data=f"weeek_edit_field_description_{task_id}")],
            [InlineKeyboardButton("🎯 Изменить приоритет", callback_data=f"weeek_edit_field_priority_{task_id}")],
            [InlineKeyboardButton("🏷 Изменить тип", callback_data=f"weeek_edit_field_type_{task_id}")],
        ]
        
        if not completed:
            keyboard.append([InlineKeyboardButton("✅ Отметить выполненной", callback_data=f"weeek_complete_{task_id}")])
        else:
            keyboard.append([InlineKeyboardButton("🔄 Возобновить", callback_data=f"weeek_uncomplete_{task_id}")])
        
        keyboard.extend([
            [InlineKeyboardButton("🗑 Удалить задачу", callback_data=f"weeek_delete_{task_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ])
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        import traceback
        log.error(traceback.format_exc())
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        await query.edit_message_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_weeek_edit_field(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Обработать выбор поля для редактирования"""
    try:
        # Формат: weeek_edit_field_{field}_{task_id}
        parts = query.data.replace("weeek_edit_field_", "").split("_", 1)
        field = parts[0]
        task_id = parts[1]
        
        context.user_data["editing_task_id"] = task_id
        context.user_data["editing_field"] = field
        
        if field == "title":
            await query.edit_message_text(
                "✏️ *Изменение названия задачи*\n\n"
                "Отправьте новое название задачи текстовым сообщением.",
                parse_mode='Markdown'
            )
            context.user_data["waiting_for_task_update"] = "title"
            
        elif field == "description":
            await query.edit_message_text(
                "📝 *Изменение описания задачи*\n\n"
                "Отправьте новое описание задачи текстовым сообщением.",
                parse_mode='Markdown'
            )
            context.user_data["waiting_for_task_update"] = "description"
            
        elif field == "priority":
            keyboard = [
                [InlineKeyboardButton("🟢 Низкий (Low)", callback_data=f"weeek_set_priority_0_{task_id}")],
                [InlineKeyboardButton("🟡 Средний (Medium)", callback_data=f"weeek_set_priority_1_{task_id}")],
                [InlineKeyboardButton("🔴 Высокий (High)", callback_data=f"weeek_set_priority_2_{task_id}")],
                [InlineKeyboardButton("⏸ В ожидании (Hold)", callback_data=f"weeek_set_priority_3_{task_id}")],
                [InlineKeyboardButton("🔙 Отмена", callback_data=f"weeek_edit_task_{task_id}")]
            ]
            await query.edit_message_text(
                "🎯 *Выберите новый приоритет:*",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif field == "type":
            keyboard = [
                [InlineKeyboardButton("📋 Задача (action)", callback_data=f"weeek_set_type_action_{task_id}")],
                [InlineKeyboardButton("👥 Встреча (meet)", callback_data=f"weeek_set_type_meet_{task_id}")],
                [InlineKeyboardButton("📞 Звонок (call)", callback_data=f"weeek_set_type_call_{task_id}")],
                [InlineKeyboardButton("🔙 Отмена", callback_data=f"weeek_edit_task_{task_id}")]
            ]
            await query.edit_message_text(
                "🏷 *Выберите новый тип:*",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")

async def handle_weeek_complete_task(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Отметить задачу как выполненную"""
    try:
        task_id = query.data.replace("weeek_complete_", "").replace("weeek_uncomplete_", "")
        
        from weeek_helper import complete_task, uncomplete_task
        
        await query.edit_message_text("⏳ Обновляю статус...")
        
        if "weeek_complete_" in query.data:
            success = await complete_task(task_id)
            message = "✅ Задача отмечена как выполненная!" if success else "❌ Ошибка при обновлении статуса"
        else:
            success = await uncomplete_task(task_id)
            message = "🔄 Задача возобновлена!" if success else "❌ Ошибка при обновлении статуса"
        
        keyboard = [[InlineKeyboardButton("🔙 К задаче", callback_data=f"weeek_edit_task_{task_id}")]]
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")

async def handle_weeek_delete_task(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Удалить задачу"""
    try:
        task_id = query.data.replace("weeek_delete_", "")
        
        # Подтверждение
        if not context.user_data.get("confirm_delete_task"):
            keyboard = [
                [InlineKeyboardButton("✅ Да, удалить", callback_data=f"weeek_delete_confirm_{task_id}")],
                [InlineKeyboardButton("❌ Отмена", callback_data=f"weeek_edit_task_{task_id}")]
            ]
            await query.edit_message_text(
                "⚠️ *Подтверждение удаления*\n\n"
                "Вы уверены, что хотите удалить эту задачу?",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data["confirm_delete_task"] = task_id
            return
        
        # Удаляем задачу
        from weeek_helper import delete_task
        
        await query.edit_message_text("⏳ Удаляю задачу...")
        
        success = await delete_task(task_id)
        
        if success:
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            await query.edit_message_text(
                "✅ Задача удалена!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [[InlineKeyboardButton("🔙 К задаче", callback_data=f"weeek_edit_task_{task_id}")]]
            await query.edit_message_text(
                "❌ Ошибка при удалении задачи",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        context.user_data["confirm_delete_task"] = None
        
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")

async def handle_weeek_set_priority(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Установить новый приоритет задачи"""
    try:
        # Формат: weeek_set_priority_{priority}_{task_id}
        parts = query.data.replace("weeek_set_priority_", "").split("_", 1)
        priority = int(parts[0])
        task_id = parts[1]
        
        from weeek_helper import update_task
        
        await query.edit_message_text("⏳ Обновляю приоритет...")
        
        updated_task = await update_task(task_id, priority=priority)
        
        if updated_task:
            priority_names = ["🟢 Низкий", "🟡 Средний", "🔴 Высокий", "⏸ В ожидании"]
            priority_str = priority_names[priority]
            
            keyboard = [[InlineKeyboardButton("🔙 К задаче", callback_data=f"weeek_edit_task_{task_id}")]]
            await query.edit_message_text(
                f"✅ Приоритет обновлен!\n\n"
                f"Новый приоритет: {priority_str}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [[InlineKeyboardButton("🔙 К задаче", callback_data=f"weeek_edit_task_{task_id}")]]
            await query.edit_message_text(
                "❌ Ошибка при обновлении приоритета",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")

async def handle_weeek_set_type(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Установить новый тип задачи"""
    try:
        # Формат: weeek_set_type_{type}_{task_id}
        parts = query.data.replace("weeek_set_type_", "").rsplit("_", 1)
        task_type = parts[0]
        task_id = parts[1]
        
        from weeek_helper import update_task
        
        await query.edit_message_text("⏳ Обновляю тип задачи...")
        
        updated_task = await update_task(task_id, task_type=task_type)
        
        if updated_task:
            type_names = {"action": "📋 Задача", "meet": "👥 Встреча", "call": "📞 Звонок"}
            type_str = type_names.get(task_type, task_type)
            
            keyboard = [[InlineKeyboardButton("🔙 К задаче", callback_data=f"weeek_edit_task_{task_id}")]]
            await query.edit_message_text(
                f"✅ Тип задачи обновлен!\n\n"
                f"Новый тип: {type_str}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [[InlineKeyboardButton("🔙 К задаче", callback_data=f"weeek_edit_task_{task_id}")]]
            await query.edit_message_text(
                "❌ Ошибка при обновлении типа",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")

async def show_main_menu(query: CallbackQuery):
    keyboard = [
        [InlineKeyboardButton("📚 База знаний", callback_data="menu_knowledge_base")],
        [InlineKeyboardButton("📋 Проекты", callback_data="menu_projects")],
        [InlineKeyboardButton("🛠 Инструменты", callback_data="menu_tools")],
        [InlineKeyboardButton("📧 Ответить на последний мейл", callback_data="email_reply_last")],
        [InlineKeyboardButton("💬 Чат с AI", callback_data="chat")],
        [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🏠 *Главное меню*\n\n"
        "📚 *База знаний* - поиск, документы, статистика\n"
        "📋 *Проекты* - управление проектами и задачами\n"
        "🛠 *Инструменты* - генерация КП, суммаризация\n"
        "📧 *Ответить на последний мейл* - быстрый ответ на последнее письмо\n"
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

def remove_markdown(text: str) -> str:
    """Удаляет Markdown форматирование из текста (более агрессивная версия)"""
    import re
    if not text:
        return text
    
    # Убираем множественные звездочки (***текст***, **текст**, *текст*)
    text = re.sub(r'\*{3,}([^*]+)\*{3,}', r'\1', text)  # ***текст***
    text = re.sub(r'\*{2}([^*]+)\*{2}', r'\1', text)  # **текст**
    text = re.sub(r'\*{1}([^*\s]+[^*]*?)\*{1}(?=\s|$|[.,!?;:])', r'\1', text)  # *текст* (но не в начале строки)
    text = re.sub(r'(?<!\*)\*([^*\s]+[^*]*?)\*(?!\*)', r'\1', text)  # *текст* (одиночные звездочки)
    
    # Убираем подчеркивания
    text = re.sub(r'__([^_]+)__', r'\1', text)  # __текст__
    text = re.sub(r'_([^_]+)_', r'\1', text)  # _текст_
    
    # Убираем заголовки
    text = re.sub(r'###+\s*', '', text)  # ### заголовок
    text = re.sub(r'##+\s*', '', text)  # ## заголовок
    text = re.sub(r'#+\s*', '', text)  # # заголовок
    
    # Убираем код
    text = re.sub(r'`([^`]+)`', r'\1', text)  # `код`
    
    # Убираем зачеркивание
    text = re.sub(r'~~([^~]+)~~', r'\1', text)  # ~~текст~~
    
    # Убираем лишние пробелы после удаления форматирования
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "без username"
    first_name = update.message.from_user.first_name or "без имени"
    
    # Автоматически подписываем пользователя на уведомления о почте (если еще не подписан)
    subscribers = load_email_subscribers()
    if user_id not in subscribers:
        add_email_subscriber(user_id)
    
    # Обработка приветствий и прощаний
    text_lower = text.lower().strip()
    original_text = text  # Сохраняем оригинальный текст
    
    # Ключевые слова для приветствия
    greeting_keywords = [
        "привет", "здравствуй", "здравствуйте", "добрый день", "добрый вечер", 
        "доброе утро", "hi", "hello", "hey", "доброго времени суток"
    ]
    
    # Ключевые слова для прощания
    goodbye_keywords = [
        "пока", "до свидания", "до встречи", "увидимся", "bye", "goodbye", 
        "see you", "до скорого", "всего доброго", "всего хорошего"
    ]
    
    # Проверяем, является ли сообщение ТОЛЬКО приветствием (короткое сообщение с приветствием)
    is_pure_greeting = any(keyword in text_lower for keyword in greeting_keywords) and len(text_lower.split()) <= 5
    # Проверяем, является ли сообщение ТОЛЬКО прощанием (короткое сообщение с прощанием)
    is_pure_goodbye = any(keyword in text_lower for keyword in goodbye_keywords) and len(text_lower.split()) <= 5
    
    # Проверяем, содержит ли сообщение приветствие или прощание (но может быть и общий вопрос)
    has_greeting = any(keyword in text_lower for keyword in greeting_keywords)
    has_goodbye = any(keyword in text_lower for keyword in goodbye_keywords)
    
    # Добавляем контекст ТОЛЬКО для чистых приветствий/прощаний, не для общих вопросов
    if is_pure_greeting and not has_goodbye:
        text = f"[ПРИВЕТСТВИЕ] {text}\n\nВажно: поздоровайся и представься как AI-ассистент Анастасии Новосёловой. НЕ добавляй прощание в ответ."
    elif is_pure_goodbye and not has_greeting:
        text = f"[ПРОЩАНИЕ] {text}\n\nВажно: вежливо попрощайся с пользователем. НЕ добавляй приветствие в ответ."
    # Если это общий вопрос (содержит приветствие/прощание, но не является чистым), не добавляем контекст
    
    # Проверяем, ожидаем ли мы ответ на email
    if user_id in email_reply_state:
        try:
            email_reply_data = email_reply_state.get(user_id)
            if not email_reply_data:
                await update.message.reply_text("❌ Ошибка: данные письма не найдены")
                email_reply_state.pop(user_id, None)
                return
            
            to_email = email_reply_data.get("to")
            subject = email_reply_data.get("subject")
            email_id = email_reply_data.get("email_id")
            
            if not to_email:
                await update.message.reply_text("❌ Ошибка: адрес получателя не найден")
                email_reply_state.pop(user_id, None)
                return
            
            # Проверяем команду отмены
            if text.lower() in ["/cancel", "отмена", "cancel"]:
                await update.message.reply_text("❌ Отправка ответа отменена")
                email_reply_state.pop(user_id, None)
                return
            
            await update.message.reply_text("⏳ Отправляю ответ на email...")
            
            # Отправляем email
            from email_helper import send_email
            
            success = await send_email(
                to_email=to_email,
                subject=subject,
                body=text,
                is_html=False
            )
            
            if success:
                await update.message.reply_text(
                    f"✅ *Ответ отправлен!*\n\n"
                    f"*Кому:* {to_email}\n"
                    f"*Тема:* {subject}\n\n"
                    f"Ваш ответ был успешно отправлен.",
                    parse_mode='Markdown'
                )
                log.info(f"✅ Ответ на письмо {email_id} отправлен на {to_email}")
            else:
                await update.message.reply_text(
                    "❌ Не удалось отправить ответ. Проверьте настройки SMTP."
                )
            
            # Сбрасываем состояние
            email_reply_state.pop(user_id, None)
            return
            
        except Exception as e:
            log.error(f"❌ Ошибка отправки ответа на email: {e}")
            import traceback
            log.error(traceback.format_exc())
            await update.message.reply_text(f"❌ Ошибка отправки: {str(e)}")
            email_reply_state.pop(user_id, None)
            return
    
    # Проверяем, ждем ли мы название задачи для WEEEK
    # Обработка обновления задачи
    if context.user_data.get("waiting_for_task_update"):
        try:
            from weeek_helper import update_task
            
            task_id = context.user_data.get("editing_task_id")
            field = context.user_data.get("waiting_for_task_update")
            new_value = text
            
            if not task_id:
                await update.message.reply_text("❌ Ошибка: задача не выбрана")
                context.user_data["waiting_for_task_update"] = None
                return
            
            await update.message.reply_text("⏳ Обновляю задачу...")
            
            # Обновляем задачу
            if field == "title":
                updated_task = await update_task(task_id, title=new_value)
            elif field == "description":
                updated_task = await update_task(task_id, description=new_value)
            else:
                await update.message.reply_text("❌ Неизвестное поле для обновления")
                context.user_data["waiting_for_task_update"] = None
                return
            
            if updated_task:
                field_name = "Название" if field == "title" else "Описание"
                await update.message.reply_text(
                    f"✅ {field_name} задачи обновлено!\n\n"
                    f"Используйте /weeek_update для дальнейшего редактирования"
                )
                log.info(f"✅ Задача {task_id} обновлена: {field} = {new_value}")
            else:
                await update.message.reply_text("❌ Не удалось обновить задачу")
            
            # Сбрасываем флаг ожидания
            context.user_data["waiting_for_task_update"] = None
            context.user_data["editing_task_id"] = None
            return
            
        except Exception as e:
            log.error(f"❌ Ошибка обновления задачи: {e}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
            context.user_data["waiting_for_task_update"] = None
            return
    
    # Обработка даты задачи
    if context.user_data.get("waiting_for_task_date"):
        try:
            from weeek_helper import create_task, get_project
            import re
            from datetime import datetime
            
            project_id = context.user_data.get("selected_project_id")
            task_name = context.user_data.get("task_name_temp")
            task_date = text.strip()
            
            if not project_id or not task_name:
                await update.message.reply_text("❌ Ошибка: данные задачи потеряны")
                context.user_data["waiting_for_task_date"] = False
                return
            
            # Парсим дату (поддерживаем разные форматы)
            day_formatted = None
            
            # Формат dd.mm.yyyy
            if re.match(r'\d{1,2}\.\d{1,2}\.\d{4}', task_date):
                day_formatted = task_date
            # Формат dd.mm
            elif re.match(r'\d{1,2}\.\d{1,2}', task_date):
                parts = task_date.split('.')
                current_year = datetime.now().year
                day_formatted = f"{parts[0].zfill(2)}.{parts[1].zfill(2)}.{current_year}"
            # Формат dd/mm/yyyy или dd-mm-yyyy
            elif re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', task_date):
                task_date = task_date.replace('/', '.').replace('-', '.')
                day_formatted = task_date
            # Относительные даты
            elif task_date.lower() in ['сегодня', 'today']:
                day_formatted = datetime.now().strftime("%d.%m.%Y")
            elif task_date.lower() in ['завтра', 'tomorrow']:
                from datetime import timedelta
                day_formatted = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
            # Пропустить дату
            elif task_date.lower() in ['нет', 'no', 'skip', 'пропустить', '-']:
                day_formatted = None
            else:
                await update.message.reply_text(
                    "❌ Неверный формат даты!\n\n"
                    "Используйте:\n"
                    "• `25.12.2024` или `25.12`\n"
                    "• `сегодня` / `завтра`\n"
                    "• `нет` - без даты"
                )
                return
            
            await update.message.reply_text(f"⏳ Создаю задачу...")
            
            # Получаем название проекта
            project = await get_project(project_id)
            project_title = project.get("title", f"Проект {project_id}") if project else f"Проект {project_id}"
            
            # Создаем задачу
            task = await create_task(
                project_id=project_id,
                title=task_name,
                description=f"Создано через Telegram бот пользователем @{username}",
                day=day_formatted
            )
            
            if task:
                text_result = f"✅ *Задача создана в WEEEK!*\n\n"
                text_result += f"📁 *Проект:* {project_title}\n"
                text_result += f"📝 *Задача:* {task_name}\n"
                if day_formatted:
                    text_result += f"📅 *Дата:* {day_formatted}\n"
                text_result += f"🆔 *ID:* `{task.get('id')}`\n\n"
                text_result += f"Используйте `/weeek_tasks {project_id}` для просмотра всех задач"
                
                await update.message.reply_text(text_result, parse_mode='Markdown')
                log.info(f"✅ Задача создана в WEEEK: {task_name} в проекте {project_title} (ID: {project_id}), дата: {day_formatted}")
            else:
                await update.message.reply_text("❌ Не удалось создать задачу в WEEEK")
            
            # Сбрасываем флаги
            context.user_data["waiting_for_task_date"] = False
            context.user_data["selected_project_id"] = None
            context.user_data["task_name_temp"] = None
            return
            
        except Exception as e:
            log.error(f"❌ Ошибка создания задачи: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
            context.user_data["waiting_for_task_date"] = False
            context.user_data["selected_project_id"] = None
            context.user_data["task_name_temp"] = None
            return
    
    # Обработка названия задачи (шаг 1: название, потом спросим дату)
    if context.user_data.get("waiting_for_task_name"):
        try:
            project_id = context.user_data.get("selected_project_id")
            task_name = text

            if not project_id:
                await update.message.reply_text("❌ Ошибка: проект не выбран")
                context.user_data["waiting_for_task_name"] = False
                return
            
            # Сохраняем название и спрашиваем дату
            context.user_data["task_name_temp"] = task_name
            context.user_data["waiting_for_task_name"] = False
            context.user_data["waiting_for_task_date"] = True
            
            await update.message.reply_text(
                f"✅ Название задачи: *{task_name}*\n\n"
                f"📅 *Укажите дату задачи:*\n\n"
                f"Форматы:\n"
                f"• `25.12.2024` или `25.12`\n"
                f"• `сегодня` / `завтра`\n"
                f"• `нет` - создать без даты\n\n"
                f"Например: `25.12` или `завтра`",
                parse_mode='Markdown'
            )
            return

        except Exception as e:
            log.error(f"❌ Ошибка: {e}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
            context.user_data["waiting_for_task_name"] = False
            return
    
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
            # Проверяем историю разговора, чтобы не повторяться
            history = get_history(user_id)
            history_lower = history.lower() if history else ""
            has_greeted_before = any(keyword in history_lower for keyword in ["здравствуйте", "привет", "hello", "hi", "добрый"])
            
            # Если это чистое приветствие и еще не здоровались - здороваемся
            if is_pure_greeting and not has_greeted_before:
                answer = (
                    "Здравствуйте! Я AI-ассистент Анастасии Новосёловой. Чем могу помочь? 😊\n\n"
                    "Я специализируюсь на:\n"
                    "• Подборе персонала (рекрутинг)\n"
                    "• Автоматизации HR-процессов\n"
                    "• Бизнес-анализе и консалтинге\n\n"
                    "Чем могу помочь в рамках HR консалтинга? 💼"
                )
            # Если это общий вопрос (не чистое приветствие) - отвечаем без приветствия и прощания
            else:
                answer = (
                    "У меня всё отлично, спасибо! 😊\n\n"
                    "Я AI-ассистент Анастасии Новосёловой, специализируюсь на:\n"
                    "• Подборе персонала (рекрутинг)\n"
                    "• Автоматизации HR-процессов\n"
                    "• Бизнес-анализе и консалтинге\n\n"
                    "Чем могу помочь в рамках HR консалтинга? 💼"
                )
            log.info("💬 Общий вопрос обработан с напоминанием о HR контексте")
        else:
            # Обычная обработка через RAG и LLM
            # Если это чистое прощание, добавляем специальный ответ
            if is_pure_goodbye:
                # Проверяем историю, чтобы не повторяться
                history = get_history(user_id)
                history_lower = history.lower() if history else ""
                has_said_goodbye_before = any(keyword in history_lower for keyword in ["до свидания", "пока", "goodbye", "bye"])
                
                if not has_said_goodbye_before:
                    answer = "До свидания! Буду рад помочь снова. 😊"
                else:
                    answer = "До свидания! 😊"
                log.info("💬 Прощание обработано")
            else:
                msg = CONSULTING_PROMPT.replace("{{history}}", get_history(user_id)).replace("{{message}}", text)
                
                # Улучшенный RAG поиск + контекст из WEEEK
                rag_context = ""
                weeek_context = ""
                
                try:
                    # 1. Поиск в Qdrant (RAG)
                    if QDRANT_AVAILABLE:
                        from qdrant_helper import get_qdrant_client, generate_embedding_async
                        
                        client = get_qdrant_client()
                        if client:
                            # Генерируем эмбеддинг для запроса
                            query_embedding = await generate_embedding_async(text)
                            
                            if query_embedding:
                                # Ищем в Qdrant
                                search_results = client.query_points(
                                    collection_name="hr2137_bot_knowledge_base",
                                    query=query_embedding,
                                    limit=5
                                )
                                
                                if search_results.points:
                                    rag_docs = []
                                    for point in search_results.points[:3]:  # Топ-3
                                        payload = point.payload if hasattr(point, 'payload') else {}
                                        file_name = payload.get("file_name", "Документ")
                                        text_chunk = payload.get("text", "")
                                        score = point.score if hasattr(point, 'score') else 0.0
                                        
                                        if text_chunk:
                                            rag_docs.append({
                                                "file": file_name,
                                                "content": text_chunk[:300],  # Первые 300 символов
                                                "score": score
                                            })
                                    
                                    if rag_docs:
                                        context_parts = []
                                        for doc in rag_docs:
                                            context_parts.append(f"📄 {doc['file']} (релевантность: {doc['score']:.2f}):\n{doc['content']}")
                                        
                                        rag_context = f"Релевантная информация из базы знаний:\n\n" + "\n\n".join(context_parts) + "\n\n"
                                        log.info(f"✅ Найдено {len(rag_docs)} документов в RAG для запроса")
                except Exception as e:
                    log.warning(f"⚠️ Ошибка RAG поиска: {e}")
                
                # 2. Контекст из WEEEK (проекты и задачи)
                try:
                    from weeek_helper import get_projects, get_tasks
                    
                    # Получаем список проектов
                    projects = await get_projects()
                    if projects:
                        active_projects = [p for p in projects if not p.get('isArchived', False)][:5]  # Топ-5 активных
                        
                        if active_projects:
                            project_info = []
                            for project in active_projects:
                                project_id = project.get('id')
                                project_title = project.get('title', 'Без названия')
                                
                                # Получаем задачи проекта
                                tasks = await get_tasks(project_id=project_id, completed=False, per_page=5)
                                task_list = []
                                if tasks and tasks.get('tasks'):
                                    for task in tasks['tasks'][:3]:  # Топ-3 задачи
                                        task_name = task.get('name') or task.get('title', 'Задача')
                                        task_list.append(f"  • {task_name}")
                                
                                project_info.append(f"📋 Проект: {project_title} (ID: {project_id})")
                                if task_list:
                                    project_info.append("\n".join(task_list))
                            
                            if project_info:
                                weeek_context = f"Активные проекты и задачи в WEEEK:\n\n" + "\n\n".join(project_info) + "\n\n"
                                log.info(f"✅ Получен контекст из WEEEK: {len(active_projects)} проектов")
                except Exception as e:
                    log.warning(f"⚠️ Ошибка получения контекста WEEEK: {e}")
                
                # Объединяем контексты
                full_context = ""
                if rag_context:
                    full_context += rag_context
                if weeek_context:
                    full_context += weeek_context
                
                msg = msg.replace("{{rag_context}}", full_context)
                
                # Используем generate_with_fallback для надежности
                try:
                    from llm_helper import generate_with_fallback
                    system_message = """Ты AI-ассистент HR консультанта Анастасии Новосёловой. Отвечай профессионально и по делу.

КРИТИЧЕСКИ ВАЖНО - ПРАВИЛА ОБЩЕНИЯ:
- ✅ Предлагай ТОЛЬКО Анастасию Новосёлову как консультанта/тренера/специалиста
- ❌ НИКОГДА не предлагай других тренеров, консультантов или специалистов
- ❌ НИКОГДА не говори "подберу тренера", "найду консультанта", "подберу специалиста"
- ❌ НИКОГДА не предлагай альтернативных вариантов или других людей
- ✅ Если спрашивают про тренера/консультанта, отвечай: "Я могу предложить услуги Анастасии Новосёловой"
- ❌ НИКОГДА не используй Markdown форматирование (звездочки **, подчеркивания __ и т.д.) - пиши обычным текстом

ПРАВИЛА ПРИВЕТСТВИЯ И ПРОЩАНИЯ:
- ✅ Если это ПРИВЕТСТВИЕ - поздоровайся и представься: "Здравствуйте! Я AI-ассистент Анастасии Новосёловой. Чем могу помочь?"
- ✅ Если это ПРОЩАНИЕ - вежливо попрощайся: "До свидания! Буду рад помочь снова"
- ❌ НИКОГДА не пиши приветствие И прощание в одном сообщении
- ❌ Если это общий вопрос (не приветствие и не прощание) - НЕ добавляй приветствие и прощание
- ✅ Используй историю разговора - не повторяйся, если уже здоровался или прощался ранее"""
                    
                    # Добавляем историю разговора в контекст для LLM
                    history = get_history(user_id)
                    if history:
                        # Проверяем, было ли уже приветствие в истории
                        history_lower = history.lower()
                        has_greeted_before = any(keyword in history_lower for keyword in ["здравствуйте", "привет", "hello", "hi", "добрый"])
                        has_said_goodbye_before = any(keyword in history_lower for keyword in ["до свидания", "пока", "goodbye", "bye"])
                        
                        # Если уже здоровались ранее и это не чистое приветствие - не добавляем приветствие
                        if has_greeted_before and not is_pure_greeting:
                            system_message += "\n\nВАЖНО: Ты уже здоровался с пользователем ранее. НЕ повторяй приветствие в ответе."
                        # Если уже прощались ранее и это не чистое прощание - не добавляем прощание
                        if has_said_goodbye_before and not is_pure_goodbye:
                            system_message += "\n\nВАЖНО: Ты уже прощался с пользователем ранее. НЕ повторяй прощание в ответе."
                    
                    answer = await generate_with_fallback([{"role": "user", "content": msg}], use_system_message=True, system_content=system_message)
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

    # Убираем Markdown из ответа перед сохранением в память и отправкой
    if answer:
        answer = remove_markdown(answer)
    
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
        # Убираем Markdown форматирование из ответа
        answer_clean = remove_markdown(answer)
        await update.message.reply_text(answer_clean)

# ===================== NEW COMMANDS FOR DEMONSTRATION =====================

async def rag_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rag_search - поиск в RAG базе знаний с генерацией ответа"""
    query = " ".join(context.args) if context.args else "помощь"
    
    try:
        await update.message.reply_text(f"🔍 Ищу в базе знаний: *{query}*...", parse_mode='Markdown')
        
        from qdrant_helper import get_qdrant_client, generate_embedding_async
        from llm_helper import generate_with_fallback
        
        client = get_qdrant_client()
        if not client:
            await update.message.reply_text("❌ Qdrant недоступен")
            return
        
        # Генерируем эмбеддинг для запроса
        query_embedding = await generate_embedding_async(query)
        if not query_embedding:
            await update.message.reply_text("❌ Ошибка создания эмбеддинга")
            return
        
        # Ищем в Qdrant
        search_results = client.query_points(
            collection_name="hr2137_bot_knowledge_base",
            query=query_embedding,
            limit=5
        )
        
        if not search_results.points:
            await update.message.reply_text(f"❌ По запросу '{query}' ничего не найдено в базе знаний.")
            return
        
        # Собираем результаты и источники
        results = []
        sources = {}
        
        for point in search_results.points:
            payload = point.payload if hasattr(point, 'payload') else {}
            score = point.score if hasattr(point, 'score') else 0.0
            
            # Извлекаем информацию о документе
            file_name = payload.get("file_name", "Документ")
            file_path = payload.get("file_path", "")
            text = payload.get("text", "")
            source = payload.get("source", "")
            
            if text:  # Только если есть текст
                results.append({
                    "file_name": file_name,
                    "text": text,
                    "file_path": file_path,
                    "source": source,
                    "score": score
                })
                
                # Собираем уникальные источники
                if file_name and file_name not in sources:
                    sources[file_name] = file_path
        
        if not results:
            await update.message.reply_text(f"❌ Найдены документы, но без текстового содержимого.")
            return
        
        # Формируем контекст для LLM
        context = "\n\n".join([
            f"Источник: {r['file_name']}\n{r['text'][:500]}"
            for r in results[:3]  # Берем топ-3 для контекста
        ])
        
        # Генерируем ответ через LLM
        prompt = f"""На основе следующих документов из базы знаний ответь на вопрос пользователя.

Вопрос: {query}

Документы:
{context}

Ответь подробно и структурированно, ссылаясь на источники. Если информации недостаточно, укажи это.

ВАЖНО: Не используй Markdown форматирование (**, ###, __ и т.д.). Пиши обычным текстом."""
        
        answer = await generate_with_fallback(
            messages=[{"role": "user", "content": prompt}],
            use_system_message=True,
            system_content="Ты AI-ассистент HR консультанта. Отвечай профессионально и по делу на основе предоставленных документов.",
            max_tokens=1000,
            temperature=0.7
        )
        
        # Убираем Markdown из ответа
        if answer:
            answer_clean = remove_markdown(answer)
        else:
            answer_clean = "Не удалось сгенерировать ответ. Проверьте доступность LLM."
        
        # Формируем ответ пользователю
        text = f"🔍 Результаты поиска: {query}\n\n"
        
        # Ответ на основе документов
        if answer_clean:
            text += f"💡 Ответ на основе документов:\n\n"
            text += f"{answer_clean}\n\n"
        
        # Источники
        if sources:
            text += f"📚 Источники ({len(sources)}):\n\n"
            for i, (name, path) in enumerate(sources.items(), 1):
                text += f"{i}. 📄 {name}\n"
                if path:
                    text += f"   {path}\n"
                text += "\n"
        
        # Релевантные фрагменты
        text += f"\n📋 Релевантные фрагменты:\n\n"
        for i, r in enumerate(results[:3], 1):
            text += f"{i}. {r['file_name']} (релевантность: {r['score']:.2f})\n"
            snippet = r['text'][:200] + "..." if len(r['text']) > 200 else r['text']
            text += f"   {snippet}\n\n"
        
        # Если сообщение слишком длинное, разбиваем на части
        max_length = 4000
        if len(text) > max_length:
            # Разбиваем на части
            parts = []
            current_part = ""
            
            lines = text.split('\n')
            for line in lines:
                if len(current_part) + len(line) + 1 > max_length:
                    parts.append(current_part)
                    current_part = ""
                current_part += line + "\n"
            
            if current_part:
                parts.append(current_part)
            
            # Отправляем все части
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(text)
        
    except Exception as e:
        log.error(f"❌ Ошибка поиска в RAG: {e}")
        import traceback
        log.error(traceback.format_exc())
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
    """Команда /summary - суммаризация проекта с использованием WEEEK и RAG"""
    project_name = " ".join(context.args) if context.args else "текущий"
    
    try:
        await update.message.reply_text(f"⏳ Суммаризирую проект '{project_name}'...")

        # 1. Получаем данные из WEEEK
        weeek_data = ""
        try:
            from weeek_helper import get_projects, get_tasks
            
            projects = await get_projects()
            target_project = None
            
            # Ищем проект по названию или ID
            if project_name.lower() != "текущий":
                # Сначала проверяем, не указан ли ID (число)
                try:
                    project_id_input = int(project_name.strip())
                    # Ищем по ID
                    for project in projects:
                        if project.get('id') == project_id_input:
                            target_project = project
                            log.info(f"✅ Найден проект по ID: {project_id_input} - {project.get('title')}")
                            break
                except ValueError:
                    # Не число, ищем по названию
                    project_name_lower = project_name.lower().strip()
                    
                    # 1. Сначала точное совпадение
                    for project in projects:
                        if project.get('title', '').lower().strip() == project_name_lower:
                            target_project = project
                            log.info(f"✅ Найден проект точным совпадением: {project.get('title')}")
                            break
                    
                    # 2. Если не нашли, ищем частичное совпадение (но только если название короткое)
                    if not target_project and len(project_name_lower) > 3:
                        for project in projects:
                            project_title_lower = project.get('title', '').lower()
                            # Проверяем, что название проекта начинается с запроса или запрос - это отдельное слово
                            if (project_title_lower.startswith(project_name_lower) or 
                                f" {project_name_lower} " in f" {project_title_lower} "):
                                target_project = project
                                log.info(f"✅ Найден проект частичным совпадением: {project.get('title')}")
                                break
            
            # Если не нашли, берем первый активный
            if not target_project and projects:
                target_project = [p for p in projects if not p.get('isArchived', False)][0] if projects else None
                if target_project:
                    log.info(f"⚠️ Проект '{project_name}' не найден, используется первый активный: {target_project.get('title')}")
            
            if target_project:
                project_id = target_project.get('id')
                project_title = target_project.get('title', 'Без названия')
                
                # Получаем задачи проекта
                tasks = await get_tasks(project_id=project_id, per_page=20)
                
                weeek_data = f"Проект: {project_title} (ID: {project_id})\n\n"
                
                if tasks and tasks.get('tasks'):
                    completed = [t for t in tasks['tasks'] if t.get('isCompleted', False)]
                    active = [t for t in tasks['tasks'] if not t.get('isCompleted', False)]
                    
                    weeek_data += f"Задач всего: {len(tasks['tasks'])}\n"
                    weeek_data += f"Активных: {len(active)}\n"
                    weeek_data += f"Завершенных: {len(completed)}\n\n"
                    
                    if active:
                        weeek_data += "Активные задачи:\n"
                        for task in active[:10]:
                            task_name = task.get('name') or task.get('title', 'Задача')
                            priority = task.get('priority', 0)
                            weeek_data += f"  • {task_name} (приоритет: {priority})\n"
                    
                    if completed:
                        weeek_data += "\nЗавершенные задачи:\n"
                        for task in completed[:5]:
                            task_name = task.get('name') or task.get('title', 'Задача')
                            weeek_data += f"  • {task_name}\n"
                
                log.info(f"✅ Получены данные из WEEEK для проекта {project_title}")
        except Exception as e:
            log.warning(f"⚠️ Ошибка получения данных WEEEK: {e}")
        
        # 2. Получаем релевантную информацию из RAG
        rag_context = ""
        try:
            from qdrant_helper import get_qdrant_client, generate_embedding_async
            
            client = get_qdrant_client()
            if client:
                # Ищем по названию проекта
                search_query = f"{project_name} {target_project.get('title', '') if target_project else ''}"
                query_embedding = await generate_embedding_async(search_query)
                
                if query_embedding:
                    search_results = client.query_points(
                        collection_name="hr2137_bot_knowledge_base",
                        query=query_embedding,
                        limit=5
                    )
                    
                    if search_results.points:
                        rag_docs = []
                        for point in search_results.points:
                            payload = point.payload if hasattr(point, 'payload') else {}
                            file_name = payload.get("file_name", "Документ")
                            text_chunk = payload.get("text", "")
                            
                            if text_chunk:
                                rag_docs.append(f"📄 {file_name}: {text_chunk[:400]}")
                        
                        if rag_docs:
                            rag_context = "Релевантные документы из базы знаний:\n\n" + "\n\n".join(rag_docs) + "\n\n"
                            log.info(f"✅ Найдено {len(rag_docs)} документов в RAG")
        except Exception as e:
            log.warning(f"⚠️ Ошибка RAG поиска: {e}")
        
        # 3. Генерируем суммаризацию через LLM
        from llm_helper import generate_with_fallback
        
        prompt = f"""Создай подробную суммаризацию проекта на основе следующих данных:

Название проекта: {project_name}

Данные из WEEEK:
{weeek_data if weeek_data else "Данные из WEEEK недоступны"}

Релевантные документы:
{rag_context if rag_context else "Релевантные документы не найдены"}

Создай структурированную суммаризацию, включающую:
1. Общее описание проекта
2. Текущий статус (активные задачи, прогресс)
3. Ключевые достижения
4. Следующие шаги
5. Рекомендации

ВАЖНО: Не используй Markdown форматирование (**, ###, __ и т.д.). Пиши обычным текстом с переносами строк."""
        
        summary = await generate_with_fallback(
            messages=[{"role": "user", "content": prompt}],
            use_system_message=True,
            system_content="Ты AI-ассистент HR консультанта. Создавай подробные и структурированные суммаризации проектов.",
            max_tokens=1500,
            temperature=0.7
        )
        
        if not summary:
            summary = "Не удалось создать суммаризацию. Проверьте доступность LLM и данных."

        # Очищаем summary от Markdown
        summary_clean = remove_markdown(summary)
        
        # Формируем сообщение без Markdown
        message_text = f"Суммаризация проекта '{project_name}':\n\n{summary_clean}"
        
        # Если сообщение слишком длинное, разбиваем на части
        max_length = 4000  # Лимит Telegram
        
        if len(message_text) > max_length:
            # Разбиваем на части
            parts = []
            header = f"Суммаризация проекта '{project_name}':\n\n"
            current_part = header
            
            # Пробуем разбить по разделам
            lines = summary_clean.split('\n')
            for line in lines:
                if len(current_part) + len(line) + 1 > max_length:
                    parts.append(current_part)
                    current_part = ""
                current_part += line + "\n"
            
            if current_part:
                parts.append(current_part)
            
            # Отправляем все части без Markdown
            for part in parts:
                await update.message.reply_text(part)
        else:
            # Отправляем без Markdown
            await update.message.reply_text(message_text)
    except Exception as e:
        log.error(f"❌ Ошибка суммаризации: {e}")
        import traceback
        log.error(traceback.format_exc())
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
            if project_name.lower() in project.get("title", "").lower():
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
                title = project.get("title", "Без названия")
                project_id = project.get("id", "")
                color = project.get("color", "")
                text += f"{i}. *{title}*\n"
                text += f"   ID: `{project_id}`"
                if color:
                    text += f" • {color}"
                text += "\n\n"

            await update.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ Проектов не найдено.\n\n"
                "Проверьте WEEEK_TOKEN в настройках."
            )
    except Exception as e:
        log.error(f"❌ Ошибка получения проектов: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def weeek_update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weeek_update - обновление задачи в Weeek (интерактивное меню)"""
    try:
        from weeek_helper import get_projects
        
        await update.message.reply_text("⏳ Загружаю проекты...")
        
        projects = await get_projects()
        
        if not projects:
            await update.message.reply_text(
                "❌ Проектов не найдено.\n\n"
                "Сначала создайте проекты в WEEEK."
            )
            return
        
        # Показываем список проектов для выбора
        keyboard = []
        for project in projects[:15]:
            project_name = project.get("name", "Без названия")
            project_id = project.get("id", "")
            keyboard.append([
                InlineKeyboardButton(
                    f"📁 {project_name}",
                    callback_data=f"weeek_update_select_project_{project_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")])
        
        await update.message.reply_text(
            "🔄 *Обновление задачи*\n\n"
            "Шаг 1/3: Выберите проект с задачей:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def weeek_tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weeek_tasks - просмотр задач проекта с фильтрами"""
    if not context.args:
        await update.message.reply_text(
            "📋 *Просмотр задач проекта*\n\n"
            "**Использование:**\n"
            "`/weeek_tasks [project_id] [фильтры]`\n\n"
            "**Примеры:**\n"
            "`/weeek_tasks 1` - все активные\n"
            "`/weeek_tasks 1 all` - все задачи\n"
            "`/weeek_tasks 1 high` - высокий приоритет\n"
            "`/weeek_tasks 1 completed` - завершенные\n\n"
            "**Фильтры:**\n"
            "• `all` - все задачи\n"
            "• `completed` - завершенные\n"
            "• `active` - активные\n"
            "• `low/medium/high/hold` - по приоритету\n\n"
            "Узнайте ID проектов:\n"
            "`/weeek_info`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from weeek_helper import get_tasks, get_project
        
        project_id = int(context.args[0])
        
        # Парсим фильтры
        filters = " ".join(context.args[1:]).lower() if len(context.args) > 1 else ""
        
        completed = None
        priority = None
        show_all = False
        
        if "all" in filters:
            show_all = True
        elif "completed" in filters:
            completed = True
        elif "active" in filters:
            completed = False
        
        if "low" in filters:
            priority = 0
        elif "medium" in filters:
            priority = 1
        elif "high" in filters:
            priority = 2
        elif "hold" in filters:
            priority = 3
        
        await update.message.reply_text("⏳ Загружаю задачи...")
        
        # Получаем название проекта
        project = await get_project(project_id)
        project_title = project.get("title", f"Проект {project_id}") if project else f"Проект {project_id}"
        
        # Получаем задачи с фильтрами
        result = await get_tasks(
            project_id=project_id,
            completed=completed,
            priority=priority,
            all_tasks=show_all,
            per_page=50
        )
        
        if result["success"] and result["tasks"]:
            tasks = result["tasks"]
            has_more = result["hasMore"]
            
            # Формируем заголовок
            filter_text = []
            if show_all:
                filter_text.append("все")
            elif completed is True:
                filter_text.append("завершенные")
            elif completed is False:
                filter_text.append("активные")
            
            if priority is not None:
                priority_names = ["низкий", "средний", "высокий", "в ожидании"]
                filter_text.append(f"приоритет: {priority_names[priority]}")
            
            filter_str = f" ({', '.join(filter_text)})" if filter_text else ""
            
            text = f"📋 *Задачи: {project_title}*{filter_str}\n"
            text += f"Найдено: {len(tasks)}\n"
            if has_more:
                text += f"⚠️ Показаны первые {len(tasks)}, есть еще\n"
            text += "\n"
            
            # Группируем по приоритету
            priority_groups = {0: [], 1: [], 2: [], 3: [], None: []}
            for task in tasks:
                p = task.get("priority")
                priority_groups[p].append(task)
            
            priority_emoji = {0: "🟢", 1: "🟡", 2: "🔴", 3: "⏸", None: "⚪"}
            priority_names = {0: "Низкий", 1: "Средний", 2: "Высокий", 3: "В ожидании", None: "Без приоритета"}
            
            count = 0
            for p in [2, 3, 1, 0, None]:  # Высокий -> Hold -> Средний -> Низкий -> Нет
                if priority_groups[p]:
                    text += f"\n*{priority_emoji[p]} {priority_names[p]}:*\n"
                    for task in priority_groups[p]:
                        count += 1
                        title = task.get("title", "Без названия")
                        task_id = task.get("id", "")
                        is_completed = task.get("isCompleted", False)
                        status = "✅" if is_completed else "⭕"
                        
                        # Обрезаем длинные названия
                        if len(title) > 40:
                            title = title[:37] + "..."
                        
                        text += f"{count}. {status} {title}\n"
                        text += f"   ID: `{task_id}`\n"
            
            text += f"\n💡 Для редактирования: `/weeek_update`"
            
            await update.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                f"📋 *Проект: {project_title}*\n\n"
                "❌ Задач не найдено.",
                parse_mode='Markdown'
            )
            
    except ValueError:
        await update.message.reply_text("❌ Неверный ID проекта (должно быть число)")
    except Exception as e:
        log.error(f"❌ Ошибка получения задач: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def weeek_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weeek_info - информация о workspace и проектах"""
    try:
        from weeek_helper import get_workspace_info, get_projects
        
        await update.message.reply_text("⏳ Получаю информацию о workspace...")
        
        # Получаем workspace info
        workspace = await get_workspace_info()
        
        if not workspace:
            await update.message.reply_text("❌ Не удалось получить информацию о workspace")
            return
        
        workspace_id = workspace.get("id")
        title = workspace.get("title", "Без названия")
        is_personal = workspace.get("isPersonal", False)
        
        # Получаем список проектов
        projects = await get_projects()
        
        # Формируем сообщение
        text = f"📊 *WORKSPACE INFO*\n\n"
        text += f"🆔 ID: `{workspace_id}`\n"
        text += f"📝 Название: {title}\n"
        text += f"👤 Персональный: {'Да' if is_personal else 'Нет'}\n\n"
        
        if projects:
            text += f"📋 *ПРОЕКТЫ* (всего: {len(projects)})\n\n"
            for i, project in enumerate(projects[:10], 1):
                project_title = project.get("title", "Без названия")
                project_id = project.get("id", "")
                color = project.get("color", "")
                is_private = project.get("isPrivate", False)
                
                text += f"{i}. *{project_title}*\n"
                text += f"   🆔 ID: `{project_id}`\n"
                if color:
                    text += f"   🎨 Цвет: {color}\n"
                if is_private:
                    text += f"   🔒 Приватный\n"
                text += "\n"
            
            if len(projects) > 10:
                text += f"_...и еще {len(projects) - 10} проектов_\n\n"
            
            text += f"💡 *Используйте:*\n"
            text += f"• `/weeek_tasks [ID]` - задачи проекта\n"
            text += f"• `/weeek_task [название] | [задача]` - создать задачу"
        else:
            text += "❌ Проектов не найдено\n\n"
            text += "Создайте проект:\n"
            text += "`/weeek_create_project [название]`"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка получения workspace info: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def weeek_create_project_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /weeek_create_project - создание проекта в Weeek"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите название проекта.\n"
            "Использование: `/weeek_create_project [название]`\n\n"
            "Примеры:\n"
            "`/weeek_create_project Новый проект HR`\n"
            "`/weeek_create_project Консалтинг 2025`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from weeek_helper import create_project
        
        project_name = " ".join(context.args)
        username = update.message.from_user.username or update.message.from_user.first_name
        
        await update.message.reply_text(f"⏳ Создаю проект: {project_name}")
        
        project = await create_project(
            name=project_name,
            description=f"Создано через Telegram бот пользователем @{username}"
        )
        
        if project:
            project_id = project.get("id")
            await update.message.reply_text(
                f"✅ Проект создан в WEEEK!\n\n"
                f"📁 Название: {project_name}\n"
                f"🆔 ID: `{project_id}`\n\n"
                f"Теперь можете добавить задачи:\n"
                f"`/weeek_task {project_name} | Название задачи`\n"
                f"или через меню: `/weeek_update`",
                parse_mode='Markdown'
            )
            log.info(f"✅ Проект создан: {project_name} (ID: {project_id})")
        else:
            await update.message.reply_text("❌ Не удалось создать проект в WEEEK")
            
    except Exception as e:
        log.error(f"❌ Ошибка создания проекта: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def yadisk_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /yadisk_list - список файлов на Яндекс.Диске"""
    try:
        from yandex_disk_helper import list_files, get_disk_info, format_file_size, get_file_type
        
        await update.message.reply_text("⏳ Получаю список файлов с Яндекс.Диска...")
        
        # Получаем информацию о диске
        disk_info = await get_disk_info()
        
        # Получаем список файлов
        path = " ".join(context.args) if context.args else "/"
        result = await list_files(path=path, limit=50)
        
        if not result:
            await update.message.reply_text("❌ Не удалось получить список файлов")
            return
        
        items = result.get("_embedded", {}).get("items", [])
        
        if not items:
            await update.message.reply_text(
                f"📂 *Яндекс.Диск*\n\n"
                f"Папка `{path}` пуста",
                parse_mode='Markdown'
            )
            return
        
        # Формируем сообщение
        text = f"📂 *Яндекс.Диск*\n\n"
        
        if disk_info:
            total = disk_info.get("total_space", 0) / (1024**3)
            used = disk_info.get("used_space", 0) / (1024**3)
            text += f"💾 Занято: {used:.1f} ГБ из {total:.1f} ГБ\n\n"
        
        text += f"📁 Путь: `{path}`\n"
        text += f"Файлов: {len(items)}\n\n"
        
        # Группируем по типу
        folders = [item for item in items if item.get("type") == "dir"]
        files = [item for item in items if item.get("type") == "file"]
        
        # Показываем папки
        if folders:
            text += "*📁 Папки:*\n"
            for folder in folders[:10]:
                name = folder.get("name", "")
                text += f"  • {name}/\n"
            if len(folders) > 10:
                text += f"  _...и еще {len(folders) - 10} папок_\n"
            text += "\n"
        
        # Показываем файлы
        if files:
            text += "*📄 Файлы:*\n"
            for file in files[:15]:
                name = file.get("name", "")
                size = format_file_size(file.get("size", 0))
                file_type = get_file_type(name)
                
                type_emoji = {
                    'document': '📝',
                    'spreadsheet': '📊',
                    'presentation': '📈',
                    'image': '🖼',
                    'archive': '📦',
                    'code': '💻',
                    'other': '📄'
                }.get(file_type, '📄')
                
                # Обрезаем длинные имена
                if len(name) > 30:
                    name = name[:27] + "..."
                
                text += f"  {type_emoji} {name} • {size}\n"
            
            if len(files) > 15:
                text += f"  _...и еще {len(files) - 15} файлов_\n"
        
        text += f"\n💡 Используйте:\n"
        text += f"• `/yadisk_search [запрос]` - поиск файлов\n"
        text += f"• `/yadisk_recent` - последние файлы"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка получения файлов: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def yadisk_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /yadisk_search - поиск файлов на Яндекс.Диске"""
    if not context.args:
        await update.message.reply_text(
            "🔍 *Поиск на Яндекс.Диске*\n\n"
            "Использование: `/yadisk_search [запрос]`\n\n"
            "Примеры:\n"
            "• `/yadisk_search договор`\n"
            "• `/yadisk_search КП`\n"
            "• `/yadisk_search .pdf`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from yandex_disk_helper import search_files, format_file_size, get_file_type
        
        query = " ".join(context.args)
        
        await update.message.reply_text(f"🔍 Ищу файлы: *{query}*...", parse_mode='Markdown')
        
        files = await search_files(query, limit=50)
        
        if not files:
            await update.message.reply_text(
                f"🔍 Поиск: *{query}*\n\n"
                f"❌ Файлов не найдено",
                parse_mode='Markdown'
            )
            return
        
        text = f"🔍 *Найдено: {len(files)} файлов*\n\n"
        text += f"Запрос: `{query}`\n\n"
        
        for i, file in enumerate(files[:20], 1):
            name = file.get("name", "")
            size = format_file_size(file.get("size", 0))
            path = file.get("path", "")
            file_type = get_file_type(name)
            
            type_emoji = {
                'document': '📝',
                'spreadsheet': '📊',
                'presentation': '📈',
                'image': '🖼',
                'archive': '📦',
                'code': '💻',
                'other': '📄'
            }.get(file_type, '📄')
            
            # Обрезаем длинные имена
            display_name = name[:35] + "..." if len(name) > 35 else name
            
            text += f"{i}. {type_emoji} {display_name}\n"
            text += f"   {size} • `{path}`\n\n"
        
        if len(files) > 20:
            text += f"_...и еще {len(files) - 20} файлов_\n\n"
        
        text += f"💡 Для скачивания используйте путь файла"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка поиска: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def yadisk_recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /yadisk_recent - последние файлы на Яндекс.Диске"""
    try:
        from yandex_disk_helper import get_recent_files, format_file_size, get_file_type
        from datetime import datetime
        
        await update.message.reply_text("⏳ Получаю последние файлы...")
        
        files = await get_recent_files(limit=20)
        
        if not files:
            await update.message.reply_text("❌ Файлов не найдено")
            return
        
        text = f"🕐 *Последние файлы* (топ-{len(files)})\n\n"
        
        for i, file in enumerate(files, 1):
            name = file.get("name", "")
            size = format_file_size(file.get("size", 0))
            modified = file.get("modified", "")
            file_type = get_file_type(name)
            
            type_emoji = {
                'document': '📝',
                'spreadsheet': '📊',
                'presentation': '📈',
                'image': '🖼',
                'archive': '📦',
                'code': '💻',
                'other': '📄'
            }.get(file_type, '📄')
            
            # Форматируем дату
            try:
                dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                date_str = dt.strftime("%d.%m.%Y %H:%M")
            except:
                date_str = modified
            
            # Обрезаем длинные имена
            display_name = name[:30] + "..." if len(name) > 30 else name
            
            text += f"{i}. {type_emoji} {display_name}\n"
            text += f"   {size} • {date_str}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка получения файлов: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /myid - показать Telegram ID пользователя"""
    try:
        user = update.message.from_user
        user_id = user.id
        username = user.username or "не указан"
        first_name = user.first_name or "не указано"
        last_name = user.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        
        text = f"🆔 *Ваш Telegram ID*\n\n"
        text += f"*ID:* `{user_id}`\n"
        text += f"*Имя:* {full_name}\n"
        text += f"*Username:* @{username}\n\n"
        text += f"💡 *Использование:*\n"
        text += f"Добавьте этот ID в `.env`:\n"
        text += f"```\nTELEGRAM_ADMIN_IDS=5305427956,{user_id}\n```\n\n"
        text += f"Или используйте для настройки уведомлений о почте."
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        log.info(f"🆔 Пользователь {user_id} (@{username}) запросил свой ID")
        
    except Exception as e:
        log.error(f"❌ Ошибка получения ID: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /unsubscribe - отписаться от уведомлений о почте"""
    try:
        user_id = update.message.from_user.id
        username = update.message.from_user.username or "без username"
        
        # Удаляем пользователя из подписчиков
        remove_email_subscriber(user_id)
        
        text = "❌ *Вы отписаны от уведомлений о почте*\n\n"
        text += "Вы больше не будете получать уведомления о новых письмах.\n\n"
        text += "Чтобы снова подписаться, используйте команду /start"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        log.info(f"❌ Пользователь {user_id} (@{username}) отписался от уведомлений")
        
    except Exception as e:
        log.error(f"❌ Ошибка отписки: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def email_check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /email_check - проверка новых писем с уведомлениями"""
    try:
        from email_helper import check_new_emails

        await update.message.reply_text("⏳ Проверяю самое новое письмо...")

        # Проверяем только самое новое письмо (limit=1 для скорости)
        emails = await check_new_emails(since_days=1, limit=1)
        
        if emails:
            # Берем только самое новое письмо (первое в списке)
            email_data = emails[0]
            email_id = email_data.get("id", "")
            
            # Проверяем, не обрабатывали ли уже это письмо
            if email_id and email_id not in processed_email_ids:
                # Отправляем уведомление только о самом новом письме
                await send_email_notification(app.bot, email_data)
                processed_email_ids.add(email_id)
                
                await update.message.reply_text(
                    f"✅ *Найдено новое письмо*\n\n"
                    f"*Тема:* {email_data.get('subject', 'Без темы')}\n"
                    f"*От:* {email_data.get('from', 'Неизвестно')}\n\n"
                    f"Уведомление отправлено всем подписчикам.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"📧 *Самое новое письмо уже обработано*\n\n"
                    f"*Тема:* {email_data.get('subject', 'Без темы')}\n\n"
                    f"Используйте кнопки в уведомлениях для работы с письмами.",
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text("📧 Новых писем нет или email недоступен")
    except Exception as e:
        log.error(f"❌ Ошибка проверки email: {e}")
        import traceback
        log.error(traceback.format_exc())
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

# ===================== EMAIL NOTIFICATIONS =====================

# Кэш для хранения данных писем
email_cache: Dict[str, Dict] = {}

async def send_email_notification(bot, email_data: Dict):
    """
    Отправить уведомление о новом письме администратору с интерактивными кнопками
    
    Args:
        bot: Telegram Bot instance
        email_data: Словарь с данными письма
    """
    try:
        from_addr = email_data.get("from", "Неизвестно")
        subject = email_data.get("subject", "Без темы")
        body = email_data.get("body", "")
        date = email_data.get("date", "")
        email_id = email_data.get("id", "")
        
        # Обрезаем тело письма для отображения
        body_preview = body[:500] + "..." if len(body) > 500 else body
        
        # Формируем текст уведомления
        text = f"📧 *Новое письмо*\n\n"
        text += f"*От:* {from_addr}\n"
        text += f"*Тема:* {subject}\n"
        text += f"*Дата:* {date}\n\n"
        text += f"*Содержимое:*\n{body_preview}\n\n"
        text += f"Что сделать с этим письмом?"
        
        # Сохраняем полные данные письма
        email_cache[email_id] = email_data
        
        # Создаем интерактивные кнопки
        keyboard = [
            [
                InlineKeyboardButton("📝 Подготовить ответ", callback_data=f"email_reply_{email_id}"),
                InlineKeyboardButton("📄 Создать КП", callback_data=f"email_proposal_{email_id}")
            ],
            [
                InlineKeyboardButton("📧 Ответить на письмо", callback_data=f"email_send_reply_{email_id}"),
                InlineKeyboardButton("📋 Создать задачу в WEEEK", callback_data=f"email_task_{email_id}")
            ],
            [
                InlineKeyboardButton("✅ Обработано", callback_data=f"email_done_{email_id}"),
                InlineKeyboardButton("📧 Показать полный текст", callback_data=f"email_full_{email_id}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем уведомление всем подписчикам (всем пользователям бота)
        subscribers = get_email_subscribers()
        sent_count = 0
        failed_count = 0
        
        for user_id in subscribers:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                sent_count += 1
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                # Не логируем ошибки "Chat not found" для пользователей, которые заблокировали бота
                if "chat not found" not in error_msg.lower() and "blocked" not in error_msg.lower():
                    log.warning(f"⚠️ Не удалось отправить уведомление пользователю {user_id}: {e}")
        
        if sent_count > 0:
            log.info(f"✅ Уведомление о письме отправлено {sent_count} пользователю(ам): {subject}")
            if failed_count > 0:
                log.info(f"⚠️ Не удалось отправить {failed_count} уведомлений (возможно, пользователи заблокировали бота)")
        else:
            log.error(f"❌ Не удалось отправить уведомление ни одному пользователю: {subject}")
        
    except Exception as e:
        log.error(f"❌ Ошибка отправки уведомления о письме: {e}")
        import traceback
        log.error(traceback.format_exc())

async def email_monitor_task(bot):
    """
    Фоновая задача для мониторинга новых писем
    
    Args:
        bot: Telegram Bot instance
    """
    global processed_email_ids
    
    log.info(f"📧 Запуск мониторинга почты (интервал: {email_check_interval} сек)")
    
    while True:
        try:
            from email_helper import check_new_emails
            
            # Проверяем только самое новое письмо (limit=1 для скорости)
            emails = await check_new_emails(since_days=1, limit=1)
            
            if emails:
                # Берем только самое новое письмо (первое в списке)
                email_data = emails[0]
                email_id = email_data.get("id", "")
                
                # Проверяем, не обрабатывали ли уже это письмо
                if email_id and email_id not in processed_email_ids:
                    # Отправляем уведомление только о самом новом письме
                    await send_email_notification(bot, email_data)
                    processed_email_ids.add(email_id)
                    log.info(f"📧 Новое письмо обнаружено: {email_data.get('subject', 'Без темы')}")
            
            # Ждем перед следующей проверкой
            await asyncio.sleep(email_check_interval)
            
        except Exception as e:
            log.error(f"❌ Ошибка в мониторинге почты: {e}")
            import traceback
            log.error(traceback.format_exc())
            # При ошибке ждем перед следующей попыткой
            await asyncio.sleep(email_check_interval)

# ===================== EMAIL ACTION HANDLERS =====================

async def handle_email_reply_last(query: CallbackQuery):
    """Обработка кнопки 'Ответить на последний мейл' - получает последнее письмо и предлагает ответить"""
    try:
        await query.answer("⏳ Получаю последнее письмо...")
        
        from email_helper import check_new_emails
        
        # Получаем последнее письмо
        emails = await check_new_emails(since_days=7, limit=1)
        
        if not emails:
            await query.edit_message_text(
                "❌ *Писем не найдено*\n\n"
                "За последние 7 дней новых писем не обнаружено.",
                parse_mode='Markdown'
            )
            return
        
        # Берем самое новое письмо (первое в списке)
        email_data = emails[0]
        email_id = email_data.get("id", "")
        from_addr = email_data.get("from", "")
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        date = email_data.get("date", "")
        
        # Сохраняем в кэш для дальнейшей работы
        if email_id:
            email_cache[email_id] = email_data
        
        # Формируем тему ответа (Re:)
        reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject
        
        # Сохраняем данные для отправки в глобальный словарь
        user_id = query.from_user.id
        email_reply_state[user_id] = {
            'email_id': email_id,
            'to': from_addr,
            'subject': reply_subject,
            'original_subject': subject
        }
        
        # Показываем информацию о письме и предлагаем ответить
        text = f"📧 *Последнее письмо*\n\n"
        text += f"*От:* {from_addr}\n"
        text += f"*Тема:* {subject}\n"
        text += f"*Дата:* {date}\n\n"
        
        # Показываем первые 300 символов письма
        body_preview = body[:300] + "..." if len(body) > 300 else body
        text += f"*Содержимое:*\n{body_preview}\n\n"
        text += "💬 *Введите текст ответа:*\n\n"
        text += "💡 Вы можете отправить текст ответа прямо в следующем сообщении.\n"
        text += "Или используйте /cancel для отмены."
        
        keyboard = [
            [InlineKeyboardButton("📧 Показать полный текст", callback_data=f"email_full_{email_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        log.info(f"📧 Пользователь {user_id} запросил ответ на последнее письмо: {subject}")
        
    except Exception as e:
        log.error(f"❌ Ошибка получения последнего письма: {e}")
        import traceback
        log.error(traceback.format_exc())
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        await query.edit_message_text(
            f"❌ *Ошибка*\n\nНе удалось получить последнее письмо.\n\n"
            f"Ошибка: {str(e)}",
            parse_mode='Markdown'
        )

async def handle_email_reply(query: CallbackQuery, email_id: str):
    """Обработка кнопки 'Подготовить ответ' для письма"""
    try:
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        from lead_processor import generate_proposal
        
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        from_addr = email_data.get("from", "")
        
        # Формируем запрос для генерации ответа
        request_text = f"{subject}\n\n{body[:500]}"
        
        await query.answer("⏳ Готовлю ответ...")
        
        # Генерируем ответ
        draft = await generate_proposal(request_text, lead_contact={"email": from_addr})
        
        # Убираем Markdown
        import re
        draft_clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', draft)
        draft_clean = re.sub(r'\*([^*]+)\*', r'\1', draft_clean)
        draft_clean = re.sub(r'###+\s*', '', draft_clean)
        draft_clean = re.sub(r'##+\s*', '', draft_clean)
        draft_clean = re.sub(r'#+\s*', '', draft_clean)
        
        text = f"📧 *Черновик ответа на письмо:*\n\n"
        text += f"*От:* {from_addr}\n"
        text += f"*Тема:* {subject}\n\n"
        text += f"{draft_clean}\n\n"
        text += "💡 Отредактируйте и отправьте через почтовый клиент."
        
        await query.edit_message_text(text, parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка подготовки ответа: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

async def handle_email_proposal(query: CallbackQuery, email_id: str):
    """Обработка кнопки 'Создать КП' для письма"""
    try:
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        from lead_processor import generate_proposal
        
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        from_addr = email_data.get("from", "")
        
        # Извлекаем запрос из письма
        request_text = f"{subject}\n\n{body}"
        
        await query.answer("⏳ Генерирую КП...")
        
        # Генерируем КП
        proposal = await generate_proposal(request_text, lead_contact={"email": from_addr})
        
        # Убираем Markdown
        import re
        proposal_clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', proposal)
        proposal_clean = re.sub(r'\*([^*]+)\*', r'\1', proposal_clean)
        proposal_clean = re.sub(r'###+\s*', '', proposal_clean)
        proposal_clean = re.sub(r'##+\s*', '', proposal_clean)
        proposal_clean = re.sub(r'#+\s*', '', proposal_clean)
        
        text = f"📄 *Коммерческое предложение*\n\n"
        text += f"*Для:* {from_addr}\n"
        text += f"*Запрос:* {subject}\n\n"
        text += f"{proposal_clean}\n\n"
        text += "💡 Отредактируйте и отправьте клиенту."
        
        # Разбиваем на части если длинное
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            await query.edit_message_text(parts[0], parse_mode='Markdown')
            for part in parts[1:]:
                await query.message.reply_text(part)
        else:
            await query.edit_message_text(text, parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка генерации КП: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

async def handle_email_task(query: CallbackQuery, email_id: str):
    """Обработка кнопки 'Создать задачу в WEEEK' для письма"""
    try:
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        subject = email_data.get("subject", "")
        from_addr = email_data.get("from", "")
        
        # Показываем меню выбора проекта
        from weeek_helper import get_projects
        
        projects = await get_projects()
        if not projects:
            await query.answer("❌ Нет доступных проектов в WEEEK", show_alert=True)
            return
        
        keyboard = []
        for project in projects[:10]:  # Топ-10 проектов
            project_id = project.get('id')
            project_title = project.get('title', 'Без названия')
            keyboard.append([
                InlineKeyboardButton(
                    f"📋 {project_title}",
                    callback_data=f"email_task_create_{email_id}_{project_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=f"email_cancel_{email_id}")])
        
        text = f"📋 *Создать задачу в WEEEK*\n\n"
        text += f"*Письмо:* {subject}\n"
        text += f"*От:* {from_addr}\n\n"
        text += f"Выберите проект:"
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        log.error(f"❌ Ошибка создания задачи: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

async def handle_email_done(query: CallbackQuery, email_id: str):
    """Обработка кнопки 'Обработано' для письма"""
    try:
        await query.answer("✅ Письмо отмечено как обработанное")
        await query.edit_message_text(
            "✅ Письмо обработано",
            reply_markup=None
        )
        log.info(f"✅ Письмо {email_id} отмечено как обработанное")
    except Exception as e:
        log.error(f"❌ Ошибка: {e}")

async def handle_email_full(query: CallbackQuery, email_id: str):
    """Обработка кнопки 'Показать полный текст' для письма"""
    try:
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        from_addr = email_data.get("from", "")
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        date = email_data.get("date", "")
        
        text = f"📧 *Полный текст письма*\n\n"
        text += f"*От:* {from_addr}\n"
        text += f"*Тема:* {subject}\n"
        text += f"*Дата:* {date}\n\n"
        text += f"*Содержимое:*\n{body}"
        
        # Разбиваем на части если длинное
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            await query.edit_message_text(parts[0], parse_mode='Markdown')
            for part in parts[1:]:
                await query.message.reply_text(part)
        else:
            await query.edit_message_text(text, parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка показа полного текста: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

async def handle_email_create_task(query: CallbackQuery, email_id: str, project_id: int):
    """Создание задачи в WEEEK из письма"""
    try:
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        from weeek_helper import create_task, get_project
        
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        from_addr = email_data.get("from", "")
        
        # Формируем название задачи из темы письма
        task_name = f"Ответить на: {subject[:50]}" if subject else "Обработать письмо"
        
        # Формируем описание задачи
        task_description = f"Письмо от: {from_addr}\n\nТема: {subject}\n\n{body[:500]}"
        
        await query.answer("⏳ Создаю задачу...")
        
        # Создаем задачу
        task = await create_task(
            name=task_name,
            description=task_description,
            project_id=project_id
        )
        
        if task:
            project = await get_project(project_id)
            project_title = project.get('title', 'Проект') if project else 'Проект'
            
            text = f"✅ *Задача создана в WEEEK*\n\n"
            text += f"*Проект:* {project_title}\n"
            text += f"*Задача:* {task_name}\n"
            text += f"*ID задачи:* {task.get('id', 'N/A')}\n\n"
            text += f"Письмо: {subject}"
            
            await query.edit_message_text(text, parse_mode='Markdown')
            log.info(f"✅ Задача создана из письма {email_id} в проект {project_id}")
        else:
            await query.answer("❌ Не удалось создать задачу", show_alert=True)
        
    except Exception as e:
        log.error(f"❌ Ошибка создания задачи из письма: {e}")
        import traceback
        log.error(traceback.format_exc())
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

async def handle_email_send_reply(query: CallbackQuery, email_id: str):
    """Обработка кнопки 'Ответить на письмо' - запрос текста ответа"""
    try:
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        from_addr = email_data.get("from", "")
        subject = email_data.get("subject", "")
        original_subject = subject
        
        # Формируем тему ответа (Re:)
        reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject
        
        # Сохраняем данные для отправки в глобальный словарь
        user_id = query.from_user.id
        email_reply_state[user_id] = {
            'email_id': email_id,
            'to': from_addr,
            'subject': reply_subject,
            'original_subject': original_subject
        }
        
        text = f"📧 *Ответить на письмо*\n\n"
        text += f"*Кому:* {from_addr}\n"
        text += f"*Тема:* {reply_subject}\n\n"
        text += "💬 *Введите текст ответа:*\n\n"
        text += "💡 Вы можете отправить текст ответа прямо в следующем сообщении.\n"
        text += "Или используйте /cancel для отмены."
        
        await query.answer("💬 Введите текст ответа")
        await query.edit_message_text(text, parse_mode='Markdown')
        
    except Exception as e:
        log.error(f"❌ Ошибка при запросе текста ответа: {e}")
        import traceback
        log.error(traceback.format_exc())
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

async def handle_email_cancel(query: CallbackQuery, email_id: str):
    """Отмена действия с письмом"""
    try:
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        # Возвращаемся к исходному уведомлению
        from_addr = email_data.get("from", "")
        subject = email_data.get("subject", "Без темы")
        body = email_data.get("body", "")
        date = email_data.get("date", "")
        
        body_preview = body[:500] + "..." if len(body) > 500 else body
        
        text = f"📧 *Новое письмо*\n\n"
        text += f"*От:* {from_addr}\n"
        text += f"*Тема:* {subject}\n"
        text += f"*Дата:* {date}\n\n"
        text += f"*Содержимое:*\n{body_preview}\n\n"
        text += f"Что сделать с этим письмом?"
        
        keyboard = [
            [
                InlineKeyboardButton("📝 Подготовить ответ", callback_data=f"email_reply_{email_id}"),
                InlineKeyboardButton("📄 Создать КП", callback_data=f"email_proposal_{email_id}")
            ],
            [
                InlineKeyboardButton("📧 Ответить на письмо", callback_data=f"email_send_reply_{email_id}"),
                InlineKeyboardButton("📋 Создать задачу в WEEEK", callback_data=f"email_task_{email_id}")
            ],
            [
                InlineKeyboardButton("✅ Обработано", callback_data=f"email_done_{email_id}"),
                InlineKeyboardButton("📧 Показать полный текст", callback_data=f"email_full_{email_id}")
            ]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        log.error(f"❌ Ошибка отмены: {e}")

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
            if project_name.lower() in project.get("title", "").lower():
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
        
        # Отправляем статус (без Markdown для избежания ошибок с названиями файлов)
        status_msg = await update.message.reply_text(
            f"⏳ Загружаю документ: {file_name}\n"
            f"Размер: {document.file_size / 1024:.1f} КБ"
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
            f"⏳ Обрабатываю документ: {file_name}\n"
            f"Извлекаю текст и создаю чанки..."
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
            f"Индексирую чанки в Qdrant Cloud..."
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
                f"✅ Документ загружен в базу знаний!\n\n"
                f"📄 Файл: {file_name}\n"
                f"📊 Создано чанков: {result['chunks_count']}\n"
                f"🆔 ID документа: {result['doc_id']}\n\n"
                f"Теперь вы можете задавать вопросы по этому документу:\n"
                f"• Просто напишите вопрос в чате\n"
                f"• Или используйте /rag_search [запрос]"
            )
            log.info(f"✅ Документ {file_name} успешно загружен (ID: {result['doc_id']})")
        else:
            await status_msg.edit_text(
                f"❌ Ошибка загрузки документа:\n{result['error']}"
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
        from qdrant_helper import generate_embedding_async
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
        # Обрабатываем чанки батчами для ускорения
        from qdrant_client.models import PointStruct
        
        points = []
        batch_size = 10  # Обрабатываем по 10 чанков за раз
        
        for batch_start in range(0, len(documents), batch_size):
            batch_end = min(batch_start + batch_size, len(documents))
            batch_docs = documents[batch_start:batch_end]
            
            log.info(f"📊 Обрабатываю чанки {batch_start + 1}-{batch_end} из {len(documents)}")
            
            # Генерируем эмбеддинги для батча
            batch_tasks = []
            for doc in batch_docs:
                batch_tasks.append(generate_embedding_async(doc["text"]))
            
            # Ждем все эмбеддинги батча параллельно
            batch_embeddings = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Создаем точки для батча
            for doc, embedding in zip(batch_docs, batch_embeddings):
                if isinstance(embedding, Exception) or embedding is None:
                    log.warning(f"⚠️ Не удалось получить эмбеддинг для чанка {doc['id']}")
                    continue
                
                # Создаем числовой ID из hash строки
                point_id = abs(hash(doc["id"])) % (10 ** 10)
                
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": doc["text"],
                        "source": doc["metadata"]["source"],
                        "doc_id": doc["metadata"]["doc_id"],
                        "chunk_index": doc["metadata"]["chunk_index"],
                        "uploaded_by": doc["metadata"]["uploaded_by"],
                        "user_id": doc["metadata"]["user_id"],
                        "category": doc["metadata"]["category"],
                        "title": doc["metadata"]["title"],
                        "chunk_id": doc["id"]  # Сохраняем строковый ID в payload
                    }
                )
                points.append(point)
            
            log.info(f"✅ Обработано {len(batch_embeddings)} эмбеддингов в батче")
        
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
    app.add_handler(CommandHandler("weeek_info", weeek_info_command))
    app.add_handler(CommandHandler("weeek_task", weeek_create_task_command))
    app.add_handler(CommandHandler("weeek_projects", weeek_projects_command))
    app.add_handler(CommandHandler("weeek_create_project", weeek_create_project_command))
    app.add_handler(CommandHandler("weeek_update", weeek_update_command))
    app.add_handler(CommandHandler("weeek_tasks", weeek_tasks_command))

    # Yandex Disk commands
    app.add_handler(CommandHandler("yadisk_list", yadisk_list_command))
    app.add_handler(CommandHandler("yadisk_search", yadisk_search_command))
    app.add_handler(CommandHandler("yadisk_recent", yadisk_recent_command))
    
    # Utility commands
    app.add_handler(CommandHandler("myid", myid_command))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    
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
            
            # Запускаем фоновую задачу мониторинга почты
            try:
                asyncio.create_task(email_monitor_task(app.bot))
                log.info("✅ Фоновая задача мониторинга почты запущена")
            except Exception as e:
                log.warning(f"⚠️ Не удалось запустить мониторинг почты: {e}")
            
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
            
            # Запускаем фоновую задачу мониторинга почты
            try:
                asyncio.create_task(email_monitor_task(app.bot))
                log.info("✅ Фоновая задача мониторинга почты запущена")
            except Exception as e:
                log.warning(f"⚠️ Не удалось запустить мониторинг почты: {e}")
            
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
