#!/usr/bin/env python3
"""
Тестовый скрипт для проверки, что письма отправляются ТОЛЬКО в канал,
а не подписчикам бота
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


async def test_email_to_channel_only():
    """Тестирует отправку mock письма только в канал"""
    try:
        from telegram import Bot
        from telegram.error import TelegramError
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
        log.info("🧪 ТЕСТ: Отправка mock письма ТОЛЬКО в канал")
        log.info("=" * 70)
        
        # Создаем mock email данные
        mock_email_data = {
            "id": "TEST_EMAIL_12345",
            "subject": "🧪 ТЕСТ: Запрос на услуги HR-консалтинга",
            "from": "test_client@example.com",
            "to": "a-novoselova07@yandex.ru",
            "body": """Здравствуйте!

Это тестовое письмо для проверки функциональности.

Наша компания заинтересована в услугах HR-консалтинга:
- Подбор персонала
- Оценка сотрудников
- Разработка HR-стратегии

Можете ли вы предоставить информацию о ваших услугах и стоимости?

С уважением,
Тестовый клиент""",
            "preview": "Здравствуйте! Это тестовое письмо для проверки функциональности...",
            "date": "2026-01-28"
        }
        
        log.info("\n📧 Mock письмо:")
        log.info(f"   От: {mock_email_data['from']}")
        log.info(f"   Тема: {mock_email_data['subject']}")
        log.info(f"   Текст: {mock_email_data['body'][:100]}...")
        
        log.info("\n" + "=" * 70)
        log.info("📤 ОТПРАВКА ПИСЬМА...")
        log.info("=" * 70)
        log.info("⚠️  ВАЖНО: Письмо должно быть отправлено ТОЛЬКО в канал")
        log.info("⚠️  Письмо НЕ должно быть отправлено подписчикам бота")
        log.info("=" * 70)
        
        # Вызываем функцию отправки (она должна отправить только в канал)
        await send_email_notification(bot, mock_email_data)
        
        log.info("\n" + "=" * 70)
        log.info("✅ ТЕСТ ЗАВЕРШЕН")
        log.info("=" * 70)
        log.info("📋 Проверьте:")
        log.info(f"   1. Канал: https://t.me/HRAI_ANovoselova_Leads")
        log.info("   2. В канале должно появиться письмо с меткой LEAD или NON_LEAD")
        log.info("   3. В боте @HR2137_bot НЕ должно быть уведомлений о письме")
        log.info("=" * 70)
        
        return True
        
    except Exception as e:
        log.error(f"❌ Ошибка при тестировании: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = asyncio.run(test_email_to_channel_only())
    sys.exit(0 if success else 1)
