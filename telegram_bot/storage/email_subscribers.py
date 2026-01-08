"""
Модуль для работы с подписчиками на email уведомления
"""
import os
import json
import logging

from telegram_bot.config import EMAIL_SUBSCRIBERS_FILE, ADMIN_USER_IDS

log = logging.getLogger(__name__)

# Попытка импорта PostgreSQL модуля
try:
    from backend.database import (
        get_email_subscribers as db_get_email_subscribers,
        add_email_subscriber as db_add_email_subscriber,
        remove_email_subscriber as db_remove_email_subscriber,
    )
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    log.warning(f"⚠️ PostgreSQL модуль не доступен: {e}")
    def db_get_email_subscribers(*args, **kwargs): return []
    def db_add_email_subscriber(*args, **kwargs): return False
    def db_remove_email_subscriber(*args, **kwargs): return False

# Попытка импорта Redis модуля
try:
    from services.helpers.redis_helper import (
        get_email_subscribers_redis,
        add_email_subscriber_redis,
        remove_email_subscriber_redis,
        REDIS_AVAILABLE
    )
    REDIS_AVAILABLE_IMPORT = REDIS_AVAILABLE
except ImportError as e:
    REDIS_AVAILABLE_IMPORT = False
    log.warning(f"⚠️ Redis модуль не доступен: {e}")
    def get_email_subscribers_redis(*args, **kwargs): return []
    def add_email_subscriber_redis(*args, **kwargs): return False
    def remove_email_subscriber_redis(*args, **kwargs): return False


def load_email_subscribers() -> set:
    """Загрузить список подписчиков (PostgreSQL или файл)"""
    if DATABASE_AVAILABLE:
        return set(db_get_email_subscribers())
    # Fallback на файл
    try:
        if os.path.exists(EMAIL_SUBSCRIBERS_FILE):
            with open(EMAIL_SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('subscribers', []))
    except Exception as e:
        log.warning(f"⚠️ Ошибка загрузки подписчиков: {e}")
    return set()


def save_email_subscribers(subscribers: set):
    """Сохранить список подписчиков (PostgreSQL или файл)"""
    if DATABASE_AVAILABLE:
        # В PostgreSQL подписчики сохраняются автоматически через add_email_subscriber
        return
    # Fallback на файл
    try:
        data = {'subscribers': list(subscribers)}
        with open(EMAIL_SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.error(f"❌ Ошибка сохранения подписчиков: {e}")


def add_email_subscriber(user_id: int):
    """Добавить пользователя в список подписчиков (Redis -> PostgreSQL -> файл)"""
    # 1. Сохраняем в Redis (быстрое кэширование)
    if REDIS_AVAILABLE_IMPORT:
        add_email_subscriber_redis(user_id)
    # 2. Сохраняем в PostgreSQL (постоянное хранилище)
    if DATABASE_AVAILABLE:
        if db_add_email_subscriber(user_id):
            log.info(f"✅ Пользователь {user_id} подписан на уведомления о почте (PostgreSQL)")
            return
    # 3. Fallback на файл
    subscribers = load_email_subscribers()
    subscribers.add(user_id)
    save_email_subscribers(subscribers)
    log.info(f"✅ Пользователь {user_id} подписан на уведомления о почте")


def remove_email_subscriber(user_id: int):
    """Удалить пользователя из списка подписчиков (Redis -> PostgreSQL -> файл)"""
    # 1. Удаляем из Redis
    if REDIS_AVAILABLE_IMPORT:
        remove_email_subscriber_redis(user_id)
    # 2. Удаляем из PostgreSQL
    if DATABASE_AVAILABLE:
        if db_remove_email_subscriber(user_id):
            log.info(f"❌ Пользователь {user_id} отписан от уведомлений о почте (PostgreSQL)")
            return
    # 3. Fallback на файл
    subscribers = load_email_subscribers()
    subscribers.discard(user_id)
    save_email_subscribers(subscribers)
    log.info(f"❌ Пользователь {user_id} отписан от уведомлений о почте")


def get_email_subscribers() -> set:
    """Получить список всех подписчиков (Redis -> PostgreSQL -> файл)"""
    subscribers = set()
    # 1. Пытаемся получить из Redis (быстрое чтение)
    if REDIS_AVAILABLE_IMPORT:
        subscribers = set(get_email_subscribers_redis())
    # 2. Если нет в Redis, пытаемся получить из PostgreSQL
    if not subscribers and DATABASE_AVAILABLE:
        subscribers = set(db_get_email_subscribers())
    # 3. Fallback на файл
    if not subscribers:
        subscribers = load_email_subscribers()
    # Всегда добавляем администраторов
    subscribers.update(ADMIN_USER_IDS)
    return subscribers
