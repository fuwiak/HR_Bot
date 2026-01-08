"""
Менеджер меню для мессенджеров
"""
from typing import List, Dict, Any, Optional
import logging

log = logging.getLogger(__name__)


class MenuManager:
    """Управление меню и кнопками"""
    
    def __init__(self, platform: str = "telegram"):
        self.platform = platform
    
    def create_main_menu(self) -> List[List[Dict[str, str]]]:
        """Создать главное меню"""
        return [
            [{"text": "📝 Записаться", "callback_data": "book_appointment"}],
            [{"text": "📅 Мои записи", "callback_data": "my_records"}],
            [{"text": "💰 Услуги и цены", "callback_data": "services"}],
            [{"text": "👨‍💼 Мастера", "callback_data": "masters"}],
            [{"text": "ℹ️ О нас", "callback_data": "about"}]
        ]
    
    def create_services_menu(self, services: List[Dict[str, Any]], page: int = 0, per_page: int = 5) -> List[List[Dict[str, str]]]:
        """Создать меню услуг с пагинацией"""
        start_idx = page * per_page
        end_idx = start_idx + per_page
        page_services = services[start_idx:end_idx]
        
        buttons = []
        for service in page_services:
            title = service.get("title", "")
            price = service.get("price_str", "")
            service_id = service.get("id", "")
            
            text = f"{title}"
            if price:
                text += f" - {price}"
            
            buttons.append([{
                "text": text,
                "callback_data": f"service_{service_id}"
            }])
        
        # Навигация
        nav_row = []
        if page > 0:
            nav_row.append({"text": "⬅️ Назад", "callback_data": f"services_page_{page-1}"})
        if end_idx < len(services):
            nav_row.append({"text": "➡️ Далее", "callback_data": f"services_page_{page+1}"})
        
        if nav_row:
            buttons.append(nav_row)
        
        buttons.append([{"text": "🔙 Главное меню", "callback_data": "back_to_menu"}])
        
        return buttons
    
    def create_masters_menu(self, masters: List[Dict[str, Any]]) -> List[List[Dict[str, str]]]:
        """Создать меню мастеров"""
        buttons = []
        for master in masters:
            name = master.get("name", "")
            master_id = master.get("id", "")
            
            buttons.append([{
                "text": f"👤 {name}",
                "callback_data": f"master_{master_id}"
            }])
        
        buttons.append([{"text": "🔙 Главное меню", "callback_data": "back_to_menu"}])
        return buttons
    
    def create_booking_menu(self) -> List[List[Dict[str, str]]]:
        """Создать меню записи"""
        return [
            [{"text": "📋 Выбрать услугу", "callback_data": "select_service"}],
            [{"text": "👨‍💼 Выбрать мастера", "callback_data": "select_master"}],
            [{"text": "📅 Выбрать дату", "callback_data": "select_date"}],
            [{"text": "⏰ Выбрать время", "callback_data": "select_time"}],
            [{"text": "✅ Подтвердить", "callback_data": "confirm_booking"}],
            [{"text": "❌ Отмена", "callback_data": "cancel_booking"}]
        ]
    
    def create_confirmation_menu(self, action: str) -> List[List[Dict[str, str]]]:
        """Создать меню подтверждения"""
        return [
            [
                {"text": "✅ Да", "callback_data": f"confirm_{action}"},
                {"text": "❌ Нет", "callback_data": f"cancel_{action}"}
            ]
        ]
