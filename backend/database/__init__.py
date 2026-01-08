"""
Модуль работы с базой данных
"""
from .session import get_db_session, init_db, DATABASE_AVAILABLE

# Импортируем функции из старого модуля database.py для обратной совместимости
try:
    # Используем абсолютный импорт для избежания циклических зависимостей
    import sys
    import importlib.util
    from pathlib import Path
    
    # Путь к backend.database (старый модуль)
    database_py_path = Path(__file__).parent.parent / "database.py"
    if database_py_path.exists():
        spec = importlib.util.spec_from_file_location("backend.database_legacy", database_py_path)
        database_legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(database_legacy)
        
        # Экспортируем функции
        add_memory = database_legacy.add_memory
        get_history = database_legacy.get_history
        get_recent_history = database_legacy.get_recent_history
        clear_user_memory = database_legacy.clear_user_memory
        add_user_record = database_legacy.add_user_record
        get_user_records = database_legacy.get_user_records
        delete_user_record = database_legacy.delete_user_record
        get_user_phone = database_legacy.get_user_phone
        set_user_phone = database_legacy.set_user_phone
        get_user_booking_data = database_legacy.get_user_booking_data
        set_user_booking_data = database_legacy.set_user_booking_data
        get_user_weeek_workspace = database_legacy.get_user_weeek_workspace
        set_user_weeek_workspace = database_legacy.set_user_weeek_workspace
        get_email_subscribers = database_legacy.get_email_subscribers
        add_email_subscriber = database_legacy.add_email_subscriber
        remove_email_subscriber = database_legacy.remove_email_subscriber
        get_user_auth = database_legacy.get_user_auth
        set_user_auth = database_legacy.set_user_auth
    else:
        raise ImportError("backend.database.py not found")
except (ImportError, AttributeError) as e:
    # Если старый модуль недоступен, создаем заглушки
    def add_memory(*args, **kwargs): return False
    def get_history(*args, **kwargs): return ""
    def get_recent_history(*args, **kwargs): return ""
    def clear_user_memory(*args, **kwargs): return False
    def add_user_record(*args, **kwargs): return False
    def get_user_records(*args, **kwargs): return []
    def delete_user_record(*args, **kwargs): return False
    def get_user_phone(*args, **kwargs): return None
    def set_user_phone(*args, **kwargs): return False
    def get_user_booking_data(*args, **kwargs): return {}
    def set_user_booking_data(*args, **kwargs): return False
    def get_user_weeek_workspace(*args, **kwargs): return None
    def set_user_weeek_workspace(*args, **kwargs): return False
    def get_email_subscribers(*args, **kwargs): return []
    def add_email_subscriber(*args, **kwargs): return False
    def remove_email_subscriber(*args, **kwargs): return False
    def get_user_auth(*args, **kwargs): return None
    def set_user_auth(*args, **kwargs): return False

__all__ = [
    'get_db_session', 
    'init_db', 
    'DATABASE_AVAILABLE',
    'add_memory',
    'get_history',
    'get_recent_history',
    'clear_user_memory',
    'add_user_record',
    'get_user_records',
    'delete_user_record',
    'get_user_phone',
    'set_user_phone',
    'get_user_booking_data',
    'set_user_booking_data',
    'get_user_weeek_workspace',
    'set_user_weeek_workspace',
    'get_email_subscribers',
    'add_email_subscriber',
    'remove_email_subscriber',
    'get_user_auth',
    'set_user_auth'
]
