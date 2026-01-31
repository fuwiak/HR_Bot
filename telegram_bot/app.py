"""
Главный файл Telegram бота (декомпозированная версия)
"""
import os
import sys
import logging
import asyncio
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для импорта модулей
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# Импортируем конфигурацию
from telegram_bot.config import (
    TELEGRAM_BOT_TOKEN,
    PORT,
    WEBHOOK_URL,
    USE_WEBHOOK,
)

# Импортируем storage модули
from telegram_bot.storage.memory import get_recent_history
from telegram_bot.storage.email_subscribers import add_email_subscriber

# Импортируем integrations
from telegram_bot.integrations.qdrant import QDRANT_AVAILABLE, index_services
from telegram_bot.integrations.google_sheets import get_services

# Импортируем handlers из новых модулей
from telegram_bot.handlers import (
    start,
    menu,
    button_callback,
    reply,
    rag_search_command,
    rag_stats_command,
    rag_docs_command,
    rag_upload_command,
    demo_proposal_command,
    summary_command,
    status_command,
    weeek_info_command,
    weeek_create_task_command,
    weeek_projects_command,
    weeek_create_project_command,
    weeek_update_command,
    weeek_tasks_command,
    yadisk_list_command,
    yadisk_search_command,
    yadisk_recent_command,
    myid_command,
    unsubscribe_command,
    email_check_command,
    email_draft_command,
    hypothesis_command,
    report_command,
    upload_document_command,
    handle_document,
)

# ===================== LOGGING ========================
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger()

# Попытка импорта PostgreSQL модуля
try:
    from backend.database import init_db
    DATABASE_AVAILABLE = True
    log.info("✅ PostgreSQL модуль загружен")
except ImportError as e:
    DATABASE_AVAILABLE = False
    log.warning(f"⚠️ PostgreSQL модуль не доступен: {e}")

# Попытка импорта Redis модуля
try:
    from services.helpers.redis_helper import (
        sync_all_to_postgres,
        REDIS_AVAILABLE
    )
    REDIS_AVAILABLE_IMPORT = REDIS_AVAILABLE
    if REDIS_AVAILABLE_IMPORT:
        log.info("✅ Redis модуль загружен")
except ImportError as e:
    REDIS_AVAILABLE_IMPORT = False
    log.warning(f"⚠️ Redis модуль не доступен: {e}")
    def sync_all_to_postgres(*args, **kwargs): return None

# Попытка импорта LangGraph Conversation Workflow
try:
    from backend.api.services.langgraph_conversation_workflow import (
        get_conversation_workflow,
        query_with_conversation_workflow,
        LANGGRAPH_AVAILABLE as LANGGRAPH_CONV_AVAILABLE
    )
    log.info("✅ LangGraph Conversation Workflow загружен")
except ImportError as e:
    LANGGRAPH_CONV_AVAILABLE = False
    log.warning(f"⚠️ LangGraph Conversation Workflow не доступен: {e}")

# Email monitoring state
from telegram_bot.services.email_monitor import (
    processed_email_ids,
    email_check_interval,
    email_reply_state,
    email_monitor_task
)

# HR Time news monitoring state
from telegram_bot.services.hrtime_news_monitor import (
    processed_news_ids,
    news_check_interval,
    hrtime_news_monitor_task
)

