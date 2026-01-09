"""
HR Time Order Parser Service
Сервис для парсинга заказов с HR Time через LLM
"""
import logging
from typing import Dict, Optional

log = logging.getLogger()

# Импорты
try:
    from services.adapters.hrtime_order_adapter import HRTimeOrderAdapter
    from services.helpers.hrtime_helper import get_order_details
    ADAPTER_AVAILABLE = True
except ImportError as e:
    ADAPTER_AVAILABLE = False
    log.warning(f"⚠️ HRTime Adapter недоступен: {e}")


class HRTimeOrderParser:
    """Сервис для парсинга заказов HR Time"""
    
    def __init__(self):
        self.adapter = None
        if ADAPTER_AVAILABLE:
            try:
                self.adapter = HRTimeOrderAdapter()
            except Exception as e:
                log.error(f"❌ Ошибка инициализации HRTimeOrderAdapter: {e}")
                self.adapter = None
    
    async def parse_order(self, order_id: str, order_data: Optional[Dict] = None) -> Dict:
        """
        Парсит заказ с HR Time, извлекая структурированные данные
        
        Args:
            order_id: ID заказа в HR Time
            order_data: Данные заказа (если не указано, загружается через API)
        
        Returns:
            Словарь с распарсенными данными:
            {
                "order_id": str,
                "parsed": {
                    "requirements": str,
                    "budget": Dict,
                    "deadline": Dict,
                    "contacts": Dict
                },
                "success": bool,
                "error": Optional[str]
            }
        """
        try:
            # Получаем данные заказа, если не предоставлены
            if order_data is None:
                log.info(f"📥 [Order Parser] Загрузка данных заказа {order_id}...")
                order_data = await get_order_details(order_id)
                if not order_data:
                    return {
                        "order_id": order_id,
                        "parsed": None,
                        "success": False,
                        "error": "Не удалось получить данные заказа"
                    }
            
            # Парсим через адаптер
            if not self.adapter:
                log.warning("⚠️ [Order Parser] Адаптер недоступен, используем базовый парсинг")
                # Базовый парсинг без LLM
                client = order_data.get("client", {})
                parsed = {
                    "requirements": order_data.get("description", ""),
                    "budget": {
                        "amount": 0.0,
                        "currency": "RUB",
                        "text": str(order_data.get("budget", ""))
                    },
                    "deadline": {
                        "date": None,
                        "text": str(order_data.get("deadline", ""))
                    },
                    "contacts": {
                        "full_name": client.get("name", ""),
                        "phone": client.get("phone", ""),
                        "email": client.get("email", "")
                    },
                    "raw_data": order_data
                }
            else:
                log.info(f"🔍 [Order Parser] Парсинг заказа {order_id} через LLM...")
                parsed = await self.adapter.parse_order(order_data)
            
            log.info(f"✅ [Order Parser] Заказ {order_id} успешно распарсен")
            return {
                "order_id": order_id,
                "parsed": parsed,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            log.error(f"❌ [Order Parser] Ошибка парсинга заказа {order_id}: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "order_id": order_id,
                "parsed": None,
                "success": False,
                "error": str(e)
            }
    
    def format_parsed_order(self, parsed_data: Dict) -> str:
        """
        Форматирует распарсенные данные в читаемый текст
        
        Args:
            parsed_data: Результат парсинга от parse_order()
        
        Returns:
            Отформатированный текст
        """
        if not parsed_data.get("success") or not parsed_data.get("parsed"):
            return "Ошибка парсинга заказа"
        
        parsed = parsed_data["parsed"]
        parts = []
        
        # ТЗ
        if parsed.get("requirements"):
            parts.append(f"📋 ТЗ:\n{parsed['requirements']}")
        
        # Бюджет
        budget = parsed.get("budget", {})
        if budget.get("amount", 0) > 0:
            parts.append(f"💰 Бюджет: {budget['amount']:.0f} {budget.get('currency', 'RUB')}")
        elif budget.get("text"):
            parts.append(f"💰 Бюджет: {budget['text']}")
        
        # Сроки
        deadline = parsed.get("deadline", {})
        if deadline.get("date"):
            parts.append(f"📅 Срок: {deadline['date']}")
        elif deadline.get("text"):
            parts.append(f"📅 Срок: {deadline['text']}")
        
        # Контакты
        contacts = parsed.get("contacts", {})
        contact_parts = []
        if contacts.get("full_name"):
            contact_parts.append(f"👤 {contacts['full_name']}")
        if contacts.get("phone"):
            contact_parts.append(f"📞 {contacts['phone']}")
        if contacts.get("email"):
            contact_parts.append(f"✉️ {contacts['email']}")
        
        if contact_parts:
            parts.append(f"📧 Контакты:\n" + "\n".join(contact_parts))
        
        return "\n\n".join(parts) if parts else "Данные не найдены"
