"""
Basic команды
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.storage.email_subscribers import add_email_subscriber
import logging

log = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "без username"
    first_name = update.message.from_user.first_name or "без имени"
    
    # Логируем команду /start
    log.info(f"🚀 КОМАНДА /start: user_id={user_id}, username=@{username}, name={first_name}")
    
    # Автоматически подписываем пользователя на уведомления о почте
    add_email_subscriber(user_id)
    
    keyboard = [
        [InlineKeyboardButton("📚 База знаний", callback_data="menu_knowledge_base")],
        [InlineKeyboardButton("📋 WEEK", callback_data="menu_projects")],
        [InlineKeyboardButton("🛠 Инструменты", callback_data="menu_tools")],
        [InlineKeyboardButton("📧 Ответить на последний мейл", callback_data="email_reply_last")],
        [InlineKeyboardButton("💬 Чат с AI", callback_data="chat")],
        [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "✨ *Добро пожаловать! Я AI-ассистент Анастасии Новосёловой* ✨\n\n"
        "🎯 *Что я умею:*\n"
        "• 🔍 Искать в базе знаний (методики, кейсы, шаблоны)\n"
        "• 📝 Генерировать коммерческие предложения\n"
        "• 📊 Показывать статистику базы знаний\n"
        "• 📚 Просматривать документы в базе\n"
        "• 💬 Отвечать на вопросы с использованием базы знаний\n"
        "• 📋 Управлять проектами и задачами\n"
        "• 📧 Отвечать на последний мейл\n\n"
        "📬 *Уведомления:*\n"
        "Уведомления о новых письмах будут поступать в чат по мере их поступления.\n\n"
        "Выберите раздел:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 База знаний", callback_data="menu_knowledge_base")],
        [InlineKeyboardButton("📋 WEEK", callback_data="menu_projects")],
        [InlineKeyboardButton("🛠 Инструменты", callback_data="menu_tools")],
        [InlineKeyboardButton("📧 Ответить на последний мейл", callback_data="email_reply_last")],
        [InlineKeyboardButton("💬 Чат с AI", callback_data="chat")],
        [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🏠 *Главное меню*\n\n"
        "📚 *База знаний* - поиск, документы, статистика\n"
        "📋 *WEEK* - управление проектами и задачами\n"
        "🛠 *Инструменты* - генерация КП, суммаризация\n"
        "📧 *Ответить на последний мейл* - быстрый ответ на последнее письмо\n"
        "💬 *Чат с AI* - общение с AI-помощником\n"
        "❓ *Помощь* - справочная информация",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def show_main_menu(query):
    """Показать главное меню"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [InlineKeyboardButton("📚 База знаний", callback_data="menu_knowledge_base")],
        [InlineKeyboardButton("📋 WEEK", callback_data="menu_projects")],
        [InlineKeyboardButton("🛠 Инструменты", callback_data="menu_tools")],
        [InlineKeyboardButton("📧 Ответить на последний мейл", callback_data="email_reply_last")],
        [InlineKeyboardButton("💬 Чат с AI", callback_data="chat")],
        [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🏠 *Главное меню*\n\n"
        "📚 *База знаний* - поиск, документы, статистика\n"
        "📋 *WEEK* - управление проектами и задачами\n"
        "🛠 *Инструменты* - генерация КП, суммаризация\n"
        "📧 *Ответить на последний мейл* - быстрый ответ на последнее письмо\n"
        "💬 *Чат с AI* - общение с AI-помощником\n"
        "❓ *Помощь* - справочная информация",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status - статус проектов"""
    try:
        from services.helpers.weeek_helper import get_project_deadlines
        
        # Получаем проекты с ближайшими дедлайнами
        upcoming_tasks = await get_project_deadlines(days_ahead=7)
        
        if upcoming_tasks:
            text = "📋 *Статус проектов и задачи*\n\n"
            text += f"Задачи с дедлайнами на ближайшие 7 дней:\n\n"
            
            for task in upcoming_tasks[:10]:  # Показываем первые 10
                task_name = task.get("name", "Задача")
                due_date = task.get("due_date", "Не указан")
                status = task.get("status", "Не указан")
                text += f"• *{task_name}*\n"
                text += f"  Дедлайн: {due_date}\n"
                text += f"  Статус: {status}\n\n"
        else:
            text = "📋 *Статус проектов*\n\n"
            text += "Нет задач с ближайшими дедлайнами.\n\n"
            text += "Используйте WEEEK для управления проектами."
        
        await update.message.reply_text(text, parse_mode='Markdown')
    except Exception as e:
        log.error(f"❌ Ошибка получения статуса: {e}")
        await update.message.reply_text(
            "📋 *Статус проектов*\n\n"
            "Используйте WEEEK для управления проектами и задачами.",
            parse_mode='Markdown'
        )

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /myid - показать Telegram ID пользователя"""
    try:
        user = update.message.from_user
        user_id = user.id
        username = user.username or "не указан"
        first_name = user.first_name or "не указано"
        last_name = user.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        
        text = f"🆔 *Ваш Telegram ID*\n\n"
        text += f"*ID:* `{user_id}`\n"
        text += f"*Имя:* {full_name}\n"
        text += f"*Username:* @{username}\n\n"
        text += f"💡 *Использование:*\n"
        text += f"Добавьте этот ID в `.env`:\n"
        text += f"```\nTELEGRAM_ADMIN_IDS=5305427956,{user_id}\n```\n\n"
        text += f"Или используйте для настройки уведомлений о почте."
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        log.info(f"🆔 Пользователь {user_id} (@{username}) запросил свой ID")
        
    except Exception as e:
        log.error(f"❌ Ошибка получения ID: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
