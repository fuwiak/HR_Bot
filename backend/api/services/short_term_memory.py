"""
Сервис краткосрочной памяти для хранения истории сообщений
Использует Redis -> PostgreSQL -> In-Memory fallback
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

log = logging.getLogger(__name__)

# In-memory хранилище (fallback)
_memory_store: Dict[str, List[Dict[str, Any]]] = defaultdict(list)


class ShortTermMemoryService:
    """Сервис краткосрочной памяти"""
    
    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self._redis_client = None
        self._redis_available = False
        self._init_redis()
    
    def _init_redis(self):
        """Инициализация Redis клиента"""
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "")
            if redis_url:
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
                self._redis_available = True
                log.info("✅ Redis подключен для краткосрочной памяти")
            else:
                redis_host = os.getenv("REDISHOST", os.getenv("REDIS_HOST", ""))
                redis_port = int(os.getenv("REDISPORT", os.getenv("REDIS_PORT", "6379")))
                redis_password = os.getenv("REDISPASSWORD", os.getenv("REDIS_PASSWORD", ""))
                
                if redis_host:
                    self._redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        password=redis_password if redis_password else None,
                        decode_responses=True
                    )
                    self._redis_client.ping()
                    self._redis_available = True
                    log.info("✅ Redis подключен для краткосрочной памяти")
        except Exception as e:
            log.warning(f"⚠️ Redis недоступен: {e}")
            self._redis_available = False
    
    def _get_key(self, user_id: str, platform: str) -> str:
        """Получить ключ для хранения"""
        return f"memory:{platform}:{user_id}"
    
    def add_message(
        self,
        user_id: str,
        platform: str,
        role: str,
        content: str
    ) -> bool:
        """Добавить сообщение в память"""
        try:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            key = self._get_key(user_id, platform)
            
            # Пробуем Redis
            if self._redis_available and self._redis_client:
                try:
                    # Добавляем в список
                    self._redis_client.rpush(key, json.dumps(message))
                    # Обрезаем до max_messages
                    self._redis_client.ltrim(key, -self.max_messages, -1)
                    # Устанавливаем TTL (24 часа)
                    self._redis_client.expire(key, 86400)
                    return True
                except Exception as e:
                    log.warning(f"⚠️ Ошибка Redis: {e}")
            
            # Fallback на in-memory
            _memory_store[key].append(message)
            # Обрезаем
            if len(_memory_store[key]) > self.max_messages:
                _memory_store[key] = _memory_store[key][-self.max_messages:]
            
            return True
        except Exception as e:
            log.error(f"❌ Ошибка добавления сообщения: {e}")
            return False
    
    def get_messages(
        self,
        user_id: str,
        platform: str,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """Получить сообщения из памяти"""
        try:
            key = self._get_key(user_id, platform)
            limit = limit or self.max_messages
            
            # Пробуем Redis
            if self._redis_available and self._redis_client:
                try:
                    messages_raw = self._redis_client.lrange(key, -limit, -1)
                    messages = [json.loads(m) for m in messages_raw]
                    return messages
                except Exception as e:
                    log.warning(f"⚠️ Ошибка Redis: {e}")
            
            # Fallback на in-memory
            messages = _memory_store.get(key, [])
            return messages[-limit:] if limit else messages
        except Exception as e:
            log.error(f"❌ Ошибка получения сообщений: {e}")
            return []
    
    def clear_memory(self, user_id: str, platform: str) -> bool:
        """Очистить память пользователя"""
        try:
            key = self._get_key(user_id, platform)
            
            # Пробуем Redis
            if self._redis_available and self._redis_client:
                try:
                    self._redis_client.delete(key)
                except Exception as e:
                    log.warning(f"⚠️ Ошибка Redis: {e}")
            
            # Очищаем in-memory
            if key in _memory_store:
                del _memory_store[key]
            
            return True
        except Exception as e:
            log.error(f"❌ Ошибка очистки памяти: {e}")
            return False
    
    def get_history_text(self, user_id: str, platform: str, limit: int = 10) -> str:
        """Получить историю в текстовом формате"""
        messages = self.get_messages(user_id, platform, limit)
        
        if not messages:
            return ""
        
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            role_name = "Пользователь" if role == "user" else "Бот"
            lines.append(f"{role_name}: {content}")
        
        return "\n".join(lines)


# Глобальный экземпляр
_short_term_memory: Optional[ShortTermMemoryService] = None


def get_short_term_memory_service() -> ShortTermMemoryService:
    """Получить глобальный экземпляр сервиса памяти"""
    global _short_term_memory
    if _short_term_memory is None:
        _short_term_memory = ShortTermMemoryService()
    return _short_term_memory
