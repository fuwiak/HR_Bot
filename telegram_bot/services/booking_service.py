"""
Сервис для работы с записями (bookings)
"""
import logging

from telegram_bot.integrations.google_sheets import (
    get_services,
    get_masters,
    create_booking_in_sheets,
    check_slot_available
)
from telegram_bot.storage.user_records import add_user_record

log = logging.getLogger(__name__)


def create_real_booking(user_id: int, service_name: str, master_name: str, date_time: str, client_name: str = "", client_phone: str = "") -> dict:
    """Создать запись через Google Sheets"""
    log.info(f"🚀 СОЗДАНИЕ ЗАПИСИ: user_id={user_id}, услуга='{service_name}', мастер='{master_name}', время='{date_time}'")
    
    try:
        # Находим услугу
        log.info("🔍 Поиск услуги...")
        services = get_services()
        service = None
        for s in services:
            if service_name.lower() in s.get("title", "").lower():
                service = s
                break
        
        if not service:
            log.error(f"❌ Услуга '{service_name}' не найдена")
            raise Exception(f"Услуга '{service_name}' не найдена")
        log.info(f"✅ Найдена услуга: {service.get('title')}")
        
        # Находим мастера
        log.info("👥 Поиск мастера...")
        masters = get_masters()
        master = None
        for m in masters:
            if master_name.lower() in m.get("name", "").lower():
                master = m
                break
        
        if not master:
            log.error(f"❌ Мастер '{master_name}' не найден")
            raise Exception(f"Мастер '{master_name}' не найден")
        log.info(f"✅ Найден мастер: {master.get('name')}")
        
        # Проверяем доступность времени
        date_part = date_time.split()[0] if " " in date_time else date_time
        time_part = date_time.split()[1] if " " in date_time else ""
        
        if not check_slot_available(master_name, date_part, time_part):
            raise Exception(f"Время {date_time} недоступно, выберите другое время")
        
        # Создаем запись в Google Sheets
        booking_data = {
            "user_id": user_id,
            "service": service_name,
            "service_id": service.get("id"),
            "master": master_name,
            "master_id": master.get("id"),
            "date": date_part,
            "time": time_part,
            "datetime": date_time,
            "client_name": client_name,
            "client_phone": client_phone,
            "price": service.get("price", 0),
            "duration": service.get("duration", 60),
            "status": "confirmed"
        }
        
        log.info("📝 Создание записи в Google Sheets...")
        booking_record = create_booking_in_sheets(booking_data)
        
        # Формируем запись для локального хранилища
        formatted_record = {
            "id": booking_record.get("id"),
            "date": date_part,
            "datetime": date_time,
            "services": [{
                "id": service.get("id"),
                "title": service.get("title"),
                "cost": service.get("price", 0)
            }],
            "staff": {
                "id": master.get("id"),
                "name": master.get("name"),
                "specialization": master.get("specialization", "")
            },
            "company": {
                "title": "HR-отдел"
            },
            "comment": "Запись через Telegram бот",
            "visit_attendance": 0,
            "length": service.get("duration", 60),
            "online": True
        }
        
        add_user_record(user_id, formatted_record)
        log.info(f"🎉 ЗАПИСЬ СОЗДАНА! ID: {formatted_record['id']}")
        return formatted_record
        
    except Exception as e:
        log.error(f"❌ ОШИБКА при создании записи: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        raise e


def create_booking_from_parsed_data(user_id: int, parsed_data: dict, client_name: str = "", client_phone: str = "") -> dict:
    """Создает запись на основе распарсенных данных"""
    try:
        log.info(f"🔍 PARSED DATA: {parsed_data}")
        
        if not parsed_data.get("has_all_info"):
            raise Exception("Недостаточно данных для создания записи")
        
        # Создаем реальную запись
        booking_record = create_real_booking(
            user_id,
            parsed_data["service"],
            parsed_data["master"],
            parsed_data["datetime"],
            client_name=client_name,
            client_phone=client_phone
        )
        
        return booking_record
        
    except Exception as e:
        log.error(f"Error creating booking from parsed data: {e}")
        raise e
