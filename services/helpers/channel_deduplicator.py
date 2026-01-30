"""
Механизм предотвращения дубликатов в канале HRAI_ANovoselova_Leads
Отслеживает уже отправленные сообщения и предотвращает повторную отправку
"""
import hashlib
import logging
from typing import Dict, Set, Optional
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

# Глобальное хранилище отправленных сообщений
# В production можно использовать Redis или БД
_sent_messages: Set[str] = set()
_message_hashes: Set[str] = set()  # Хеши содержимого для обнаружения похожих сообщений

# Максимальное количество хранимых ID (для предотвращения утечки памяти)
MAX_STORED_IDS = 10000


def generate_message_id(lead_info: Dict) -> str:
    """
    Генерирует уникальный ID для сообщения на основе его содержимого
    
    Args:
        lead_info: Словарь с информацией о лиде
    
    Returns:
        Уникальный строковый идентификатор
    """
    source = lead_info.get("source", "unknown")
    title = lead_info.get("title", "")
    client_email = lead_info.get("client_email", "")
    client_phone = lead_info.get("client_phone", "")
    message = lead_info.get("message", "")
    
    # Используем комбинацию источника и уникальных идентификаторов
    # Если есть email или phone, используем их как уникальный идентификатор
    if client_email:
        unique_id = f"{source}:{client_email}:{title}"
    elif client_phone:
        unique_id = f"{source}:{client_phone}:{title}"
    else:
        # Если нет уникальных идентификаторов, используем хеш содержимого
        content = f"{source}:{title}:{message[:200]}"
        unique_id = f"{source}:{hashlib.md5(content.encode()).hexdigest()[:16]}"
    
    return unique_id


def generate_content_hash(lead_info: Dict) -> str:
    """
    Генерирует хеш содержимого сообщения для обнаружения похожих сообщений
    
    Args:
        lead_info: Словарь с информацией о лиде
    
    Returns:
        MD5 хеш содержимого
    """
    # Нормализуем содержимое (убираем пробелы, приводим к нижнему регистру)
    source = lead_info.get("source", "").lower().strip()
    title = lead_info.get("title", "").lower().strip()
    message = lead_info.get("message", "").lower().strip()[:500]  # Первые 500 символов
    
    # Создаем хеш из нормализованного содержимого (включая источник)
    # Это позволяет различать одинаковое содержимое из разных источников
    content = f"{source}:{title}:{message}"
    content_hash = hashlib.md5(content.encode()).hexdigest()
    
    return content_hash


def is_duplicate(lead_info: Dict, check_content: bool = True) -> tuple[bool, Optional[str]]:
    """
    Проверяет, является ли сообщение дубликатом
    
    Args:
        lead_info: Словарь с информацией о лиде
        check_content: Проверять ли похожесть содержимого (по умолчанию True)
    
    Returns:
        Кортеж (is_duplicate, reason):
        - is_duplicate: True если это дубликат
        - reason: Причина (если это дубликат)
    """
    # Генерируем ID сообщения
    message_id = generate_message_id(lead_info)
    
    # Проверяем по ID
    if message_id in _sent_messages:
        return True, f"Сообщение с ID '{message_id}' уже было отправлено"
    
    # Проверяем по хешу содержимого (если включено)
    if check_content:
        content_hash = generate_content_hash(lead_info)
        if content_hash in _message_hashes:
            return True, f"Похожее сообщение уже было отправлено (хеш: {content_hash[:8]}...)"
    
    return False, None


def mark_as_sent(lead_info: Dict):
    """
    Помечает сообщение как отправленное
    
    Args:
        lead_info: Словарь с информацией о лиде
    """
    message_id = generate_message_id(lead_info)
    content_hash = generate_content_hash(lead_info)
    
    # Добавляем в хранилище
    _sent_messages.add(message_id)
    _message_hashes.add(content_hash)
    
    # Очищаем старые записи, если превышен лимит
    if len(_sent_messages) > MAX_STORED_IDS:
        # Удаляем первые 1000 записей (FIFO)
        items_to_remove = list(_sent_messages)[:1000]
        for item in items_to_remove:
            _sent_messages.discard(item)
    
    if len(_message_hashes) > MAX_STORED_IDS:
        items_to_remove = list(_message_hashes)[:1000]
        for item in items_to_remove:
            _message_hashes.discard(item)
    
    log.debug(f"✅ Сообщение помечено как отправленное: {message_id[:50]}...")


def clear_old_entries(days: int = 7):
    """
    Очищает старые записи (для периодической очистки)
    
    Args:
        days: Количество дней для хранения записей
    """
    # В текущей реализации (in-memory) очистка происходит автоматически
    # при превышении лимита. В production с Redis/БД можно добавить TTL
    log.info(f"🧹 Очистка старых записей (старше {days} дней)")
    # Пока просто логируем, в будущем можно добавить реальную очистку


def get_stats() -> Dict:
    """
    Возвращает статистику по отправленным сообщениям
    
    Returns:
        Словарь со статистикой
    """
    return {
        "total_sent": len(_sent_messages),
        "total_hashes": len(_message_hashes),
        "max_stored": MAX_STORED_IDS
    }


def reset():
    """
    Сбрасывает все записи (для тестирования)
    """
    global _sent_messages, _message_hashes
    _sent_messages.clear()
    _message_hashes.clear()
    log.warning("⚠️ Все записи о отправленных сообщениях сброшены")
