"""
HR Time Integration Module
Интеграция с HR Time API для получения заказов и отправки откликов
"""
import os
import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

log = logging.getLogger()

# ===================== CONFIGURATION =====================
HRTIME_API_KEY = os.getenv("HRTIME_API_KEY")
HRTIME_API_URL = os.getenv("HRTIME_API_URL", "https://api.hrtime.ru/v1")
HRTIME_PROFILE_ID = os.getenv("HRTIME_PROFILE_ID", "29664")

# ===================== HELPER FUNCTIONS =====================

def get_headers() -> Dict[str, str]:
    """Получить заголовки для API запросов"""
    if not HRTIME_API_KEY:
        return {}
    return {
        "Authorization": f"Bearer {HRTIME_API_KEY}",
        "Content-Type": "application/json"
    }

# ===================== ORDER OPERATIONS =====================

async def get_new_orders(limit: int = 10) -> List[Dict]:
    """
    Получить новые заказы с HR Time
    
    Args:
        limit: Максимальное количество заказов
    
    Returns:
        Список заказов с информацией
    """
    if not HRTIME_API_KEY:
        log.error("❌ HRTIME_API_KEY не установлен")
        return []
    
    # Примерный endpoint, нужно адаптировать под реальный API HR Time
    url = f"{HRTIME_API_URL}/orders"
    headers = get_headers()
    params = {
        "profile_id": HRTIME_PROFILE_ID,
        "status": "new",
        "limit": limit
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [HR Time] Ошибка получения заказов: {response.status} - {error_text}")
                    return []
                
                result = await response.json()
                orders = result.get("orders", result.get("data", []))
                
                parsed_orders = []
                for order in orders:
                    parsed_orders.append({
                        "id": order.get("id"),
                        "title": order.get("title", ""),
                        "description": order.get("description", ""),
                        "budget": order.get("budget"),
                        "deadline": order.get("deadline"),
                        "client": {
                            "name": order.get("client_name", ""),
                            "email": order.get("client_email", ""),
                            "phone": order.get("client_phone", "")
                        },
                        "created_at": order.get("created_at"),
                        "requirements": order.get("requirements", "")
                    })
                
                log.info(f"✅ [HR Time] Получено {len(parsed_orders)} новых заказов")
                return parsed_orders
    except Exception as e:
        log.error(f"❌ [HR Time] Ошибка получения заказов: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return []

async def send_proposal(order_id: str, proposal_text: str) -> bool:
    """
    Отправить отклик на заказ через HR Time API
    
    Args:
        order_id: ID заказа
        proposal_text: Текст отклика
    
    Returns:
        True при успехе, False при ошибке
    """
    if not HRTIME_API_KEY:
        log.error("❌ HRTIME_API_KEY не установлен")
        return False
    
    url = f"{HRTIME_API_URL}/orders/{order_id}/proposals"
    headers = get_headers()
    
    data = {
        "text": proposal_text,
        "profile_id": HRTIME_PROFILE_ID
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [HR Time] Ошибка отправки отклика: {response.status} - {error_text}")
                    return False
                
                log.info(f"✅ [HR Time] Отклик отправлен на заказ {order_id}")
                return True
    except Exception as e:
        log.error(f"❌ [HR Time] Ошибка отправки отклика: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return False

async def send_message(order_id: str, message_text: str, recipient_email: Optional[str] = None) -> bool:
    """
    Отправить сообщение по заказу (прямое письмо)
    
    Args:
        order_id: ID заказа
        message_text: Текст сообщения
        recipient_email: Email получателя (если указан, отправляется также email)
    
    Returns:
        True при успехе, False при ошибке
    """
    if not HRTIME_API_KEY:
        return False
    
    url = f"{HRTIME_API_URL}/orders/{order_id}/messages"
    headers = get_headers()
    
    data = {
        "text": message_text,
        "profile_id": HRTIME_PROFILE_ID
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [HR Time] Ошибка отправки сообщения: {response.status} - {error_text}")
                    return False
                
                # Если указан email, отправляем также через email
                if recipient_email:
                    from email_helper import send_email
                    await send_email(
                        to_email=recipient_email,
                        subject=f"Ответ по заказу #{order_id}",
                        body=message_text
                    )
                
                log.info(f"✅ [HR Time] Сообщение отправлено по заказу {order_id}")
                return True
    except Exception as e:
        log.error(f"❌ [HR Time] Ошибка отправки сообщения: {e}")
        return False

async def get_order_details(order_id: str) -> Optional[Dict]:
    """Получить детальную информацию о заказе"""
    if not HRTIME_API_KEY:
        return None
    
    url = f"{HRTIME_API_URL}/orders/{order_id}"
    headers = get_headers()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status >= 400:
                    return None
                return await response.json()
    except Exception as e:
        log.error(f"❌ [HR Time] Ошибка получения деталей заказа: {e}")
        return None










