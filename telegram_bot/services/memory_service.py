"""
Сервис для работы с памятью пользователей (история чата)
"""
import logging
from collections import defaultdict, deque
from typing import Dict, Deque

log = logging.getLogger(__name__)

# Fallback хранилище в памяти (используется если PostgreSQL недоступен)
MEMORY_TURNS = 6
UserMemory: Dict[int, Deque] = defaultdict(lambda: deque(maxlen=MEMORY_TURNS * 2))

# Попытка импорта PostgreSQL модуля
try:
    from backend.database import (
        add_memory as db_add_memory,
        get_history as db_get_history,
        get_recent_history as db_get_recent_history,
    )
    DATABASE_AVAILABLE = True
    log.info("✅ PostgreSQL модуль загружен для memory_service")
except ImportError as e:
    DATABASE_AVAILABLE = False
    log.warning(f"⚠️ PostgreSQL модуль не доступен, используем память: {e}")
    def db_add_memory(*args, **kwargs): return False
    def db_get_history(*args, **kwargs): return ""
    def db_get_recent_history(*args, **kwargs): return ""

# Попытка импорта Redis модуля
try:
    from services.helpers.redis_helper import (
        add_memory_redis,
        get_history_redis,
        get_recent_history_redis,
        REDIS_AVAILABLE
    )
    REDIS_AVAILABLE_IMPORT = REDIS_AVAILABLE
    if REDIS_AVAILABLE_IMPORT:
        log.info("✅ Redis модуль загружен для memory_service")
except ImportError as e:
    REDIS_AVAILABLE_IMPORT = False
    log.warning(f"⚠️ Redis модуль не доступен: {e}")
    def add_memory_redis(*args, **kwargs): return False
    def get_history_redis(*args, **kwargs): return ""
    def get_recent_history_redis(*args, **kwargs): return ""


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
    """Получить недавнюю историю (Redis -> PostgreSQL -> RAM)"""
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
