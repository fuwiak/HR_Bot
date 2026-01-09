"""
Модуль для работы с Redis - быстрый доступ к данным конверсации
Используется как кэш перед PostgreSQL для ускорения чтения
"""
import os
import logging
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Попытка импорта redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("⚠️ redis не установлен. Установите: pip install redis")

# Переменные окружения для подключения к Redis
REDIS_URL = os.getenv("REDIS_URL") or os.getenv("REDIS_PUBLIC_URL")
REDIS_HOST = os.getenv("REDISHOST") or os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDISPORT") or os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDISPASSWORD") or os.getenv("REDIS_PASSWORD")
REDIS_USER = os.getenv("REDISUSER") or os.getenv("REDIS_USER", "default")

# Глобальный Redis клиент
_redis_client = None

# TTL для ключей в Redis (в секундах)
REDIS_TTL = int(os.getenv("REDIS_TTL", "3600"))  # 1 час по умолчанию


def get_redis_client():
    """Получить Redis клиент"""
    global _redis_client
    
    if not REDIS_AVAILABLE:
        logger.warning("⚠️ Redis библиотека не доступна")
        return None
    
    if _redis_client is not None:
        return _redis_client
    
    try:
        # Логируем доступные переменные окружения (без паролей)
        logger.debug(f"🔍 Проверка Redis переменных: REDIS_URL={'установлен' if REDIS_URL else 'не установлен'}, "
                    f"REDIS_HOST={REDIS_HOST if REDIS_HOST != 'localhost' else 'не установлен'}, "
                    f"REDIS_PORT={REDIS_PORT}, REDIS_PASSWORD={'установлен' if REDIS_PASSWORD else 'не установлен'}")
        
        # Если есть REDIS_URL, используем его (приоритет)
        if REDIS_URL:
            try:
                _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
                logger.info(f"✅ Redis клиент создан через REDIS_URL")
                # Проверяем подключение
                _redis_client.ping()
                logger.info("✅ Redis подключение успешно через REDIS_URL")
                return _redis_client
            except Exception as e:
                logger.error(f"❌ Ошибка подключения через REDIS_URL: {e}")
                _redis_client = None
        
        # Иначе используем отдельные параметры
        if REDIS_HOST and REDIS_HOST != "localhost":
            try:
                # Создаем подключение с паролем или без (в зависимости от наличия)
                connection_params = {
                    "host": REDIS_HOST,
                    "port": REDIS_PORT,
                    "username": REDIS_USER,
                    "decode_responses": True
                }
                if REDIS_PASSWORD:
                    connection_params["password"] = REDIS_PASSWORD
                
                _redis_client = redis.Redis(**connection_params)
                logger.info(f"✅ Redis клиент создан: {REDIS_HOST}:{REDIS_PORT} (user: {REDIS_USER})")
                # Проверяем подключение
                _redis_client.ping()
                logger.info("✅ Redis подключение успешно через отдельные параметры")
                return _redis_client
            except Exception as e:
                logger.error(f"❌ Ошибка подключения через отдельные параметры: {e}")
                _redis_client = None
        
        # Если ничего не сработало
        logger.warning("⚠️ Redis переменные окружения не установлены или подключение не удалось. "
                      "Используем только PostgreSQL (медленнее). "
                      "Для добавления Redis на Railway: Dashboard → '+ New' → 'Database' → 'Add Redis'")
        return None
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка создания Redis клиента: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


# ===================== USER MEMORY (История чатов) =====================

