"""
Email monitoring state и фоновая задача
"""
import os
import asyncio
import logging
from typing import Dict

log = logging.getLogger(__name__)

# Глобальное состояние для отслеживания обработанных писем
processed_email_ids: set = set()

# Интервал проверки почты (в секундах)
email_check_interval = int(os.getenv("EMAIL_CHECK_INTERVAL", "10"))  # 10 секунд по умолчанию

# Хранилище состояния ответа на email для каждого пользователя
email_reply_state: Dict[int, Dict] = {}  # {user_id: {'email_id': ..., 'to': ..., 'subject': ...}}


async def send_email_notification(bot, email_data: Dict):
    """Отправка уведомления о новом письме подписчикам"""
    try:
        from telegram_bot.storage.email_subscribers import load_email_subscribers
        
        subscribers = load_email_subscribers()
        if not subscribers:
            return
        
        subject = email_data.get("subject", "Без темы")
        from_email = email_data.get("from", "Неизвестный отправитель")
        email_id = email_data.get("id", "")
        preview = email_data.get("preview", "")[:200]  # Первые 200 символов
        
        message_text = (
            f"📧 *Новое письмо*\n\n"
            f"*От:* {from_email}\n"
            f"*Тема:* {subject}\n\n"
        )
        
        if preview:
            message_text += f"*Превью:* {preview}...\n\n"
        
        message_text += (
            f"Используйте команду `/email_check` для просмотра полного письма\n"
            f"или нажмите кнопку ниже для ответа."
        )
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("📧 Ответить", callback_data=f"email_reply_{email_id}")],
            [InlineKeyboardButton("📋 Полный текст", callback_data=f"email_full_{email_id}")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем уведомление всем подписчикам
        for user_id in subscribers:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                log.info(f"✅ Уведомление о письме отправлено пользователю {user_id}")
            except Exception as e:
                log.warning(f"⚠️ Не удалось отправить уведомление пользователю {user_id}: {e}")
                
    except Exception as e:
        log.error(f"❌ Ошибка отправки уведомления о письме: {e}")
        import traceback
        log.error(traceback.format_exc())


async def email_monitor_task(bot):
    """
    Фоновая задача для мониторинга новых писем
    
    Args:
        bot: Telegram Bot instance
    """
    global processed_email_ids
    
    log.info(f"📧 Запуск мониторинга почты (интервал: {email_check_interval} сек)")
    
    while True:
        try:
            from services.helpers.email_helper import check_new_emails
            
            # Проверяем только самое новое письмо (limit=1 для скорости)
            emails = await check_new_emails(since_days=1, limit=1)
            
            if emails:
                # Берем только самое новое письмо (первое в списке)
                email_data = emails[0]
                email_id = email_data.get("id", "")
                
                # Проверяем, не обрабатывали ли уже это письмо
                if email_id and email_id not in processed_email_ids:
                    # Отправляем уведомление только о самом новом письме
                    await send_email_notification(bot, email_data)
                    processed_email_ids.add(email_id)
                    log.info(f"📧 Новое письмо обнаружено: {email_data.get('subject', 'Без темы')}")
            
            # Ждем перед следующей проверкой
            await asyncio.sleep(email_check_interval)
            
        except Exception as e:
            log.error(f"❌ Ошибка в мониторинге почты: {e}")
            import traceback
            log.error(traceback.format_exc())
            # При ошибке ждем перед следующей попыткой
            await asyncio.sleep(email_check_interval)