# ===================== RUN BOT ========================
def main():
    # Убеждаемся, что filters доступен (импортирован глобально в строке 21)
    global filters
    # Инициализация PostgreSQL базы данных
    if DATABASE_AVAILABLE:
        try:
            if init_db():
                log.info("✅ PostgreSQL база данных инициализирована")
            else:
                log.warning("⚠️ Не удалось инициализировать PostgreSQL, используем память")
        except Exception as e:
            log.error(f"❌ Ошибка инициализации PostgreSQL: {e}")
            log.warning("⚠️ Используем память вместо PostgreSQL")
    else:
        log.info("ℹ️ PostgreSQL не настроен, используем память для хранения данных")
    
    # Проверяем доступность Qdrant библиотек еще раз при старте
    try:
        import qdrant_client
        log.info("✅ Qdrant библиотеки доступны: qdrant-client")
    except ImportError as e:
        log.warning(f"⚠️ Qdrant библиотеки не установлены: {e}")
        log.warning("⚠️ Для работы векторного поиска установите: pip install qdrant-client")
    
    # Инициализация: индексируем услуги в Qdrant в фоновом режиме
    def index_services_background():
        """Индексировать услуги в Qdrant в фоновом потоке"""
        try:
            import time
            # Даем время для инициализации Google Sheets
            time.sleep(2)
            log.info("🔄 Фоновая индексация Qdrant: чтение услуг из Google Sheets...")
            services = get_services()
            if services and len(services) > 0:
                log.info(f"📋 Прочитано {len(services)} услуг из Google Sheets, начинаю индексацию в Qdrant...")
                if index_services(services):
                    log.info(f"✅ Успешно проиндексировано {len(services)} услуг в Qdrant")
                else:
                    log.warning("⚠️ Не удалось проиндексировать услуги в Qdrant")
            else:
                log.debug("ℹ️ Нет услуг для индексации в Qdrant (возможно Google Sheets еще не загружены или пусты)")
        except Exception as e:
            log.error(f"❌ Ошибка индексации Qdrant в фоне: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
    
    # Запускаем индексацию в фоновом потоке
    if QDRANT_AVAILABLE:
        import threading
        index_thread = threading.Thread(target=index_services_background, daemon=True)
        index_thread.start()
        log.info("🔄 Запущена фоновая индексация Qdrant (бот запускается, не ждет завершения)")
    
    # Запускаем фоновую синхронизацию Redis -> PostgreSQL
    if REDIS_AVAILABLE_IMPORT and DATABASE_AVAILABLE:
        def sync_redis_to_postgres_background():
            """Фоновая синхронизация Redis -> PostgreSQL каждые 5 минут"""
            import time
            while True:
                try:
                    time.sleep(300)  # 5 минут
                    log.info("🔄 Начало фоновой синхронизации Redis -> PostgreSQL...")
                    sync_all_to_postgres()
                    log.info("✅ Фоновая синхронизация Redis -> PostgreSQL завершена")
                except Exception as e:
                    log.error(f"❌ Ошибка фоновой синхронизации: {e}")
        
        import threading
        sync_thread = threading.Thread(target=sync_redis_to_postgres_background, daemon=True)
        sync_thread.start()
        log.info("🔄 Запущена фоновая синхронизация Redis -> PostgreSQL (каждые 5 минут)")
    
    # Start Telegram bot с поддержкой concurrent updates для масштабирования
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).concurrent_updates(True).build()
    
    # Command handlers
    log.info("📝 Регистрация обработчиков команд...")
    app.add_handler(CommandHandler("start", start))
    log.info("✅ Обработчик /start зарегистрирован")
    app.add_handler(CommandHandler("menu", menu))
    log.info("✅ Обработчик /menu зарегистрирован")
    
    # New commands for demonstration
    app.add_handler(CommandHandler("rag_search", rag_search_command))
    app.add_handler(CommandHandler("rag_stats", rag_stats_command))
    app.add_handler(CommandHandler("rag_docs", rag_docs_command))
    app.add_handler(CommandHandler("rag_upload", rag_upload_command))
    app.add_handler(CommandHandler("demo_proposal", demo_proposal_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("status", status_command))
    
    # WEEEK commands
    app.add_handler(CommandHandler("weeek_info", weeek_info_command))
    app.add_handler(CommandHandler("weeek_task", weeek_create_task_command))
    app.add_handler(CommandHandler("weeek_projects", weeek_projects_command))
    app.add_handler(CommandHandler("weeek_create_project", weeek_create_project_command))
    app.add_handler(CommandHandler("weeek_update", weeek_update_command))
    app.add_handler(CommandHandler("weeek_tasks", weeek_tasks_command))

    # Yandex Disk commands
    app.add_handler(CommandHandler("yadisk_list", yadisk_list_command))
    app.add_handler(CommandHandler("yadisk_search", yadisk_search_command))
    app.add_handler(CommandHandler("yadisk_recent", yadisk_recent_command))
    
    # Utility commands
    app.add_handler(CommandHandler("myid", myid_command))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    
    # Email commands
    app.add_handler(CommandHandler("email_check", email_check_command))
    app.add_handler(CommandHandler("email_draft", email_draft_command))

    # Additional commands
    app.add_handler(CommandHandler("hypothesis", hypothesis_command))
    app.add_handler(CommandHandler("report", report_command))
    
    # Document upload command and handler
    app.add_handler(CommandHandler("upload", upload_document_command))
    # Используем filters из глобального импорта (строка 21)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Callback query handler for inline buttons
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Channel post handler for @HRTime_bot
    # Примечание: channel_post обрабатывается через Update в основном обработчике reply
    # MessageHandler не подходит для channel_post, так как он работает с message, а не update.channel_post
    try:
        from telegram_bot.handlers.channel.hrtime_channel_handler import handle_channel_post
        # channel_post обрабатывается в reply_handler.py
        log.info("ℹ️ Обработчик channel_post будет работать через reply_handler")
    except Exception as e:
        log.warning(f"⚠️ Не удалось загрузить обработчик канала: {e}")
        import traceback
        log.warning(traceback.format_exc())
    
    # Message handler for AI chat (должен быть последним!)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    
    # Запуск бота: webhook для production (Railway) или polling для локальной разработки
    async def start_bot():
        """Асинхронный запуск бота с webhook или polling"""
        # Функция для настройки grid menu (Bot Commands Menu)
        async def setup_bot_commands():
            """Настройка grid menu с командами бота"""
            commands = [
                BotCommand("start", "🚀 Начать работу с ботом"),
                BotCommand("menu", "🏠 Главное меню"),
                BotCommand("status", "📊 Статус проектов"),
                BotCommand("email_check", "📧 Проверить новые письма"),
                BotCommand("email_draft", "✉️ Подготовить ответ на письмо"),
                BotCommand("rag_search", "🔍 Поиск в базе знаний"),
                BotCommand("rag_docs", "📚 Список документов"),
                BotCommand("weeek_projects", "📋 Список проектов"),
                BotCommand("weeek_tasks", "✅ Список задач"),
                BotCommand("yadisk_list", "📁 Список файлов"),
                BotCommand("summary", "📝 Суммаризация текста"),
                BotCommand("demo_proposal", "💼 Демо КП"),
                BotCommand("hypothesis", "💡 Гипотеза"),
                BotCommand("report", "📊 Отчет"),
                BotCommand("upload", "📤 Загрузить документ"),
                BotCommand("myid", "🆔 Мой Telegram ID"),
                BotCommand("unsubscribe", "❌ Отписаться от уведомлений"),
            ]
            
            try:
                # Устанавливаем команды меню
                # Telegram автоматически создаст кнопку меню рядом с полем ввода,
                # которая может раскрываться (expand) и сворачиваться (collapse)
                await app.bot.set_my_commands(commands)
                log.info(f"✅ Grid menu установлен: {len(commands)} команд")
                log.info("✅ Bot Menu Button создан автоматически (expand/collapse доступно)")
            except Exception as e:
                log.error(f"❌ Ошибка установки grid menu: {e}")
                import traceback
                log.error(traceback.format_exc())
        
        if USE_WEBHOOK and WEBHOOK_URL:
            # Используем webhook для production
            webhook_path = f"/webhook/{TELEGRAM_BOT_TOKEN}"
            full_webhook_url = f"{WEBHOOK_URL.rstrip('/')}{webhook_path}"
            
            log.info(f"🌐 Настройка webhook: {full_webhook_url}")
            log.info(f"🔌 Порт: {PORT}")
            
            if not app.running:
                await app.initialize()
                await app.start()
            else:
                log.warning("⚠️ Приложение уже запущено, пропускаем повторный запуск")
            
            # Устанавливаем grid menu
            await setup_bot_commands()
            
            await app.bot.set_webhook(
                url=full_webhook_url,
                drop_pending_updates=True,
                max_connections=100,
                allowed_updates=["message", "channel_post", "callback_query"]
            )
            
            log.info(f"✅ Webhook установлен: {full_webhook_url}")
            
            # Запускаем фоновые задачи
            try:
                from services.agents.integrate_scenarios import start_background_tasks
                start_background_tasks(
                    telegram_bot=app.bot,
                    enable_hrtime=True,
                    enable_email=True,
                    enable_deadlines=True
                )
                log.info("✅ Фоновые задачи мониторинга запущены")
            except Exception as e:
                log.warning(f"⚠️ Не удалось запустить фоновые задачи: {e}")
            
            try:
                # Сохраняем задачу в переменную, чтобы она не была удалена сборщиком мусора
                email_task = asyncio.create_task(email_monitor_task(app.bot))
                # Сохраняем задачу в атрибут приложения для доступа из других мест
                app.email_monitor_task = email_task
                log.info("✅ Фоновая задача мониторинга почты запущена")
            except Exception as e:
                log.warning(f"⚠️ Не удалось запустить мониторинг почты: {e}")
                import traceback
                log.error(traceback.format_exc())
            
            try:
                # Запускаем мониторинг новостей HR Time
                news_task = asyncio.create_task(hrtime_news_monitor_task(app.bot))
                app.hrtime_news_monitor_task = news_task
                log.info("✅ Фоновая задача мониторинга новостей HR Time запущена")
            except Exception as e:
                log.warning(f"⚠️ Не удалось запустить мониторинг новостей HR Time: {e}")
                import traceback
                log.error(traceback.format_exc())
            
            await app.updater.start_webhook(
                listen="0.0.0.0",
                port=PORT,
                webhook_url=full_webhook_url,
                url_path=webhook_path
            )
            
            log.info(f"✅ Бот запущен с webhook на порту {PORT}")
            log.info(f"📡 Webhook URL: {full_webhook_url}")
            log.info("🚀 Готов к обработке обновлений от Telegram (concurrent_updates=True)")
            
            try:
                await asyncio.Event().wait()
            except (asyncio.CancelledError, KeyboardInterrupt):
                log.info("⏹️  Получен сигнал остановки...")
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
        else:
            # Используем polling для локальной разработки
            log.info("🔄 Используем polling (локальная разработка)")
            
            if not app.running:
                await app.initialize()
                await app.start()
            else:
                log.warning("⚠️ Приложение уже запущено, пропускаем повторный запуск")
            
            # Устанавливаем grid menu
            await setup_bot_commands()
            
            try:
                from services.agents.integrate_scenarios import start_background_tasks
                start_background_tasks(
                    telegram_bot=app.bot,
                    enable_hrtime=True,
                    enable_email=True,
                    enable_deadlines=True
                )
                log.info("✅ Фоновые задачи мониторинга запущены")
            except Exception as e:
                log.warning(f"⚠️ Не удалось запустить фоновые задачи: {e}")
            
            try:
                # Сохраняем задачу в переменную, чтобы она не была удалена сборщиком мусора
                email_task = asyncio.create_task(email_monitor_task(app.bot))
                # Сохраняем задачу в атрибут приложения для доступа из других мест
                app.email_monitor_task = email_task
                log.info("✅ Фоновая задача мониторинга почты запущена")
            except Exception as e:
                log.warning(f"⚠️ Не удалось запустить мониторинг почты: {e}")
                import traceback
                log.error(traceback.format_exc())
            
            try:
                # Запускаем мониторинг новостей HR Time
                news_task = asyncio.create_task(hrtime_news_monitor_task(app.bot))
                app.hrtime_news_monitor_task = news_task
                log.info("✅ Фоновая задача мониторинга новостей HR Time запущена")
            except Exception as e:
                log.warning(f"⚠️ Не удалось запустить мониторинг новостей HR Time: {e}")
                import traceback
                log.error(traceback.format_exc())
            
            log.info("💡 Для production установите USE_WEBHOOK=true и WEBHOOK_URL")
            
            try:
                webhook_info = await app.bot.get_webhook_info()
                if webhook_info.url:
                    log.warning(f"⚠️ Обнаружен webhook: {webhook_info.url}. Удаляем для polling...")
                    await app.bot.delete_webhook(drop_pending_updates=True)
                    log.info("✅ Webhook удален")
            except Exception as e:
                log.error(f"❌ Ошибка проверки webhook: {e}")
            
            await app.updater.start_polling(
                allowed_updates=["message", "channel_post", "callback_query"],
                drop_pending_updates=True
            )
            log.info("✅ Бот запущен с polling (concurrent_updates=True)")
            log.info("🚀 Готов к обработке обновлений от Telegram")
            
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                pass
    
    # Запускаем бота
    log.info("🚀 Запуск Telegram Bot...")
    log.info(f"⚙️  Режим: {'WEBHOOK' if USE_WEBHOOK and WEBHOOK_URL else 'POLLING'}")
    log.info(f"🔄 Concurrent updates: ВКЛЮЧЕН (поддержка 100+ одновременных пользователей)")
    
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        log.info("⏹️  Остановка бота по запросу пользователя...")
    except RuntimeError as e:
        if "already running" in str(e).lower():
            log.warning("⚠️ Приложение уже запущено, возможно перезапуск контейнера")
            import time
            time.sleep(5)
        else:
            raise
    except Exception as e:
        log.error(f"❌ Критическая ошибка при запуске бота: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()
