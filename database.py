"""
Модуль для работы с PostgreSQL базой данных
Используется для хранения истории чатов, данных пользователей и записей
"""
import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Попытка импорта psycopg2 (PostgreSQL драйвер)
try:
    import psycopg2
    from psycopg2 import pool, sql
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logger.warning("⚠️ psycopg2 не установлен. Установите: pip install psycopg2-binary")

# Переменные окружения для подключения к PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")
PGHOST = os.getenv("PGHOST")
PGPORT = os.getenv("PGPORT", "5432")
PGDATABASE = os.getenv("PGDATABASE")
PGUSER = os.getenv("PGUSER")
PGPASSWORD = os.getenv("PGPASSWORD")

# Глобальный connection pool
_connection_pool = None


def get_connection_pool():
    """Получить connection pool для PostgreSQL"""
    global _connection_pool
    
    if not PSYCOPG2_AVAILABLE:
        logger.error("❌ psycopg2 не доступен")
        return None
    
    if _connection_pool is not None:
        return _connection_pool
    
    try:
        # Если есть DATABASE_URL, используем его
        if DATABASE_URL:
            _connection_pool = pool.SimpleConnectionPool(
                1, 20, DATABASE_URL
            )
            logger.info("✅ PostgreSQL connection pool создан через DATABASE_URL")
        # Иначе используем отдельные параметры
        elif PGHOST and PGDATABASE and PGUSER and PGPASSWORD:
            _connection_pool = pool.SimpleConnectionPool(
                1, 20,
                host=PGHOST,
                port=PGPORT,
                database=PGDATABASE,
                user=PGUSER,
                password=PGPASSWORD
            )
            logger.info(f"✅ PostgreSQL connection pool создан: {PGHOST}:{PGPORT}/{PGDATABASE}")
        else:
            logger.warning("⚠️ PostgreSQL переменные окружения не установлены")
            return None
        
        return _connection_pool
    except Exception as e:
        logger.error(f"❌ Ошибка создания connection pool: {e}")
        return None


def get_connection():
    """Получить соединение с базой данных"""
    pool = get_connection_pool()
    if not pool:
        return None
    
    try:
        return pool.getconn()
    except Exception as e:
        logger.error(f"❌ Ошибка получения соединения: {e}")
        return None


def return_connection(conn):
    """Вернуть соединение в pool"""
    pool = get_connection_pool()
    if pool and conn:
        try:
            pool.putconn(conn)
        except Exception as e:
            logger.error(f"❌ Ошибка возврата соединения: {e}")


