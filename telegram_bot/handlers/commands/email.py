"""
Email команды
"""
from typing import Dict
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
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
                
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"✅ *Найдено новое письмо*\n\n"
                    f"*Тема:* {email_data.get('subject', 'Без темы')}\n"
                    f"*От:* {email_data.get('from', 'Неизвестно')}\n\n"
                    f"Уведомление отправлено всем подписчикам.",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"📧 *Самое новое письмо уже обработано*\n\n"
                    f"*Тема:* {email_data.get('subject', 'Без темы')}\n\n"
                    f"Используйте кнопки в уведомлениях для работы с письмами.",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        else:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📧 Новых писем нет или email недоступен", reply_markup=reply_markup)
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
            "Пример: `/email_draft нужна помощь с автоматизацией HR-процессов`",
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
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Разбиваем длинное сообщение если нужно
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for i, part in enumerate(parts):
                # Добавляем кнопку только к последнему сообщению
                if i == len(parts) - 1:
                    await update.message.reply_text(part, parse_mode='Markdown', reply_markup=reply_markup)
                else:
                    await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    except Exception as e:
        log.error(f"❌ Ошибка подготовки черновика: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# ===================== EMAIL NOTIFICATIONS =====================

# Кэш для хранения данных писем
email_cache: Dict[str, Dict] = {}

# Импортируем состояние для ответов на email из email_monitor
from telegram_bot.services.email_monitor import email_reply_state

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
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        log.info(f"❌ Пользователь {user_id} (@{username}) отписался от уведомлений")
        
    except Exception as e:
        log.error(f"❌ Ошибка отписки: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# ===================== EMAIL REPLY HANDLERS =====================

async def handle_email_reply_last(query):
    """Обработка кнопки 'Ответить на последний мейл'"""
    try:
        from services.helpers.email_helper import check_new_emails
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        user_id = query.from_user.id
        
        # Получаем последнее письмо
        emails = await check_new_emails(since_days=7, limit=1)
        
        if not emails:
            await query.answer("📭 Новых писем не найдено", show_alert=True)
            return
        
        email_data = emails[0]
        email_id = email_data.get("id", "")
        from_addr = email_data.get("from", "")
        subject = email_data.get("subject", "Без темы")
        body = email_data.get("body", email_data.get("preview", ""))
        
        # Сохраняем в кэш
        email_cache[email_id] = email_data
        
        # Показываем меню выбора типа ответа
        text = f"📧 *Ответить на письмо*\n\n"
        text += f"*От:* {from_addr}\n"
        text += f"*Тема:* {subject}\n\n"
        text += "Выберите тип ответа:"
        
        keyboard = [
            [
                InlineKeyboardButton("✉️ Первичный ответ", callback_data=f"email_reply_primary_{email_id}"),
                InlineKeyboardButton("💬 Уточняющий", callback_data=f"email_reply_followup_{email_id}")
            ],
            [
                InlineKeyboardButton("📎 С КП", callback_data=f"email_reply_proposal_{email_id}"),
                InlineKeyboardButton("📊 С отчетом", callback_data=f"email_reply_report_{email_id}")
            ],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.answer()
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        log.error(f"❌ Ошибка handle_email_reply_last: {e}")
        import traceback
        log.error(traceback.format_exc())
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


async def handle_email_reply(query, email_id: str):
    """Обработка кнопки 'Подготовить ответ' для письма"""
    try:
        from services.agents.lead_processor import generate_proposal
        
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        subject = email_data.get("subject", "")
        body = email_data.get("body", email_data.get("preview", ""))
        
        await query.answer("⏳ Генерирую черновик ответа...")
        
        # Генерируем черновик ответа
        draft = await generate_proposal(body, lead_contact={})
        
        text = f"📧 *Черновик ответа на письмо:*\n\n"
        text += f"*Тема:* {subject}\n\n"
        text += f"{draft}\n\n"
        text += "💡 Вы можете отредактировать и отправить этот черновик."
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton("✉️ Отправить как есть", callback_data=f"email_send_reply_{email_id}"),
                InlineKeyboardButton("✏️ Редактировать", callback_data=f"email_edit_reply_{email_id}")
            ],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"email_reply_last")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        log.error(f"❌ Ошибка handle_email_reply: {e}")
        import traceback
        log.error(traceback.format_exc())
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


async def handle_email_send_reply(query, email_id: str):
    """Обработка отправки ответа на письмо"""
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        from_addr = email_data.get("from", "")
        subject = email_data.get("subject", "")
        
        # Сохраняем данные для отправки
        user_id = query.from_user.id
        email_reply_state[user_id] = {
            'email_id': email_id,
            'to': from_addr,
            'subject': subject,
            'reply_type': 'primary'
        }
        
        text = f"📧 *Отправить ответ на письмо*\n\n"
        text += f"*Кому:* {from_addr}\n"
        text += f"*Тема:* Re: {subject}\n\n"
        text += "💬 *Введите текст ответа:*\n\n"
        text += "💡 Вы можете отправить текст ответа прямо в следующем сообщении.\n"
        text += "Или используйте /cancel для отмены."
        
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=f"email_cancel_{email_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer("💬 Введите текст ответа")
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        log.error(f"❌ Ошибка handle_email_send_reply: {e}")
        import traceback
        log.error(traceback.format_exc())
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


async def handle_email_proposal(query, email_id: str):
    """Обработка отправки письма с КП"""
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        # Показываем индикатор печати
        await query.bot.send_chat_action(chat_id=query.message.chat.id, action=ChatAction.TYPING)
        
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        from_addr = email_data.get("from", "")
        subject = email_data.get("subject", "")
        body = email_data.get("body", email_data.get("preview", ""))
        
        await query.answer("⏳ Генерирую КП и отправляю письмо...")
        
        # Используем новый сервис для отправки письма с КП
        from telegram_bot.services.email_reply_service import send_proposal_email
        
        result = await send_proposal_email(
            to_email=from_addr,
            subject=subject,
            lead_request=body,
            lead_contact={"email": from_addr},
            email_id=email_id
        )
        
        if result:
            text = f"✅ *Письмо с КП отправлено*\n\n"
            text += f"*Кому:* {from_addr}\n"
            text += f"*Тема:* Re: {subject}\n\n"
            text += "📎 К письму прикреплено коммерческое предложение."
        else:
            text = f"❌ *Не удалось отправить письмо*\n\n"
            text += "Попробуйте позже или отправьте вручную."
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"email_reply_last")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        log.error(f"❌ Ошибка handle_email_proposal: {e}")
        import traceback
        log.error(traceback.format_exc())
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


