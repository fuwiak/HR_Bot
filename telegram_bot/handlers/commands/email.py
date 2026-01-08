"""
Email команды
"""
from typing import Dict
from telegram import Update
from telegram.ext import ContextTypes
import logging

log = logging.getLogger(__name__)

async def email_check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /email_check - проверка новых писем с уведомлениями"""
    try:
        from services.helpers.email_helper import check_new_emails
        from telegram_bot.services.email_monitor import processed_email_ids, send_email_notification

        await update.message.reply_text("⏳ Проверяю самое новое письмо...")

        # Проверяем только самое новое письмо (limit=1 для скорости)
        emails = await check_new_emails(since_days=1, limit=1)
        
        if emails:
            # Берем только самое новое письмо (первое в списке)
            email_data = emails[0]
            email_id = email_data.get("id", "")
            
            # Проверяем, не обрабатывали ли уже это письмо
            if email_id and email_id not in processed_email_ids:
                # Отправляем уведомление только о самом новом письме
                await send_email_notification(context.bot, email_data)
                processed_email_ids.add(email_id)
                
                await update.message.reply_text(
                    f"✅ *Найдено новое письмо*\n\n"
                    f"*Тема:* {email_data.get('subject', 'Без темы')}\n"
                    f"*От:* {email_data.get('from', 'Неизвестно')}\n\n"
                    f"Уведомление отправлено всем подписчикам.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"📧 *Самое новое письмо уже обработано*\n\n"
                    f"*Тема:* {email_data.get('subject', 'Без темы')}\n\n"
                    f"Используйте кнопки в уведомлениях для работы с письмами.",
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text("📧 Новых писем нет или email недоступен")
    except Exception as e:
        log.error(f"❌ Ошибка проверки email: {e}")
        import traceback
        log.error(traceback.format_exc())
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def email_draft_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /email_draft - подготовка ответа на письмо"""
    request_text = " ".join(context.args) if context.args else ""
    
    if not request_text:
        await update.message.reply_text(
            "❌ Укажите тему письма или запрос клиента.\n"
            "Использование: `/email_draft [текст запроса]`\n\n"
            "Пример: `/email_draft нужна помощь с подбором персонала`",
            parse_mode='Markdown'
        )
        return
    
    try:
        from lead_processor import generate_proposal
        
        await update.message.reply_text("⏳ Готовлю черновик ответа на письмо...")
        
        # Генерируем ответ используя generate_proposal
        draft = await generate_proposal(request_text, lead_contact={})
        
        text = f"📧 *Черновик ответа на письмо:*\n\n{draft}\n\n"
        text += "💡 Отредактируйте черновик и отправьте через WEEEK или почтовый клиент."
        
        # Разбиваем длинное сообщение если нужно
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        log.error(f"❌ Ошибка подготовки черновика: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# ===================== EMAIL NOTIFICATIONS =====================

# Кэш для хранения данных писем
email_cache: Dict[str, Dict] = {}

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /unsubscribe - отписаться от уведомлений о почте"""
    try:
        from telegram_bot.storage.email_subscribers import remove_email_subscriber
        
        user_id = update.message.from_user.id
        username = update.message.from_user.username or "без username"
        
        # Удаляем пользователя из подписчиков
        remove_email_subscriber(user_id)
        
        text = "❌ *Вы отписаны от уведомлений о почте*\n\n"
        text += "Вы больше не будете получать уведомления о новых письмах.\n\n"
        text += "Чтобы снова подписаться, используйте команду /start"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        log.info(f"❌ Пользователь {user_id} (@{username}) отписался от уведомлений")
        
    except Exception as e:
        log.error(f"❌ Ошибка отписки: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
