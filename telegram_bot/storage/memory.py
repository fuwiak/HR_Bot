"""
Модуль для работы с памятью пользователей (история чата)
"""
import logging
from collections import defaultdict, deque
from typing import Dict, Deque

from telegram_bot.config import MEMORY_TURNS

log = logging.getLogger(__name__)

# Fallback хранилище в памяти
UserMemory: Dict[int, Deque] = defaultdict(lambda: deque(maxlen=MEMORY_TURNS * 2))

# Попытка импорта PostgreSQL модуля
try:
    from backend.database import (
        add_memory as db_add_memory,
        get_history as db_get_history,
        get_recent_history as db_get_recent_history,
        clear_user_memory as db_clear_user_memory,
    )
    DATABASE_AVAILABLE = True
    log.info("✅ PostgreSQL модуль загружен")
except ImportError as e:
    DATABASE_AVAILABLE = False
    log.warning(f"⚠️ PostgreSQL модуль не доступен, используем память: {e}")
    def db_add_memory(*args, **kwargs): return False
    def db_get_history(*args, **kwargs): return ""
    def db_get_recent_history(*args, **kwargs): return ""
    def db_clear_user_memory(*args, **kwargs): return False

# Попытка импорта Redis модуля
try:
    from services.helpers.redis_helper import (
        add_memory_redis,
        get_history_redis,
        get_recent_history_redis,
        clear_user_memory_redis,
        REDIS_AVAILABLE
    )
    REDIS_AVAILABLE_IMPORT = REDIS_AVAILABLE
    if REDIS_AVAILABLE_IMPORT:
        log.info("✅ Redis модуль загружен")
except ImportError as e:
    REDIS_AVAILABLE_IMPORT = False
    log.warning(f"⚠️ Redis модуль не доступен: {e}")
    def add_memory_redis(*args, **kwargs): return False
    def get_history_redis(*args, **kwargs): return ""
    def get_recent_history_redis(*args, **kwargs): return ""
    def clear_user_memory_redis(*args, **kwargs): return False


def add_memory(user_id, role, text):
    """Добавить сообщение в память (Redis -> PostgreSQL -> RAM)"""
    # 1. Записываем в Redis (быстрое кэширование)
    if REDIS_AVAILABLE_IMPORT:
        add_memory_redis(user_id, role, text)
    
    # 2. Записываем в PostgreSQL (постоянное хранилище) - асинхронно
    if DATABASE_AVAILABLE:
        db_add_memory(user_id, role, text)
    
    # 3. Fallback на память если Redis и PostgreSQL недоступны
    if not REDIS_AVAILABLE_IMPORT and not DATABASE_AVAILABLE:
        UserMemory[user_id].append((role, text))


def get_history(user_id):
    """Получить историю чата (Redis -> PostgreSQL -> RAM)"""
    # 1. Пытаемся получить из Redis (быстрое чтение)
    if REDIS_AVAILABLE_IMPORT:
        history = get_history_redis(user_id)
        if history:
            return history
    
    # 2. Пытаемся получить из PostgreSQL
    if DATABASE_AVAILABLE:
        history = db_get_history(user_id)
        if history:
            return history
    
    # 3. Fallback на память
    return "\n".join([f"{r}: {t}" for r, t in UserMemory[user_id]])


def get_recent_history(user_id: int, limit: int = 50) -> str:
    """Получить недавнюю историю чата (Redis -> PostgreSQL -> RAM)"""
    # 1. Пытаемся получить из Redis (быстрое чтение)
    if REDIS_AVAILABLE_IMPORT:
        history = get_recent_history_redis(user_id, limit)
        if history:
            return history
    
    # 2. Пытаемся получить из PostgreSQL
    if DATABASE_AVAILABLE:
        history = db_get_recent_history(user_id, limit)
        if history:
            return history
    
    # 3. Fallback на память
    recent_messages = list(UserMemory[user_id])[-limit:]
    return "\n".join([f"{r}: {t}" for r, t in recent_messages])


def clear_user_memory(user_id: int):
    """Очистить память пользователя"""
    # 1. Очищаем Redis
    if REDIS_AVAILABLE_IMPORT:
        clear_user_memory_redis(user_id)
    
    # 2. Очищаем PostgreSQL
    if DATABASE_AVAILABLE:
        db_clear_user_memory(user_id)
    
    # 3. Очищаем память
    if user_id in UserMemory:
        UserMemory[user_id].clear()
