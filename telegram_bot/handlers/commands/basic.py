"""
Basic команды
"""
from telegram import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    WebAppInfo,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton
)
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.storage.email_subscribers import add_email_subscriber
import logging

log = logging.getLogger(__name__)


def get_reply_keyboard():
    """Создает Reply Keyboard (кнопки снизу) с основными командами"""
    keyboard = [
        [
            KeyboardButton("📚 База знаний"),
            KeyboardButton("📋 Проекты")
        ],
        [
            KeyboardButton("🛠 Инструменты"),
            KeyboardButton("💬 Чат с AI")
        ],
        [
            KeyboardButton("📧 Email"),
            KeyboardButton("❓ Помощь")
        ],
        [
            KeyboardButton("🏠 Главное меню"),
            KeyboardButton("📊 Статус")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,  # Автоматически подстраивает размер кнопок
        one_time_keyboard=False,  # Кнопки остаются видимыми после нажатия
        input_field_placeholder="Выберите действие или введите сообщение..."
    )


async def show_keyboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /show_keyboard - показать кнопки меню снизу"""
    try:
        reply_markup = get_reply_keyboard()
        await update.message.reply_text(
            "⌨️ *Кнопки меню показаны*\n\n"
            "Используйте кнопки снизу для быстрого доступа к функциям бота.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        log.info(f"✅ Кнопки меню показаны для user_id={update.message.from_user.id}")
    except Exception as e:
        log.error(f"❌ Ошибка показа клавиатуры: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def hide_keyboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /hide_keyboard - скрыть кнопки меню снизу"""
    try:
        reply_markup = ReplyKeyboardRemove(remove_keyboard=True)
        await update.message.reply_text(
            "⌨️ *Кнопки меню скрыты*\n\n"
            "Используйте /show_keyboard чтобы показать их снова.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        log.info(f"✅ Кнопки меню скрыты для user_id={update.message.from_user.id}")
    except Exception as e:
        log.error(f"❌ Ошибка скрытия клавиатуры: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        user_id = update.message.from_user.id
        username = update.message.from_user.username or "без username"
        first_name = update.message.from_user.first_name or "без имени"
        
        # Логируем команду /start
        log.info(f"🚀 КОМАНДА /start: user_id={user_id}, username=@{username}, name={first_name}")
        
        # Автоматически подписываем пользователя на уведомления о почте
        try:
            add_email_subscriber(user_id)
        except Exception as e:
            log.warning(f"⚠️ Ошибка подписки на email уведомления: {e}")
        
        # Группируем кнопки по 2 в ряд для компактности
        from telegram_bot.config import MINI_APP_URL
        
        keyboard = [
            [
                InlineKeyboardButton("📚 База знаний", callback_data="menu_knowledge_base"),
                InlineKeyboardButton("📋 Проекты", callback_data="menu_projects")
            ],
            [
                InlineKeyboardButton("🛠 Инструменты", callback_data="menu_tools"),
                InlineKeyboardButton("💬 Чат с AI", callback_data="chat")
            ],
            [
                InlineKeyboardButton("📧 Ответить на мейл", callback_data="email_reply_last"),
                InlineKeyboardButton("❓ Помощь", callback_data="menu_help")
            ]
        ]
        
        # Добавляем кнопку Web App если URL настроен
        if MINI_APP_URL:
            log.info(f"🌐 Добавлена кнопка Mini App с URL: {MINI_APP_URL}")
            keyboard.append([
                InlineKeyboardButton(
                    "🌐 Открыть Mini App",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                )
            ])
        else:
            log.warning("⚠️ Mini App URL не настроен, кнопка не добавлена")
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Улучшенное форматирование с разделителями
        welcome_text = (
            "✨ *Добро пожаловать!*\n"
            "Я Анастасия Новосёлова\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎯 *Возможности:*\n\n"
            "🔍 *База знаний*\n"
            "   Поиск методик, кейсов, шаблонов\n\n"
            "📋 *Проекты*\n"
            "   Управление задачами в WEEEK\n\n"
            "🛠 *Инструменты*\n"
            "   Генерация КП, суммаризация\n\n"
            "💬 *Чат с AI*\n"
            "   Общение с умным помощником\n\n"
            "📧 *Email*\n"
            "   Быстрые ответы на письма\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📬 Уведомления о новых письмах приходят автоматически"
        )
        
        # Отправляем приветственное сообщение с inline кнопками
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Также показываем Reply Keyboard (кнопки снизу)
        reply_keyboard = get_reply_keyboard()
        await update.message.reply_text(
            "⌨️ *Кнопки меню активированы*\n\n"
            "Используйте кнопки снизу для быстрого доступа.\n"
            "Или используйте /hide_keyboard чтобы скрыть их.",
            parse_mode='Markdown',
            reply_markup=reply_keyboard
        )
        
        log.info(f"✅ Команда /start выполнена успешно для user_id={user_id}")
        
    except Exception as e:
        log.error(f"❌ Ошибка в обработчике /start: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Пытаемся отправить сообщение об ошибке
        try:
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке команды /start. Попробуйте позже."
            )
        except:
            pass

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Компактная группировка кнопок
    from telegram_bot.config import MINI_APP_URL
    
    keyboard = [
        [
            InlineKeyboardButton("📚 База знаний", callback_data="menu_knowledge_base"),
            InlineKeyboardButton("📋 Проекты", callback_data="menu_projects")
        ],
        [
            InlineKeyboardButton("🛠 Инструменты", callback_data="menu_tools"),
            InlineKeyboardButton("💬 Чат с AI", callback_data="chat")
        ],
        [
            InlineKeyboardButton("📧 Ответить на мейл", callback_data="email_reply_last"),
            InlineKeyboardButton("❓ Помощь", callback_data="menu_help")
        ]
    ]
    
    # Добавляем кнопку Web App если URL настроен
    if MINI_APP_URL:
        keyboard.append([
            InlineKeyboardButton(
                "🌐 Открыть Mini App",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    menu_text = (
        "🏠 *Главное меню*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📚 *База знаний* — поиск и документы\n"
        "📋 *Проекты* — управление задачами\n"
        "🛠 *Инструменты* — генерация и анализ\n"
        "💬 *Чат с AI* — умный помощник\n"
        "📧 *Email* — быстрые ответы\n"
        "❓ *Помощь* — справочная информация"
    )
    
    await update.message.reply_text(
        menu_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def show_main_menu(query):
    """Показать главное меню с улучшенным дизайном"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from telegram_bot.config import MINI_APP_URL
    
    # Компактная группировка кнопок
    keyboard = [
        [
            InlineKeyboardButton("📚 База знаний", callback_data="menu_knowledge_base"),
            InlineKeyboardButton("📋 Проекты", callback_data="menu_projects")
        ],
        [
            InlineKeyboardButton("🛠 Инструменты", callback_data="menu_tools"),
            InlineKeyboardButton("💬 Чат с AI", callback_data="chat")
        ],
        [
            InlineKeyboardButton("📧 Ответить на мейл", callback_data="email_reply_last"),
            InlineKeyboardButton("❓ Помощь", callback_data="menu_help")
        ]
    ]
    
    # Добавляем кнопку Web App если URL настроен
    if MINI_APP_URL:
        keyboard.append([
            InlineKeyboardButton(
                "🌐 Открыть Mini App",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    menu_text = (
        "🏠 *Главное меню*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📚 *База знаний* — поиск и документы\n"
        "📋 *Проекты* — управление задачами\n"
        "🛠 *Инструменты* — генерация и анализ\n"
        "💬 *Чат с AI* — умный помощник\n"
        "📧 *Email* — быстрые ответы\n"
        "❓ *Помощь* — справочная информация"
    )
    
    await query.edit_message_text(
        menu_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status - статус проектов"""
    try:
        from services.helpers.weeek_helper import get_project_deadlines
        
        # Получаем проекты с ближайшими дедлайнами
        upcoming_tasks = await get_project_deadlines(days_ahead=7)
        
        keyboard = [
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if upcoming_tasks:
            text = (
                "📊 *Статус проектов*\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 *Дедлайны на 7 дней*\n\n"
            )
            
            for task in upcoming_tasks[:10]:  # Показываем первые 10
                task_name = task.get("name", "Задача")
                due_date = task.get("due_date", "Не указан")
                status = task.get("status", "Активна")
                
                # Иконка статуса
                status_icon = "✅" if status == "Завершена" else "⏳"
                
                text += f"{status_icon} *{task_name}*\n"
                text += f"   📅 {due_date}\n"
                text += f"   📊 {status}\n\n"
            
            if len(upcoming_tasks) > 10:
                text += f"_...и еще {len(upcoming_tasks) - 10} задач_"
        else:
            text = (
                "📊 *Статус проектов*\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "✅ Нет задач с ближайшими дедлайнами\n\n"
                "Используйте WEEEK для управления проектами."
            )
        
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    except Exception as e:
        log.error(f"❌ Ошибка получения статуса: {e}")
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📋 *Статус проектов*\n\n"
            "Используйте WEEEK для управления проектами и задачами.",
            parse_mode='Markdown',
            reply_markup=reply_markup
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
