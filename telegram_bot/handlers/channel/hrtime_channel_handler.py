"""
HR Time Channel Handler
Обработчик сообщений из Telegram канала @HRTime_bot
"""
import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

log = logging.getLogger()

# Импорты
try:
    from services.services.telegram_channel_parser import TelegramChannelParser
    from services.agents.scenario_workflows import process_hrtime_order
    from services.services.hrtime_sync import HRTimeSync
    CHANNEL_HANDLER_AVAILABLE = True
except ImportError as e:
    CHANNEL_HANDLER_AVAILABLE = False
    log.warning(f"⚠️ Channel handler модули недоступны: {e}")


# Глобальные переменные
processed_channel_messages = set()
channel_parser = None
sync_service = None

if CHANNEL_HANDLER_AVAILABLE:
    try:
        channel_parser = TelegramChannelParser()
        sync_service = HRTimeSync()
    except Exception as e:
        log.error(f"❌ Ошибка инициализации channel handler: {e}")


async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик сообщений из Telegram канала @HRTime_bot
    
    Args:
        update: Обновление от Telegram
        context: Контекст бота
    """
    if not CHANNEL_HANDLER_AVAILABLE or not channel_parser:
        return
    
    # Проверяем, что это сообщение из канала
    if not update.channel_post:
        return
    
    post = update.channel_post
    message_id = post.message_id
    chat_id = post.chat.id
    chat_username = post.chat.username
    
    # Проверяем, что это наш канал
    import os
    hrtime_channel_username = os.getenv("HRTIME_CHANNEL_USERNAME", "@HRTime_bot").lstrip('@')
    hrtime_channel_id = os.getenv("HRTIME_CHANNEL_ID")
    
    is_our_channel = False
    if chat_username and hrtime_channel_username in chat_username:
        is_our_channel = True
    elif hrtime_channel_id and str(chat_id) == str(hrtime_channel_id):
        is_our_channel = True
    
    if not is_our_channel:
        return
    
    # Пропускаем уже обработанные сообщения
    if message_id in processed_channel_messages:
        log.debug(f"ℹ️ [Channel Handler] Сообщение {message_id} уже обработано")
        return
    
    try:
        log.info(f"📢 [Channel Handler] Получено сообщение из канала @HRTime_bot: {message_id}")
        
        # Формируем данные сообщения
        message_data = {
            "message_id": message_id,
            "text": post.text or post.caption or "",
            "date": post.date,
            "chat_id": chat_id,
            "chat_username": chat_username,
            "raw": post.to_dict() if hasattr(post, 'to_dict') else {}
        }
        
        # Отправляем все новости в канал лидов с классификацией
        try:
            from telegram_bot.services.hrtime_news_monitor import send_news_notification
            await send_news_notification(context.bot, message_data)
            log.info(f"✅ [Channel Handler] Новость отправлена в канал лидов")
        except Exception as e:
            log.warning(f"⚠️ [Channel Handler] Ошибка отправки новости в канал лидов: {e}")
        
        # Парсим сообщение
        parsed_order = await channel_parser.parse_channel_message(message_data)
        
        if not parsed_order:
            log.warning(f"⚠️ [Channel Handler] Не удалось распарсить сообщение {message_id}")
            return
        
        # Синхронизируем с API (если нужно)
        if sync_service:
            channel_order = {
                "message_id": message_id,
                "parsed": parsed_order
            }
            await sync_service.sync_channel_to_api(channel_order)
        
        # Обрабатываем заказ через Сценарий 1
        order_id = f"channel_{message_id}"
        order_data = {
            "id": order_id,
            "title": parsed_order.get("raw_data", {}).get("title", "Заказ из канала"),
            "description": parsed_order.get("raw_data", {}).get("description", ""),
            "budget": parsed_order.get("budget", {}).get("text", ""),
            "deadline": parsed_order.get("deadline", {}).get("text", ""),
            "client": parsed_order.get("contacts", {}),
            "source": "telegram_channel",
            "message_id": message_id
        }
        
        result = await process_hrtime_order(order_id, order_data=order_data, telegram_bot=context.bot)
        
        if result.get("success"):
            processed_channel_messages.add(message_id)
            log.info(f"✅ [Channel Handler] Заказ {order_id} обработан успешно")
            
            # Отправляем уведомление консультанту, если подготовлено
            if result.get("notification_text") and context.bot:
                consultant_chat_id = os.getenv("TELEGRAM_CONSULTANT_CHAT_ID")
                if consultant_chat_id:
                    try:
                        await context.bot.send_message(
                            chat_id=int(consultant_chat_id),
                            text=result["notification_text"],
                            parse_mode="Markdown"
                        )
                        log.info(f"✅ [Channel Handler] Консультант уведомлен о заказе {order_id}")
                    except Exception as e:
                        log.error(f"❌ [Channel Handler] Ошибка отправки уведомления: {e}")
        else:
            log.warning(f"⚠️ [Channel Handler] Ошибка обработки заказа {order_id}: {result.get('error')}")
    
    except Exception as e:
        log.error(f"❌ [Channel Handler] Ошибка обработки сообщения из канала: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")


__all__ = ['handle_channel_post']
