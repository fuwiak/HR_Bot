"""
Базовый адаптер для мессенджеров
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

log = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """Абстрактный базовый класс для адаптеров мессенджеров"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self._initialized = False
    
    @abstractmethod
    async def send_message(self, user_id: str, text: str, **kwargs) -> bool:
        """Отправить сообщение пользователю"""
        pass
    
    @abstractmethod
    async def send_typing_action(self, user_id: str) -> bool:
        """Показать индикатор набора текста"""
        pass
    
    @abstractmethod
    async def handle_message(self, message: Dict[str, Any]) -> Optional[str]:
        """Обработать входящее сообщение"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Инициализация адаптера"""
        pass
    
    def is_initialized(self) -> bool:
        return self._initialized
