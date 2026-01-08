"""
Модуль для работы с пользовательскими данными (телефоны, данные записи, workspace)
"""
import logging
from typing import Dict

log = logging.getLogger(__name__)

# Fallback хранилище в памяти
UserPhone: Dict[int, str] = {}
UserBookingData: Dict[int, Dict] = {}
UserWeeekWorkspace: Dict[int, str] = {}
UserAuth: Dict[int, Dict] = {}

# Попытка импорта PostgreSQL модуля
try:
    from backend.database import (
        get_user_phone as db_get_user_phone,
        set_user_phone as db_set_user_phone,
        get_user_booking_data as db_get_user_booking_data,
        set_user_booking_data as db_set_user_booking_data,
        get_user_weeek_workspace as db_get_user_weeek_workspace,
        set_user_weeek_workspace as db_set_user_weeek_workspace,
        get_user_auth as db_get_user_auth,
        set_user_auth as db_set_user_auth
    )
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    log.warning(f"⚠️ PostgreSQL модуль не доступен: {e}")
    def db_get_user_phone(*args, **kwargs): return None
    def db_set_user_phone(*args, **kwargs): return False
    def db_get_user_booking_data(*args, **kwargs): return None
    def db_set_user_booking_data(*args, **kwargs): return False
    def db_get_user_weeek_workspace(*args, **kwargs): return None
    def db_set_user_weeek_workspace(*args, **kwargs): return False
    def db_get_user_auth(*args, **kwargs): return None
    def db_set_user_auth(*args, **kwargs): return False

# Попытка импорта Redis модуля
try:
    from services.helpers.redis_helper import (
        get_user_phone_redis,
        set_user_phone_redis,
        get_user_booking_data_redis,
        set_user_booking_data_redis,
        REDIS_AVAILABLE
    )
    REDIS_AVAILABLE_IMPORT = REDIS_AVAILABLE
except ImportError as e:
    REDIS_AVAILABLE_IMPORT = False
    log.warning(f"⚠️ Redis модуль не доступен: {e}")
    def get_user_phone_redis(*args, **kwargs): return None
    def set_user_phone_redis(*args, **kwargs): return False
    def get_user_booking_data_redis(*args, **kwargs): return None
    def set_user_booking_data_redis(*args, **kwargs): return False


def get_user_phone(user_id: int) -> str:
    """Получить номер телефона пользователя (Redis -> PostgreSQL -> RAM)"""
    # 1. Пытаемся получить из Redis
    if REDIS_AVAILABLE_IMPORT:
        phone = get_user_phone_redis(user_id)
        if phone:
            return phone
    # 2. Пытаемся получить из PostgreSQL
    if DATABASE_AVAILABLE:
        phone = db_get_user_phone(user_id)
        if phone:
            return phone
    # 3. Fallback на память
    return UserPhone.get(user_id, "")


def set_user_phone(user_id: int, phone: str):
    """Установить номер телефона пользователя (Redis -> PostgreSQL -> RAM)"""
    # 1. Сохраняем в Redis
    if REDIS_AVAILABLE_IMPORT:
        set_user_phone_redis(user_id, phone)
    # 2. Сохраняем в PostgreSQL
    if DATABASE_AVAILABLE:
        db_set_user_phone(user_id, phone)
    # 3. Fallback на память
    UserPhone[user_id] = phone


def get_user_booking_data(user_id: int) -> Dict:
    """Получить данные записи пользователя (Redis -> PostgreSQL -> RAM)"""
    # 1. Пытаемся получить из Redis
    if REDIS_AVAILABLE_IMPORT:
        data = get_user_booking_data_redis(user_id)
        if data:
            return data
    # 2. Пытаемся получить из PostgreSQL
    if DATABASE_AVAILABLE:
        data = db_get_user_booking_data(user_id)
        if data:
            return data
    # 3. Fallback на память
    return UserBookingData.get(user_id)


def set_user_booking_data(user_id: int, data: Dict):
    """Установить данные записи пользователя (Redis -> PostgreSQL -> RAM)"""
    # 1. Сохраняем в Redis
    if REDIS_AVAILABLE_IMPORT:
        set_user_booking_data_redis(user_id, data)
    # 2. Сохраняем в PostgreSQL
    if DATABASE_AVAILABLE:
        db_set_user_booking_data(user_id, data)
    # 3. Fallback на память
    UserBookingData[user_id] = data


def get_user_weeek_workspace(user_id: int) -> str:
    """Получить WEEEK workspace ID пользователя (PostgreSQL -> RAM)"""
    if DATABASE_AVAILABLE:
        workspace = db_get_user_weeek_workspace(user_id)
        if workspace:
            return workspace
    return UserWeeekWorkspace.get(user_id)


def set_user_weeek_workspace(user_id: int, workspace: str):
    """Установить WEEEK workspace ID пользователя (PostgreSQL -> RAM)"""
    if DATABASE_AVAILABLE:
        db_set_user_weeek_workspace(user_id, workspace)
    UserWeeekWorkspace[user_id] = workspace


def get_user_auth(user_id: int) -> Dict:
    """Получить данные авторизации пользователя (PostgreSQL -> RAM)"""
    if DATABASE_AVAILABLE:
        auth = db_get_user_auth(user_id)
        if auth:
            return auth
    return UserAuth.get(user_id, {})


def set_user_auth(user_id: int, auth: Dict):
    """Установить данные авторизации пользователя (PostgreSQL -> RAM)"""
    if DATABASE_AVAILABLE:
        db_set_user_auth(user_id, auth)
    UserAuth[user_id] = auth
