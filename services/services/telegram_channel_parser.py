"""
Telegram Channel Parser Service
Сервис для парсинга сообщений из Telegram канала @HRTime_bot и извлечения данных о заказах
"""
import logging
from typing import Dict, List, Optional
import re

log = logging.getLogger()

# Импорты
try:
    from services.adapters.telegram_channel_adapter import TelegramChannelAdapter
    from services.adapters.hrtime_order_adapter import HRTimeOrderAdapter
    ADAPTER_AVAILABLE = True
except ImportError as e:
    ADAPTER_AVAILABLE = False
    log.warning(f"⚠️ Adapters недоступны: {e}")


class TelegramChannelParser:
    """Сервис для парсинга сообщений из Telegram канала"""
    
    def __init__(self):
        self.channel_adapter = None
        self.order_adapter = None
        
        if ADAPTER_AVAILABLE:
            try:
                self.channel_adapter = TelegramChannelAdapter()
                self.order_adapter = HRTimeOrderAdapter()
            except Exception as e:
                log.error(f"❌ Ошибка инициализации адаптеров: {e}")
    
    async def parse_channel_message(self, message: Dict) -> Optional[Dict]:
        """
        Парсит сообщение из канала и извлекает данные о заказе
        
        Args:
            message: Словарь с данными сообщения из канала
        
        Returns:
            Словарь с распарсенными данными заказа или None
        """
        if not message:
            return None
        
        try:
            message_text = message.get("text", "") or message.get("caption", "")
            if not message_text:
                return None
            
            log.info(f"🔍 [Channel Parser] Парсинг сообщения {message.get('message_id')}")
            
            # Используем LLM для парсинга сообщения из канала
            if self.order_adapter:
                # Формируем структуру данных для парсинга
                order_data = {
                    "title": self._extract_title(message_text),
                    "description": message_text,
                    "budget": self._extract_budget(message_text),
                    "deadline": self._extract_deadline(message_text),
                    "client": {
                        "name": self._extract_client_name(message_text),
                        "email": self._extract_email(message_text),
                        "phone": self._extract_phone(message_text)
                    },
                    "message_id": message.get("message_id"),
                    "date": message.get("date"),
                    "source": "telegram_channel"
                }
                
                # Парсим через LLM адаптер
                parsed = await self.order_adapter.parse_order(order_data)
                parsed["message_id"] = message.get("message_id")
                parsed["source"] = "telegram_channel"
                
                log.info(f"✅ [Channel Parser] Сообщение распарсено")
                return parsed
            else:
                # Базовый парсинг без LLM
                return self._basic_parse(message_text, message)
                
        except Exception as e:
            log.error(f"❌ [Channel Parser] Ошибка парсинга сообщения: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            return None
    
    def _extract_title(self, text: str) -> str:
        """Извлекает заголовок заказа из текста"""
        # Ищем заголовок в начале сообщения или после ключевых слов
        lines = text.split('\n')
        if lines:
            # Первая строка часто является заголовком
            first_line = lines[0].strip()
            if len(first_line) > 10 and len(first_line) < 200:
                return first_line
        
        # Ищем после ключевых слов
        patterns = [
            r'Заказ[:\s]+(.+?)(?:\n|$)',
            r'Название[:\s]+(.+?)(?:\n|$)',
            r'Тема[:\s]+(.+?)(?:\n|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Заказ из HR Time"
    
    def _extract_budget(self, text: str) -> Optional[str]:
        """Извлекает бюджет из текста"""
        patterns = [
            r'Бюджет[:\s]+([\d\s]+(?:\s*[руб|RUB|₽])?)',
            r'Стоимость[:\s]+([\d\s]+(?:\s*[руб|RUB|₽])?)',
            r'(\d+\s*(?:тыс|тысяч|руб|RUB|₽))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_deadline(self, text: str) -> Optional[str]:
        """Извлекает сроки из текста"""
        patterns = [
            r'Срок[:\s]+(.+?)(?:\n|$)',
            r'Дедлайн[:\s]+(.+?)(?:\n|$)',
            r'(\d{1,2}[./]\d{1,2}[./]\d{2,4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_client_name(self, text: str) -> str:
        """Извлекает имя клиента из текста"""
        patterns = [
            r'Клиент[:\s]+(.+?)(?:\n|$)',
            r'Заказчик[:\s]+(.+?)(?:\n|$)',
            r'Контакт[:\s]+(.+?)(?:\n|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Клиент"
    
    def _extract_email(self, text: str) -> str:
        """Извлекает email из текста"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        if match:
            return match.group(0)
        return ""
    
    def _extract_phone(self, text: str) -> str:
        """Извлекает телефон из текста"""
        phone_patterns = [
            r'\+?[7-8]?\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}',
            r'\+?\d{1,3}[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}',
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        
        return ""
    
    def _basic_parse(self, text: str, message: Dict) -> Dict:
        """Базовый парсинг без LLM"""
        return {
            "requirements": text,
            "budget": {
                "amount": 0.0,
                "currency": "RUB",
                "text": self._extract_budget(text) or ""
            },
            "deadline": {
                "date": None,
                "text": self._extract_deadline(text) or ""
            },
            "contacts": {
                "full_name": self._extract_client_name(text),
                "phone": self._extract_phone(text),
                "email": self._extract_email(text)
            },
            "raw_data": {
                "title": self._extract_title(text),
                "description": text,
                "message_id": message.get("message_id"),
                "date": message.get("date"),
                "source": "telegram_channel"
            },
            "message_id": message.get("message_id"),
            "source": "telegram_channel"
        }
    
    async def get_new_orders_from_channel(
        self,
        limit: int = 10,
        last_message_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Получить новые заказы из Telegram канала
        
        Args:
            limit: Максимальное количество заказов
            last_message_id: ID последнего обработанного сообщения
        
        Returns:
            Список распарсенных заказов
        """
        if not self.channel_adapter:
            log.warning("⚠️ [Channel Parser] Channel adapter недоступен")
            return []
        
        try:
            # Получаем сообщения из канала
            messages = await self.channel_adapter.get_channel_updates(limit=limit * 2)
            
            # Фильтруем только новые сообщения
            if last_message_id:
                messages = [m for m in messages if m.get("message_id", 0) > last_message_id]
            
            # Ограничиваем количество
            messages = messages[:limit]
            
            # Парсим каждое сообщение
            orders = []
            for message in messages:
                parsed = await self.parse_channel_message(message)
                if parsed:
                    orders.append({
                        "id": f"channel_{message.get('message_id')}",
                        "message_id": message.get("message_id"),
                        "parsed": parsed,
                        "source": "telegram_channel",
                        "raw_message": message
                    })
            
            log.info(f"✅ [Channel Parser] Получено {len(orders)} заказов из канала")
            return orders
            
        except Exception as e:
            log.error(f"❌ [Channel Parser] Ошибка получения заказов из канала: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            return []