def add_memory_redis(user_id: int, role: str, text: str) -> bool:
    """Добавить сообщение в Redis (быстрое кэширование)"""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        key = f"user_memory:{user_id}"
        
        # Получаем текущие сообщения
        messages_json = client.get(key)
        if messages_json:
            messages = json.loads(messages_json)
        else:
            messages = []
        
        # Добавляем новое сообщение
        messages.append({
            "role": role,
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
        
        # Ограничиваем количество сообщений (последние 50)
        if len(messages) > 50:
            messages = messages[-50:]
        
        # Сохраняем обратно в Redis с TTL
        client.setex(key, REDIS_TTL, json.dumps(messages))
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка добавления в Redis: {e}")
        return False


def get_history_redis(user_id: int, limit: int = 12) -> str:
    """Получить историю из Redis (быстрое чтение)"""
    client = get_redis_client()
    if not client:
        return ""
    
    try:
        key = f"user_memory:{user_id}"
        messages_json = client.get(key)
        
        if not messages_json:
            return ""
        
        messages = json.loads(messages_json)
        # Берем последние limit сообщений
        recent_messages = messages[-limit:] if len(messages) > limit else messages
        
        return "\n".join([f"{msg['role']}: {msg['text']}" for msg in recent_messages])
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения истории из Redis: {e}")
        return ""


def get_recent_history_redis(user_id: int, limit: int = 50) -> str:
    """Получить недавнюю историю из Redis"""
    return get_history_redis(user_id, limit)


# ===================== USER DATA =====================

def get_user_phone_redis(user_id: int) -> Optional[str]:
    """Получить телефон пользователя из Redis"""
    client = get_redis_client()
    if not client:
        return None
    
    try:
        key = f"user_data:{user_id}:phone"
        return client.get(key)
    except Exception as e:
        logger.error(f"❌ Ошибка получения телефона из Redis: {e}")
        return None


def set_user_phone_redis(user_id: int, phone: str) -> bool:
    """Установить телефон пользователя в Redis"""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        key = f"user_data:{user_id}:phone"
        client.setex(key, REDIS_TTL, phone)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка установки телефона в Redis: {e}")
        return False


def get_user_booking_data_redis(user_id: int) -> Optional[Dict]:
    """Получить данные для записи из Redis"""
    client = get_redis_client()
    if not client:
        return None
    
    try:
        key = f"user_data:{user_id}:booking"
        data_json = client.get(key)
        if data_json:
            return json.loads(data_json)
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка получения данных записи из Redis: {e}")
        return None


def set_user_booking_data_redis(user_id: int, booking_data: Dict) -> bool:
    """Установить данные для записи в Redis"""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        key = f"user_data:{user_id}:booking"
        client.setex(key, REDIS_TTL, json.dumps(booking_data))
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка установки данных записи в Redis: {e}")
        return False


# ===================== EMAIL SUBSCRIBERS =====================

def get_email_subscribers_redis() -> List[int]:
    """Получить список подписчиков из Redis"""
    client = get_redis_client()
    if not client:
        return []
    
    try:
        key = "email_subscribers"
        subscribers_json = client.get(key)
        if subscribers_json:
            return json.loads(subscribers_json)
        return []
    except Exception as e:
        logger.error(f"❌ Ошибка получения подписчиков из Redis: {e}")
        return []


def add_email_subscriber_redis(user_id: int) -> bool:
    """Добавить подписчика в Redis"""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        key = "email_subscribers"
        subscribers = get_email_subscribers_redis()
        if user_id not in subscribers:
            subscribers.append(user_id)
            client.setex(key, REDIS_TTL * 24, json.dumps(subscribers))  # 24 часа TTL
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления подписчика в Redis: {e}")
        return False


def remove_email_subscriber_redis(user_id: int) -> bool:
    """Удалить подписчика из Redis"""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        key = "email_subscribers"
        subscribers = get_email_subscribers_redis()
        if user_id in subscribers:
            subscribers.remove(user_id)
            client.setex(key, REDIS_TTL * 24, json.dumps(subscribers))
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка удаления подписчика из Redis: {e}")
        return False


# ===================== SYNCHRONIZATION TO POSTGRESQL =====================

def sync_memory_to_postgres(user_id: int) -> bool:
    """Синхронизировать память пользователя из Redis в PostgreSQL"""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        from database import add_memory as db_add_memory
        
        key = f"user_memory:{user_id}"
        messages_json = client.get(key)
        
        if not messages_json:
            return True  # Нет данных для синхронизации
        
        messages = json.loads(messages_json)
        
        # Синхронизируем каждое сообщение в PostgreSQL
        synced_count = 0
        for msg in messages:
            if db_add_memory(user_id, msg['role'], msg['text']):
                synced_count += 1
        
        if synced_count > 0:
            logger.info(f"✅ Синхронизировано {synced_count} сообщений пользователя {user_id} в PostgreSQL")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка синхронизации памяти в PostgreSQL: {e}")
        return False


def sync_user_data_to_postgres(user_id: int) -> bool:
    """Синхронизировать данные пользователя из Redis в PostgreSQL"""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        from database import (
            set_user_phone as db_set_user_phone,
            set_user_booking_data as db_set_user_booking_data
        )
        
        # Синхронизируем телефон
        phone = get_user_phone_redis(user_id)
        if phone:
            db_set_user_phone(user_id, phone)
        
        # Синхронизируем данные записи
        booking_data = get_user_booking_data_redis(user_id)
        if booking_data:
            db_set_user_booking_data(user_id, booking_data)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка синхронизации данных пользователя в PostgreSQL: {e}")
        return False


def sync_email_subscribers_to_postgres() -> bool:
    """Синхронизировать подписчиков из Redis в PostgreSQL"""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        from database import add_email_subscriber as db_add_email_subscriber
        
        subscribers = get_email_subscribers_redis()
        
        synced_count = 0
        for user_id in subscribers:
            if db_add_email_subscriber(user_id):
                synced_count += 1
        
        if synced_count > 0:
            logger.info(f"✅ Синхронизировано {synced_count} подписчиков в PostgreSQL")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка синхронизации подписчиков в PostgreSQL: {e}")
        return False


# ===================== BACKGROUND SYNC TASK =====================

def sync_all_to_postgres():
    """Синхронизировать все данные из Redis в PostgreSQL (фоновая задача)"""
    client = get_redis_client()
    if not client:
        return
    
    try:
        # Находим все ключи пользователей
        user_keys = client.keys("user_memory:*")
        
        synced_users = 0
        for key in user_keys:
            # Извлекаем user_id из ключа
            user_id_str = key.replace("user_memory:", "")
            try:
                user_id = int(user_id_str)
                if sync_memory_to_postgres(user_id):
                    synced_users += 1
                sync_user_data_to_postgres(user_id)
            except ValueError:
                continue
        
        # Синхронизируем подписчиков
        sync_email_subscribers_to_postgres()
        
        logger.info(f"✅ Фоновая синхронизация завершена: {synced_users} пользователей")
        
    except Exception as e:
        logger.error(f"❌ Ошибка фоновой синхронизации: {e}")


def clear_user_memory_redis(user_id: int) -> bool:
    """Очистить память пользователя в Redis"""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        key = f"user_memory:{user_id}"
        client.delete(key)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка очистки памяти в Redis: {e}")
        return False
