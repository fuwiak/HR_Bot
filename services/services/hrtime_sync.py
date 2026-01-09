"""
HR Time Sync Service
Сервис для синхронизации данных между Telegram каналом @HRTime_bot и HR Time API
"""
import logging
from typing import Dict, List, Optional

log = logging.getLogger()

# Импорты
try:
    from services.services.telegram_channel_parser import TelegramChannelParser
    from services.helpers.hrtime_helper import get_new_orders, send_proposal, get_order_details
    SYNC_AVAILABLE = True
except ImportError as e:
    SYNC_AVAILABLE = False
    log.warning(f"⚠️ Sync модули недоступны: {e}")


class HRTimeSync:
    """Сервис для синхронизации между каналом и API"""
    
    def __init__(self):
        self.channel_parser = None
        if SYNC_AVAILABLE:
            try:
                self.channel_parser = TelegramChannelParser()
            except Exception as e:
                log.error(f"❌ Ошибка инициализации ChannelParser: {e}")
    
    async def sync_channel_to_api(self, channel_order: Dict) -> bool:
        """
        Синхронизирует заказ из канала с HR Time API
        
        Args:
            channel_order: Заказ из Telegram канала
        
        Returns:
            True если синхронизация успешна
        """
        if not SYNC_AVAILABLE:
            return False
        
        try:
            # Извлекаем данные из заказа канала
            parsed = channel_order.get("parsed", {})
            raw_data = parsed.get("raw_data", {})
            
            # Формируем данные для API
            order_data = {
                "title": raw_data.get("title", "Заказ из канала"),
                "description": raw_data.get("description", ""),
                "budget": parsed.get("budget", {}).get("text", ""),
                "deadline": parsed.get("deadline", {}).get("text", ""),
                "client": parsed.get("contacts", {}),
                "source": "telegram_channel",
                "message_id": channel_order.get("message_id")
            }
            
            # TODO: Когда API будет готово, здесь будет отправка данных в HR Time API
            # Пока это placeholder
            log.info(f"🔄 [Sync] Заказ из канала подготовлен для синхронизации с API (placeholder)")
            log.debug(f"🔄 [Sync] Данные: {order_data}")
            
            return True
            
        except Exception as e:
            log.error(f"❌ [Sync] Ошибка синхронизации канала с API: {e}")
            return False
    
    async def sync_api_to_channel(self, api_order: Dict) -> bool:
        """
        Синхронизирует заказ из API с Telegram каналом
        
        Args:
            api_order: Заказ из HR Time API
        
        Returns:
            True если синхронизация успешна
        """
        if not SYNC_AVAILABLE:
            return False
        
        try:
            # TODO: Когда будет готово, здесь будет отправка данных в канал
            # Пока это placeholder
            log.info(f"🔄 [Sync] Заказ из API подготовлен для синхронизации с каналом (placeholder)")
            log.debug(f"🔄 [Sync] Данные: {api_order}")
            
            return True
            
        except Exception as e:
            log.error(f"❌ [Sync] Ошибка синхронизации API с каналом: {e}")
            return False
    
    async def find_duplicates(
        self,
        channel_orders: List[Dict],
        api_orders: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        Находит дубликаты заказов между каналом и API
        
        Args:
            channel_orders: Список заказов из канала
            api_orders: Список заказов из API
        
        Returns:
            Словарь с дубликатами: {"channel": [...], "api": [...]}
        """
        duplicates = {"channel": [], "api": []}
        
        # Простая проверка по заголовку и описанию
        for channel_order in channel_orders:
            channel_title = channel_order.get("parsed", {}).get("raw_data", {}).get("title", "")
            channel_desc = channel_order.get("parsed", {}).get("raw_data", {}).get("description", "")
            
            for api_order in api_orders:
                api_title = api_order.get("title", "")
                api_desc = api_order.get("description", "")
                
                # Проверяем совпадение
                if channel_title and api_title and channel_title.lower() in api_title.lower():
                    duplicates["channel"].append(channel_order)
                    duplicates["api"].append(api_order)
                    log.info(f"🔄 [Sync] Найден дубликат: канал '{channel_title}' = API '{api_title}'")
        
        return duplicates
