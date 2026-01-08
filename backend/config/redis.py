"""
Конфигурация Redis
"""
import os
from typing import Optional
from functools import lru_cache
import logging

log = logging.getLogger(__name__)


class RedisConfig:
    """Конфигурация Redis"""
    
    def __init__(self):
        self.url: str = os.getenv("REDIS_URL", "")
        self.host: str = os.getenv("REDISHOST", os.getenv("REDIS_HOST", "localhost"))
        self.port: int = int(os.getenv("REDISPORT", os.getenv("REDIS_PORT", "6379")))
        self.password: Optional[str] = os.getenv("REDISPASSWORD", os.getenv("REDIS_PASSWORD"))
        self.user: str = os.getenv("REDISUSER", "default")
        self.db: int = int(os.getenv("REDIS_DB", "0"))
        
        # Настройки пула соединений
        self.max_connections: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
        self.socket_timeout: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
        self.socket_connect_timeout: int = int(os.getenv("REDIS_CONNECT_TIMEOUT", "5"))
        
        # TTL настройки
        self.memory_ttl: int = int(os.getenv("REDIS_MEMORY_TTL", "86400"))  # 24 часа
        self.session_ttl: int = int(os.getenv("REDIS_SESSION_TTL", "3600"))  # 1 час
    
    def get_url(self) -> str:
        """Получить URL для подключения"""
        if self.url:
            return self.url
        
        if self.password:
            return f"redis://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
        
        return f"redis://{self.host}:{self.port}/{self.db}"
    
    def get_connection_params(self) -> dict:
        """Получить параметры для подключения"""
        params = {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "socket_timeout": self.socket_timeout,
            "socket_connect_timeout": self.socket_connect_timeout,
            "max_connections": self.max_connections,
            "decode_responses": True
        }
        
        if self.password:
            params["password"] = self.password
        
        return params
    
    def is_available(self) -> bool:
        """Проверить доступность Redis"""
        try:
            import redis
            client = redis.Redis(**self.get_connection_params())
            client.ping()
            return True
        except Exception as e:
            log.warning(f"Redis недоступен: {e}")
            return False


@lru_cache()
def get_redis_config() -> RedisConfig:
    """Получить конфигурацию Redis (синглтон)"""
    return RedisConfig()