def init_database():
    """Инициализировать базу данных (создать таблицы если их нет)"""
    conn = get_connection()
    if not conn:
        logger.warning("⚠️ Не удалось подключиться к PostgreSQL, используем память")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Таблица для истории чатов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_memory (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                role VARCHAR(20) NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Создаем индексы отдельно
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_memory_user_id ON user_memory(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_memory_created_at ON user_memory(created_at)")
        
        # Таблица для записей пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_records (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                booking_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_records_user_id ON user_records(user_id)")
        
        # Таблица для данных авторизации
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_auth (
                user_id BIGINT PRIMARY KEY,
                auth_data JSONB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица для дополнительных данных пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_data (
                user_id BIGINT PRIMARY KEY,
                phone VARCHAR(50),
                weeek_workspace VARCHAR(255),
                booking_data JSONB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица для подписчиков на email уведомления
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_subscribers (
                user_id BIGINT PRIMARY KEY,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        logger.info("✅ Таблицы базы данных созданы/проверены")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        return_connection(conn)


# ===================== USER MEMORY (История чатов) =====================

def add_memory(user_id: int, role: str, text: str) -> bool:
    """Добавить сообщение в историю пользователя"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_memory (user_id, role, text) VALUES (%s, %s, %s)",
            (user_id, role, text)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления в память: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        return_connection(conn)


def get_history(user_id: int, limit: int = 12) -> str:
    """Получить историю чата пользователя"""
    conn = get_connection()
    if not conn:
        return ""
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, text 
            FROM user_memory 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """, (user_id, limit))
        
        messages = cursor.fetchall()
        # Обращаем порядок (от старых к новым)
        messages.reverse()
        
        return "\n".join([f"{role}: {text}" for role, text in messages])
    except Exception as e:
        logger.error(f"❌ Ошибка получения истории: {e}")
        return ""
    finally:
        cursor.close()
        return_connection(conn)


def get_recent_history(user_id: int, limit: int = 50) -> str:
    """Получить недавнюю историю (для парсинга записей)"""
    return get_history(user_id, limit)


def clear_user_memory(user_id: int) -> bool:
    """Очистить историю пользователя"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_memory WHERE user_id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка очистки памяти: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        return_connection(conn)


# ===================== USER RECORDS (Записи) =====================

def add_user_record(user_id: int, booking_data: Dict) -> bool:
    """Добавить запись пользователя"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_records (user_id, booking_data) VALUES (%s, %s)",
            (user_id, json.dumps(booking_data))
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления записи: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        return_connection(conn)


def get_user_records(user_id: int) -> List[Dict]:
    """Получить записи пользователя"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, booking_data, created_at 
            FROM user_records 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """, (user_id,))
        
        records = []
        for row in cursor.fetchall():
            record = dict(row)
            if isinstance(record['booking_data'], str):
                record['booking_data'] = json.loads(record['booking_data'])
            records.append(record)
        
        return records
    except Exception as e:
        logger.error(f"❌ Ошибка получения записей: {e}")
        return []
    finally:
        cursor.close()
        return_connection(conn)


def delete_user_record(record_id: int) -> bool:
    """Удалить запись по ID"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_records WHERE id = %s", (record_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"❌ Ошибка удаления записи: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        return_connection(conn)


# ===================== USER DATA (Дополнительные данные) =====================

def get_user_phone(user_id: int) -> Optional[str]:
    """Получить телефон пользователя"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT phone FROM user_data WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"❌ Ошибка получения телефона: {e}")
        return None
    finally:
        cursor.close()
        return_connection(conn)


def set_user_phone(user_id: int, phone: str) -> bool:
    """Установить телефон пользователя"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_data (user_id, phone, updated_at) 
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) 
            DO UPDATE SET phone = %s, updated_at = CURRENT_TIMESTAMP
        """, (user_id, phone, phone))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка установки телефона: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        return_connection(conn)


def get_user_booking_data(user_id: int) -> Optional[Dict]:
    """Получить данные для записи пользователя"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT booking_data FROM user_data WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        if result and result[0]:
            if isinstance(result[0], str):
                return json.loads(result[0])
            return result[0]
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка получения данных записи: {e}")
        return None
    finally:
        cursor.close()
        return_connection(conn)


def set_user_booking_data(user_id: int, booking_data: Dict) -> bool:
    """Установить данные для записи пользователя"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_data (user_id, booking_data, updated_at) 
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) 
            DO UPDATE SET booking_data = %s, updated_at = CURRENT_TIMESTAMP
        """, (user_id, json.dumps(booking_data), json.dumps(booking_data)))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка установки данных записи: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        return_connection(conn)


def get_user_weeek_workspace(user_id: int) -> Optional[str]:
    """Получить WEEEK workspace ID пользователя"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT weeek_workspace FROM user_data WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"❌ Ошибка получения WEEEK workspace: {e}")
        return None
    finally:
        cursor.close()
        return_connection(conn)


def set_user_weeek_workspace(user_id: int, workspace_id: str) -> bool:
    """Установить WEEEK workspace ID пользователя"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_data (user_id, weeek_workspace, updated_at) 
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) 
            DO UPDATE SET weeek_workspace = %s, updated_at = CURRENT_TIMESTAMP
        """, (user_id, workspace_id, workspace_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка установки WEEEK workspace: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        return_connection(conn)


# ===================== EMAIL SUBSCRIBERS =====================

def get_email_subscribers() -> List[int]:
    """Получить список подписчиков на email уведомления"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM email_subscribers")
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"❌ Ошибка получения подписчиков: {e}")
        return []
    finally:
        cursor.close()
        return_connection(conn)


def add_email_subscriber(user_id: int) -> bool:
    """Добавить подписчика на email уведомления"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO email_subscribers (user_id) 
            VALUES (%s)
            ON CONFLICT (user_id) DO NOTHING
        """, (user_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления подписчика: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        return_connection(conn)


def remove_email_subscriber(user_id: int) -> bool:
    """Удалить подписчика на email уведомления"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM email_subscribers WHERE user_id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка удаления подписчика: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        return_connection(conn)


# ===================== USER AUTH =====================

def get_user_auth(user_id: int) -> Optional[Dict]:
    """Получить данные авторизации пользователя"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT auth_data FROM user_auth WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        if result and result[0]:
            if isinstance(result[0], str):
                return json.loads(result[0])
            return result[0]
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка получения данных авторизации: {e}")
        return None
    finally:
        cursor.close()
        return_connection(conn)


def set_user_auth(user_id: int, auth_data: Dict) -> bool:
    """Установить данные авторизации пользователя"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_auth (user_id, auth_data, updated_at) 
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) 
            DO UPDATE SET auth_data = %s, updated_at = CURRENT_TIMESTAMP
        """, (user_id, json.dumps(auth_data), json.dumps(auth_data)))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка установки данных авторизации: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        return_connection(conn)
