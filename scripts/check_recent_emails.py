#!/usr/bin/env python3
"""
Проверка последних писем из Yandex и отправка их в канал
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Загружаем переменные окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


async def check_and_send_recent_emails():
    """Проверяет последние письма и отправляет их в канал"""
    try:
        from telegram import Bot
        from telegram.error import TelegramError
        from services.helpers.email_helper import check_new_emails
        from telegram_bot.services.email_monitor import send_email_notification
        
        # Проверяем наличие необходимых переменных окружения
        telegram_token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        channel_id = os.getenv("TELEGRAM_LEADS_CHANNEL_ID")
        
        if not telegram_token:
            log.error("❌ TELEGRAM_TOKEN не установлен")
            return False
        
        # Если channel_id не установлен, пытаемся получить его автоматически
        if not channel_id:
            log.warning("⚠️ TELEGRAM_LEADS_CHANNEL_ID не установлен, пытаюсь получить автоматически...")
            try:
                bot_temp = Bot(token=telegram_token)
                channel_username = "@HRAI_ANovoselova_Leads"
                try:
                    chat = await bot_temp.get_chat(channel_username)
                    channel_id = str(chat.id)
                    log.info(f"✅ ID канала получен автоматически: {channel_id}")
                    os.environ["TELEGRAM_LEADS_CHANNEL_ID"] = channel_id
                    import services.agents.scenario_workflows as sw_module
                    sw_module.TELEGRAM_LEADS_CHANNEL_ID = channel_id
                except TelegramError as e:
                    log.error(f"❌ Не удалось получить ID канала автоматически: {e}")
                    return False
            except Exception as e:
                log.error(f"❌ Ошибка при получении ID канала: {e}")
                return False
        
        # Создаем бота
        bot = Bot(token=telegram_token)
        
        log.info("=" * 70)
        log.info("📧 Проверка последних писем из Yandex")
        log.info("=" * 70)
        
        # Получаем последние 10 писем за последние 7 дней
        log.info("\n🔍 Поиск последних писем...")
        emails = await check_new_emails(folder="INBOX", since_days=7, limit=10)
        
        if not emails:
            log.warning("⚠️ Письма не найдены")
            log.info("   Проверьте:")
            log.info("   - YANDEX_EMAIL и YANDEX_PASSWORD установлены")
            log.info("   - Есть ли письма в папке INBOX за последние 7 дней")
            return False
        
        log.info(f"✅ Найдено {len(emails)} писем")
        log.info("=" * 70)
        
        # Показываем список писем
        for idx, email_data in enumerate(emails, 1):
            subject = email_data.get("subject", "Без темы")
            from_addr = email_data.get("from", "Неизвестно")
            email_id = email_data.get("id", "")
            date = email_data.get("date", "")
            
            log.info(f"\n{idx}. Письмо ID: {email_id}")
            log.info(f"   От: {from_addr}")
            log.info(f"   Тема: {subject}")
            log.info(f"   Дата: {date}")
        
        log.info("\n" + "=" * 70)
        log.info("📤 Отправка последнего письма в канал...")
        log.info("=" * 70)
        
        # Отправляем самое новое письмо (первое в списке)
        if emails:
            latest_email = emails[0]
            log.info(f"\n📧 Обработка письма:")
            log.info(f"   От: {latest_email.get('from', 'Неизвестно')}")
            log.info(f"   Тема: {latest_email.get('subject', 'Без темы')}")
            
            await send_email_notification(bot, latest_email)
            log.info("\n✅ Письмо обработано и отправлено в канал")
        
        log.info("\n" + "=" * 70)
        log.info("✅ Проверка завершена")
        log.info(f"Проверьте канал: https://t.me/HRAI_ANovoselova_Leads")
        log.info("=" * 70)
        
        return True
        
    except Exception as e:
        log.error(f"❌ Ошибка при проверке писем: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = asyncio.run(check_and_send_recent_emails())
    sys.exit(0 if success else 1)
