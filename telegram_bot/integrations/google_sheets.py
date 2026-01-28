"""
Интеграция с Google Sheets
"""
import logging

log = logging.getLogger(__name__)

from services.helpers.google_sheets_helper import (
    get_masters as get_masters_from_sheets,
    get_services as get_services_from_sheets,
    create_booking as create_booking_in_sheets,
    check_slot_available,
    get_available_slots,
    get_user_bookings,
    delete_user_booking,
)


def get_services(master_name: str = None):
    """Get available services, optionally filtered by master"""
    log.info(f"📋 Получение услуг (HR-специалист: {master_name or 'все'})...")
    try:
        services = get_services_from_sheets(master_name)
        log.info(f"✅ Найдено {len(services)} услуг")
        return services
    except Exception as e:
        log.error(f"❌ Ошибка получения услуг: {e}")
        return []


def get_services_with_prices(master_name: str = None):
    """Получить услуги с ценами (аналог старой функции)"""
    return get_services(master_name)


def get_services_for_master(master_name: str):
    """Получить услуги для конкретного HR-специалиста"""
    return get_services(master_name)


def get_masters():
    """Get available masters"""
    log.info("👥 Получение списка HR-специалистов...")
    try:
        masters = get_masters_from_sheets()
        log.info(f"✅ Найдено {len(masters)} HR-специалистов")
        return masters
    except Exception as e:
        log.error(f"❌ Ошибка получения HR-специалистов: {e}")
        return []


def get_api_data_for_ai():
    """Получить форматированные данные для AI (услуги и мастера) из Google Sheets листа 'Ценник'"""
    try:
        services = get_services()
        masters = get_masters()
        
        if not services:
            return "⚠️ Услуги временно недоступны. Данные загружаются..."
        
        data_text = "🚨 ВАЖНО: Это ТОЧНЫЕ данные из Google Sheets листа 'Ценник'. Используй ТОЛЬКО эти цены!\n\n"
        data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        data_text += "📋 ВСЕ HR-УСЛУГИ:\n"
        data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Разделяем по типам (если есть)
        men_services = [s for s in services if s.get('type') == 'men']
        women_services = [s for s in services if s.get('type') == 'women']
        
        if men_services:
            data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            data_text += "👤 УСЛУГИ HR-КОНСУЛЬТАНТА (Анастасия Новосёлова):\n"
            data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for service in men_services:
                name = service.get("title", "Без названия")
                price = service.get("price", 0)
                price_str = service.get("price_str", "")
                duration = service.get("duration", 0)
                
                data_text += f"• {name}"
                
                # Отображаем цену (приоритет строковому формату с диапазоном) - ЯВНО и ЧЕТКО
                if price_str and ("–" in price_str or "-" in price_str):
                    data_text += f" → ЦЕНА: {price_str} ₽"
                elif price > 0:
                    data_text += f" → ЦЕНА: {price} ₽"
                else:
                    data_text += f" → ЦЕНА: уточнить"
                
                if duration > 0:
                    data_text += f" ({duration} мин)"
                    
                data_text += "\n"
        
        if women_services:
            data_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            data_text += "👤 УСЛУГИ HR-КОНСУЛЬТАНТА (Анастасия Новосёлова):\n"
            data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for service in women_services:
                name = service.get("title", "Без названия")
                price = service.get("price", 0)
                price_str = service.get("price_str", "")
                duration = service.get("duration", 0)
                
                data_text += f"• {name}"
                
                # Отображаем цену (приоритет строковому формату с диапазоном) - ЯВНО и ЧЕТКО
                if price_str and ("–" in price_str or "-" in price_str):
                    data_text += f" → ЦЕНА: {price_str} ₽"
                elif price > 0:
                    data_text += f" → ЦЕНА: {price} ₽"
                else:
                    data_text += f" → ЦЕНА: уточнить"
                    
                if duration > 0:
                    data_text += f" ({duration} мин)"
                
                data_text += "\n"
        
        data_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        data_text += "👥 МАСТЕРА:\n"
        data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for master in masters:
            name = master.get("name", "Без имени")
            specialization = master.get("specialization", "")
            
            data_text += f"• {name}"
            if specialization:
                data_text += f" ({specialization})"
            data_text += "\n"
        
        data_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        data_text += "🚨 ПОВТОРЯЮ: Используй ТОЛЬКО цены из списка выше!\n"
        data_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        return data_text
    except Exception as e:
        log.error(f"Ошибка получения данных: {e}")
        return "Данные временно недоступны"


def get_master_services_text(master_name: str) -> str:
    """Получить текст с услугами HR-специалиста (без AI)"""
    try:
        masters = get_masters()
        master = next((m for m in masters if m.get("name", "").lower() == master_name.lower()), None)
        
        if not master:
            return f"HR-специалист {master_name} не найден"
            
        master_services = get_services_for_master(master_name)
        if not master_services:
            return f"У мастера {master_name} нет доступных услуг"
            
        text = f"✨ Услуги мастера {master_name}:\n\n"
        
        for service in master_services:
            service_name = service.get("title", "")
            price = service.get("price", 0)
            duration = service.get("duration", 0)
            
            if service_name:
                text += f"• {service_name}"
                if price > 0:
                    text += f" — {price} ₽"
                if duration > 0:
                    text += f" ({duration} мин)"
                text += "\n"
        
        text += f"\n💡 Чтобы записаться к {master_name}, укажите желаемую дату и время."
        
        return text
    except Exception as e:
        log.error(f"Ошибка получения услуг мастера: {e}")
        return "Данные временно недоступны"
