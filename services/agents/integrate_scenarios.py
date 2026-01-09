"""
Интеграция сценариев в основное приложение
Добавляет фоновые задачи для мониторинга и обработки лидов
"""
import asyncio
import logging
import os
from typing import Optional

log = logging.getLogger()

try:
    from services.agents.scenario_workflows import (
        process_hrtime_order,
        process_lead_email,
        process_telegram_lead,
        check_upcoming_deadlines,
        start_deadline_monitor
    )
    from services.helpers.hrtime_helper import get_new_orders
    from services.helpers.email_helper import check_new_emails
    from services.services.telegram_channel_parser import TelegramChannelParser
    SCENARIOS_AVAILABLE = True
    CHANNEL_PARSER_AVAILABLE = True
except ImportError as e:
    log.warning(f"⚠️ Модули сценариев недоступны: {e}")
    SCENARIOS_AVAILABLE = False
    CHANNEL_PARSER_AVAILABLE = False


# Глобальные переменные для хранения обработанных ID (чтобы не обрабатывать повторно)
processed_hrtime_orders = set()
processed_channel_messages = set()  # ID сообщений из Telegram канала
processed_emails = set()  # Используем message_id или subject+from как ключ
last_channel_message_id = None  # ID последнего обработанного сообщения из канала


# ===================== Фоновые задачи =====================

