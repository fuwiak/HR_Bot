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
    from scenario_workflows import (
        process_hrtime_order,
        process_lead_email,
        process_telegram_lead,
        check_upcoming_deadlines,
        start_deadline_monitor
    )
    from hrtime_helper import get_new_orders
    from email_helper import check_new_emails
    SCENARIOS_AVAILABLE = True
except ImportError as e:
    log.warning(f"⚠️ Модули сценариев недоступны: {e}")
    SCENARIOS_AVAILABLE = False


# Глобальные переменные для хранения обработанных ID (чтобы не обрабатывать повторно)
processed_hrtime_orders = set()
processed_emails = set()  # Используем message_id или subject+from как ключ


# ===================== Фоновые задачи =====================

async def monitor_hrtime_orders(telegram_bot, interval_minutes: int = 30):
    """
    Фоновая задача для мониторинга новых заказов с HR Time
    
    Args:
        telegram_bot: Экземпляр Telegram бота для уведомлений
        interval_minutes: Интервал проверки в минутах
    """
    if not SCENARIOS_AVAILABLE:
        log.warning("⚠️ Сценарии недоступны, мониторинг HR Time отключен")
        return
    
    log.info(f"🔄 [Мониторинг] Запуск мониторинга HR Time (интервал: {interval_minutes} минут)")
    
    while True:
        try:
            # Получаем новые заказы
            orders = await get_new_orders(limit=10)
            
            for order in orders:
                order_id = str(order.get("id", ""))
                
                # Пропускаем уже обработанные
                if order_id in processed_hrtime_orders:
                    continue
                
                log.info(f"🔔 [Мониторинг] Найден новый заказ: {order_id}")
                
                # Обрабатываем заказ через Сценарий 1
                result = await process_hrtime_order(order_id, order_data=order)
                
                if result.get("success"):
                    processed_hrtime_orders.add(order_id)
                    
                    # Отправляем уведомление консультанту, если подготовлено
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
                
                # Небольшая задержка между обработкой заказов
                await asyncio.sleep(2)
            
            if orders:
                log.info(f"✅ [Мониторинг] Обработано {len(orders)} заказов с HR Time")
            
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