async def handle_email_task(query, email_id: str):
    """Обработка создания задачи из письма"""
    await query.answer("⚠️ Функция временно недоступна", show_alert=True)


async def handle_email_done(query, email_id: str):
    """Обработка отметки письма как выполненного"""
    await query.answer("✅ Письмо отмечено как выполненное")
    await query.edit_message_text("✅ Письмо обработано")


async def handle_email_full(query, email_id: str):
    """Показать полный текст письма"""
    try:
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        subject = email_data.get("subject", "")
        from_addr = email_data.get("from", "")
        body = email_data.get("body", email_data.get("preview", ""))
        
        text = f"📧 *Полный текст письма*\n\n"
        text += f"*От:* {from_addr}\n"
        text += f"*Тема:* {subject}\n\n"
        text += f"{body[:3000]}"
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"email_reply_last")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer()
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        log.error(f"❌ Ошибка handle_email_full: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


async def handle_email_create_task(query, email_id: str, project_id: int):
    """Создание задачи из письма"""
    await query.answer("⚠️ Функция временно недоступна", show_alert=True)


async def handle_email_reply_primary(query, email_id: str):
    """Обработка первичного ответа"""
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        # Показываем индикатор печати
        await query.bot.send_chat_action(chat_id=query.message.chat.id, action=ChatAction.TYPING)
        
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        from_addr = email_data.get("from", "")
        subject = email_data.get("subject", "")
        
        # Сохраняем данные для отправки
        user_id = query.from_user.id
        email_reply_state[user_id] = {
            'email_id': email_id,
            'to': from_addr,
            'subject': subject,
            'reply_type': 'primary'
        }
        
        text = f"📧 *Первичный ответ на письмо*\n\n"
        text += f"*Кому:* {from_addr}\n"
        text += f"*Тема:* Re: {subject}\n\n"
        text += "💬 *Введите текст первичного ответа:*\n\n"
        text += "💡 Это первое письмо клиенту. Будьте дружелюбны и информативны."
        
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=f"email_cancel_{email_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer("💬 Введите текст ответа")
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        log.error(f"❌ Ошибка handle_email_reply_primary: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


async def handle_email_reply_followup(query, email_id: str):
    """Обработка уточняющего ответа"""
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        # Показываем индикатор печати
        await query.bot.send_chat_action(chat_id=query.message.chat.id, action=ChatAction.TYPING)
        
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        from_addr = email_data.get("from", "")
        subject = email_data.get("subject", "")
        
        # Сохраняем данные для отправки
        user_id = query.from_user.id
        email_reply_state[user_id] = {
            'email_id': email_id,
            'to': from_addr,
            'subject': subject,
            'reply_type': 'followup'
        }
        
        text = f"📧 *Уточняющий ответ на письмо*\n\n"
        text += f"*Кому:* {from_addr}\n"
        text += f"*Тема:* Re: {subject}\n\n"
        text += "💬 *Введите текст уточняющего ответа:*\n\n"
        text += "💡 Это продолжение диалога. Уточните детали или ответьте на вопросы."
        
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=f"email_cancel_{email_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer("💬 Введите текст ответа")
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        log.error(f"❌ Ошибка handle_email_reply_followup: {e}")
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


async def handle_email_reply_report(query, email_id: str):
    """Обработка отправки письма с отчетом"""
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        # Показываем индикатор печати
        await query.bot.send_chat_action(chat_id=query.message.chat.id, action=ChatAction.TYPING)
        
        email_data = email_cache.get(email_id)
        if not email_data:
            await query.answer("❌ Данные письма не найдены", show_alert=True)
            return
        
        from_addr = email_data.get("from", "")
        subject = email_data.get("subject", "")
        
        await query.answer("⏳ Генерирую отчет и отправляю письмо...")
        
        # Используем новый сервис для отправки письма с отчетом
        from telegram_bot.services.email_reply_service import send_report_email
        
        # Для генерации отчета нужны данные проекта
        # Пока используем базовые данные
        project_data = {
            "name": subject,
            "status": "В работе",
            "description": email_data.get("body", email_data.get("preview", ""))
        }
        
        result = await send_report_email(
            to_email=from_addr,
            subject=subject,
            project_data=project_data,
            email_id=email_id
        )
        
        if result:
            text = f"✅ *Письмо с отчетом отправлено*\n\n"
            text += f"*Кому:* {from_addr}\n"
            text += f"*Тема:* Re: {subject}\n\n"
            text += "📊 К письму прикреплен отчет по проекту."
        else:
            text = f"❌ *Не удалось отправить письмо*\n\n"
            text += "Попробуйте позже или отправьте вручную."
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"email_reply_last")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        log.error(f"❌ Ошибка handle_email_reply_report: {e}")
        import traceback
        log.error(traceback.format_exc())
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


async def handle_email_cancel(query, email_id: str):
    """Отмена действия с письмом"""
    user_id = query.from_user.id
    if user_id in email_reply_state:
        email_reply_state.pop(user_id, None)
    await query.answer("❌ Действие отменено")
    await query.edit_message_text("❌ Отправка ответа отменена")