async def monitor_hrtime_orders(telegram_bot, interval_minutes: int = 30):
    """
    Фоновая задача для мониторинга новых заказов с HR Time
    
    Приоритет источников:
    1. Telegram канал @HRTime_bot (основной источник)
    2. HR Time API (fallback/placeholder)
    
    Args:
        telegram_bot: Экземпляр Telegram бота для уведомлений
        interval_minutes: Интервал проверки в минутах
    """
    if not SCENARIOS_AVAILABLE:
        log.warning("⚠️ Сценарии недоступны, мониторинг HR Time отключен")
        return
    
    log.info(f"🔄 [Мониторинг] Запуск мониторинга HR Time (интервал: {interval_minutes} минут)")
    log.info(f"📢 [Мониторинг] Приоритет: Telegram канал @HRTime_bot → HR Time API (fallback)")
    
    # Инициализируем парсер канала
    channel_parser = None
    if CHANNEL_PARSER_AVAILABLE:
        try:
            channel_parser = TelegramChannelParser()
            log.info("✅ [Мониторинг] Парсер Telegram канала инициализирован")
        except Exception as e:
            log.warning(f"⚠️ [Мониторинг] Не удалось инициализировать парсер канала: {e}")
    
    global last_channel_message_id
    
    while True:
        try:
            orders_found = 0
            
            # ШАГ 1: Проверяем Telegram канал @HRTime_bot (основной источник)
            if channel_parser:
                try:
                    log.info("📢 [Мониторинг] Проверка Telegram канала @HRTime_bot...")
                    channel_orders = await channel_parser.get_new_orders_from_channel(
                        limit=10,
                        last_message_id=last_channel_message_id
                    )
                    
                    for channel_order in channel_orders:
                        message_id = channel_order.get("message_id")
                        order_id = f"channel_{message_id}"
                        
                        # Пропускаем уже обработанные
                        if order_id in processed_channel_messages:
                            continue
                        
                        log.info(f"🔔 [Мониторинг] Найден новый заказ из канала: {order_id}")
                        
                        # Преобразуем данные из канала в формат для process_hrtime_order
                        parsed_data = channel_order.get("parsed", {})
                        raw_data = parsed_data.get("raw_data", {})
                        
                        order_data = {
                            "id": order_id,
                            "title": raw_data.get("title", "Заказ из канала"),
                            "description": raw_data.get("description", ""),
                            "budget": parsed_data.get("budget", {}).get("text", ""),
                            "deadline": parsed_data.get("deadline", {}).get("text", ""),
                            "client": parsed_data.get("contacts", {}),
                            "source": "telegram_channel",
                            "message_id": message_id
                        }
                        
                        # Обрабатываем заказ через Сценарий 1
                        result = await process_hrtime_order(order_id, order_data=order_data)
                        
                        if result.get("success"):
                            processed_channel_messages.add(order_id)
                            if message_id and (not last_channel_message_id or message_id > last_channel_message_id):
                                last_channel_message_id = message_id
                            orders_found += 1
                            
                            # Отправляем уведомление консультанту
                            if result.get("notification_text") and telegram_bot:
                                consultant_chat_id = os.getenv("TELEGRAM_CONSULTANT_CHAT_ID")
                                if consultant_chat_id:
                                    try:
                                        await telegram_bot.send_message(
                                            chat_id=int(consultant_chat_id),
                                            text=result["notification_text"],
                                            parse_mode="Markdown"
                                        )
                                        log.info(f"✅ [Мониторинг] Консультант уведомлен о заказе {order_id}")
                                    except Exception as e:
                                        log.error(f"❌ [Мониторинг] Ошибка отправки уведомления: {e}")
                        
                        await asyncio.sleep(2)
                    
                    if channel_orders:
                        log.info(f"✅ [Мониторинг] Обработано {len(channel_orders)} заказов из Telegram канала")
                
                except Exception as e:
                    log.warning(f"⚠️ [Мониторинг] Ошибка получения заказов из канала: {e}")
                    log.info("🔄 [Мониторинг] Переключаюсь на HR Time API (fallback)")
            
            # ШАГ 2: Fallback на HR Time API (placeholder, пока не реализовано)
            if orders_found == 0:
                try:
                    log.info("🔄 [Мониторинг] Проверка HR Time API (fallback)...")
                    api_orders = await get_new_orders(limit=10)
                    
                    if not api_orders:
                        log.info("ℹ️ [Мониторинг] HR Time API не вернул заказов (placeholder)")
                    else:
                        log.warning("⚠️ [Мониторинг] HR Time API вернул заказы, но это placeholder - не обрабатываем")
                        # TODO: Когда API будет готово, раскомментировать обработку
                        # for order in api_orders:
                        #     order_id = str(order.get("id", ""))
                        #     if order_id in processed_hrtime_orders:
                        #         continue
                        #     # ... обработка заказа
                
                except Exception as e:
                    log.warning(f"⚠️ [Мониторинг] Ошибка HR Time API (fallback): {e}")
            
        except Exception as e:
            log.error(f"❌ [Мониторинг] Ошибка мониторинга HR Time: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Ожидание перед следующей проверкой
        await asyncio.sleep(interval_minutes * 60)


async def monitor_emails(telegram_bot, interval_minutes: int = 15, require_approval: bool = True):
    """
    Фоновая задача для мониторинга новых писем
    
    Args:
        telegram_bot: Экземпляр Telegram бота для подтверждений и уведомлений
        interval_minutes: Интервал проверки в минутах
        require_approval: Требовать ли подтверждение консультанта перед отправкой
    """
    if not SCENARIOS_AVAILABLE:
        log.warning("⚠️ Сценарии недоступны, мониторинг email отключен")
        return
    
    log.info(f"📧 [Мониторинг] Запуск мониторинга email (интервал: {interval_minutes} минут)")
    
    while True:
        try:
            # Проверяем новые письма за последний день
            emails = await check_new_emails(folder="INBOX", since_days=1, limit=20)
            
            for email_data in emails:
                # Создаем уникальный ключ для письма
                email_key = f"{email_data.get('from', '')}_{email_data.get('subject', '')}"
                
                # Пропускаем уже обработанные
                if email_key in processed_emails:
                    continue
                
                log.info(f"📬 [Мониторинг] Найдено новое письмо: {email_data.get('subject', 'Без темы')}")
                
                # Обрабатываем письмо через Сценарий 2
                result = await process_lead_email(
                    email_data=email_data,
                    require_approval=require_approval,
                    telegram_bot=telegram_bot
                )
                
                if result.get("success"):
                    processed_emails.add(email_key)
                    log.info(f"✅ [Мониторинг] Письмо обработано: {email_key}")
                
                # Небольшая задержка между обработкой писем
                await asyncio.sleep(1)
            
            if emails:
                log.info(f"✅ [Мониторинг] Проверено {len(emails)} писем")
            
        except Exception as e:
            log.error(f"❌ [Мониторинг] Ошибка мониторинга email: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Ожидание перед следующей проверкой
        await asyncio.sleep(interval_minutes * 60)


def start_background_tasks(telegram_bot, enable_hrtime: bool = True, enable_email: bool = True, enable_deadlines: bool = True):
    """
    Запуск всех фоновых задач мониторинга
    
    Args:
        telegram_bot: Экземпляр Telegram бота
        enable_hrtime: Включить мониторинг HR Time
        enable_email: Включить мониторинг email
        enable_deadlines: Включить мониторинг дедлайнов
    """
    if not SCENARIOS_AVAILABLE:
        log.warning("⚠️ Сценарии недоступны, фоновые задачи не запущены")
        return
    
    log.info("🚀 [Интеграция] Запуск фоновых задач мониторинга...")
    
    # Создаем задачи
    tasks = []
    
    if enable_hrtime:
        hrtime_interval = int(os.getenv("HRTIME_CHECK_INTERVAL_MINUTES", "30"))
        task = asyncio.create_task(monitor_hrtime_orders(telegram_bot, interval_minutes=hrtime_interval))
        tasks.append(task)
        log.info(f"✅ [Интеграция] Запущен мониторинг HR Time (интервал: {hrtime_interval} мин)")
    
    if enable_email:
        email_interval = int(os.getenv("EMAIL_CHECK_INTERVAL_MINUTES", "15"))
        email_approval = os.getenv("EMAIL_REQUIRE_APPROVAL", "true").lower() == "true"
        task = asyncio.create_task(monitor_emails(telegram_bot, interval_minutes=email_interval, require_approval=email_approval))
        tasks.append(task)
        log.info(f"✅ [Интеграция] Запущен мониторинг email (интервал: {email_interval} мин, подтверждение: {email_approval})")
    
    if enable_deadlines:
        deadline_interval = int(os.getenv("DEADLINE_CHECK_INTERVAL_HOURS", "24"))
        task = asyncio.create_task(start_deadline_monitor(telegram_bot, check_interval_hours=deadline_interval))
        tasks.append(task)
        log.info(f"✅ [Интеграция] Запущен мониторинг дедлайнов (интервал: {deadline_interval} часов)")
    
    log.info(f"✅ [Интеграция] Запущено {len(tasks)} фоновых задач")
    
    return tasks


