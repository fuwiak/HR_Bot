"""
Настройки приложения
"""
import os
from typing import Optional, List
from functools import lru_cache
import logging

log = logging.getLogger(__name__)


class Settings:
    """Настройки приложения"""
    
    def __init__(self):
        # Telegram
        self.telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.admin_user_ids: List[int] = self._parse_admin_ids()
        
        # Database
        self.database_url: str = os.getenv("DATABASE_URL", "")
        self.pg_host: str = os.getenv("PGHOST", "")
        self.pg_port: str = os.getenv("PGPORT", "5432")
        self.pg_database: str = os.getenv("PGDATABASE", "railway")
        self.pg_user: str = os.getenv("PGUSER", "postgres")
        self.pg_password: str = os.getenv("PGPASSWORD", "")
        
        # Redis
        self.redis_url: str = os.getenv("REDIS_URL", "")
        self.redis_host: str = os.getenv("REDISHOST", os.getenv("REDIS_HOST", ""))
        self.redis_port: int = int(os.getenv("REDISPORT", os.getenv("REDIS_PORT", "6379")))
        self.redis_password: str = os.getenv("REDISPASSWORD", os.getenv("REDIS_PASSWORD", ""))
        
        # Qdrant
        self.qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_api_key: Optional[str] = os.getenv("QDRANT_API_KEY")
        self.qdrant_host: str = os.getenv("QDRANT_HOST", "")
        self.qdrant_port: str = os.getenv("QDRANT_PORT", "6333")
        
        # LLM
        self.openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "")
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        
        # Google Sheets
        self.google_sheets_credentials: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "")
        self.google_spreadsheet_id: str = os.getenv("GOOGLE_SPREADSHEET_ID", "")
        
        # Email
        self.email_address: str = os.getenv("EMAIL_ADDRESS", "")
        self.email_password: str = os.getenv("EMAIL_PASSWORD", "")
        self.imap_server: str = os.getenv("IMAP_SERVER", "imap.yandex.ru")
        self.smtp_server: str = os.getenv("SMTP_SERVER", "smtp.yandex.ru")
        
        # WEEEK
        self.weeek_api_token: str = os.getenv("WEEEK_API_TOKEN", "")
        
        # Yandex Disk
        self.yandex_disk_token: str = os.getenv("YANDEX_DISK_TOKEN", "")
        
        # App settings
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.web_port: int = int(os.getenv("PORT", os.getenv("WEB_PORT", "8081")))
        
        # Railway
        self.railway_environment: str = os.getenv("RAILWAY_ENVIRONMENT", "")
        self.railway_private_domain: str = os.getenv("RAILWAY_PRIVATE_DOMAIN", "")
    
    def _parse_admin_ids(self) -> List[int]:
        """Парсинг списка админ ID"""
        admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
        if not admin_ids_str:
            return []
        
        try:
            return [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
        except ValueError:
            log.warning("Не удалось распарсить ADMIN_USER_IDS")
            return []
    
    def get_database_url(self) -> str:
        """Получить URL базы данных"""
        if self.database_url:
            return self.database_url
        
        if self.pg_host and self.pg_password:
            return f"postgresql://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_database}"
        
        return ""
    
    def get_redis_url(self) -> str:
        """Получить URL Redis"""
        if self.redis_url:
            return self.redis_url
        
        if self.redis_host:
            if self.redis_password:
                return f"redis://default:{self.redis_password}@{self.redis_host}:{self.redis_port}"
            return f"redis://{self.redis_host}:{self.redis_port}"
        
        return ""
    
    def get_qdrant_url(self) -> str:
        """Получить URL Qdrant"""
        # Приоритет: Railway -> Cloud -> локальный
        if self.qdrant_host:
            return f"http://{self.qdrant_host}:{self.qdrant_port}"
        
        if self.qdrant_api_key and self.qdrant_url:
            return self.qdrant_url
        
        return "http://localhost:6333"
    
    def is_production(self) -> bool:
        """Проверка на продакшен среду"""
        return bool(self.railway_environment) or not self.debug


@lru_cache()
def get_settings() -> Settings:
    """Получить настройки (синглтон)"""
    return Settings()
