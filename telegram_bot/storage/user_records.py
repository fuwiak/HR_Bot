"""
Модуль для работы с записями пользователей
"""
import logging
from collections import defaultdict
from typing import Dict, List

log = logging.getLogger(__name__)

# Fallback хранилище в памяти
UserRecords: Dict[int, List[Dict]] = defaultdict(list)

# Попытка импорта PostgreSQL модуля
try:
    from backend.database import (
        add_user_record as db_add_user_record,
        get_user_records as db_get_user_records,
        delete_user_record as db_delete_user_record,
    )
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    log.warning(f"⚠️ PostgreSQL модуль не доступен: {e}")
    def db_add_user_record(*args, **kwargs): return False
    def db_get_user_records(*args, **kwargs): return []
    def db_delete_user_record(*args, **kwargs): return False


def format_user_record(record: Dict) -> str:
    """Форматирует запись пользователя для отображения"""
    try:
        services = record.get("services", [])
        staff = record.get("staff", {})
        company = record.get("company", {})
        
        text = f"📅 *{record.get('date', 'Неизвестно')}*\n"
        text += f"⏰ {record.get('datetime', 'Неизвестно')}\n"
        text += f"👤 HR-специалист: *{staff.get('name', 'Неизвестно')}*\n"
        text += f"🏢 {company.get('title', 'HR-отдел')}\n"
        
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
    """Получить записи пользователя (PostgreSQL или RAM)"""
    return get_user_records_list(user_id)


def add_user_record(user_id: int, record: Dict):
    """Добавить запись пользователя (PostgreSQL или RAM)"""
    if DATABASE_AVAILABLE:
        if db_add_user_record(user_id, record):
            return
        # Fallback на память если PostgreSQL недоступен
    UserRecords[user_id].append(record)


def remove_user_record(user_id: int, record_id: int):
    """Удалить запись пользователя (PostgreSQL или RAM)"""
    if DATABASE_AVAILABLE:
        if db_delete_user_record(record_id):
            return
        # Fallback на память если PostgreSQL недоступен
    UserRecords[user_id] = [r for r in UserRecords[user_id] if r.get("id") != record_id]


def get_user_records_list(user_id: int) -> List[Dict]:
    """Получить список записей пользователя (PostgreSQL или RAM)"""
    if DATABASE_AVAILABLE:
        records = db_get_user_records(user_id)
        if records:
            return records
        # Fallback на память если PostgreSQL недоступен
    return UserRecords.get(user_id, [])
