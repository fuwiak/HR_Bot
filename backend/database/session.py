"""
Управление сессиями базы данных
"""
import os
import logging
from typing import Optional, Generator
from contextlib import contextmanager

log = logging.getLogger(__name__)

DATABASE_AVAILABLE = False

try:
    import psycopg2
    from psycopg2 import pool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    log.warning("psycopg2 не установлен")


class DatabaseSession:
    """Менеджер сессий базы данных"""
    
    _pool: Optional[pool.ThreadedConnectionPool] = None
    _initialized: bool = False
    
    @classmethod
    def get_database_url(cls) -> str:
        """Получить URL базы данных"""
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url
        
        pg_host = os.getenv("PGHOST")
        pg_port = os.getenv("PGPORT", "5432")
        pg_database = os.getenv("PGDATABASE", "railway")
        pg_user = os.getenv("PGUSER", "postgres")
        pg_password = os.getenv("PGPASSWORD", "")
        
        if pg_host and pg_password:
            return f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
        
        return ""
    
    @classmethod
    def init_pool(cls, min_conn: int = 1, max_conn: int = 10) -> bool:
        """Инициализация пула соединений"""
        global DATABASE_AVAILABLE
        
        if not PSYCOPG2_AVAILABLE:
            log.warning("psycopg2 не установлен, БД недоступна")
            return False
        
        if cls._initialized and cls._pool:
            return True
        
        database_url = cls.get_database_url()
        if not database_url:
            log.warning("DATABASE_URL не настроен")
            return False
        
        try:
            cls._pool = pool.ThreadedConnectionPool(
                min_conn,
                max_conn,
                database_url
            )
            cls._initialized = True
            DATABASE_AVAILABLE = True
            log.info("✅ Пул соединений PostgreSQL инициализирован")
            return True
        except Exception as e:
            log.error(f"❌ Ошибка инициализации пула: {e}")
            return False
    
    @classmethod
    def get_connection(cls):
        """Получить соединение из пула"""
        if not cls._initialized or not cls._pool:
            cls.init_pool()
        
        if cls._pool:
            return cls._pool.getconn()
        return None
    
    @classmethod
    def return_connection(cls, conn):
        """Вернуть соединение в пул"""
        if cls._pool and conn:
            cls._pool.putconn(conn)
    
    @classmethod
    def close_all(cls):
        """Закрыть все соединения"""
        if cls._pool:
            cls._pool.closeall()
            cls._pool = None
            cls._initialized = False
            log.info("Все соединения PostgreSQL закрыты")


@contextmanager
def get_db_session() -> Generator:
    """Контекстный менеджер для работы с БД"""
    conn = DatabaseSession.get_connection()
    if not conn:
        yield None
        return
    
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        log.error(f"❌ Ошибка БД: {e}")
        raise
    finally:
        DatabaseSession.return_connection(conn)


def init_db() -> bool:
    """Инициализация базы данных"""
    return DatabaseSession.init_pool()
