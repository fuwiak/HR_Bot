#!/usr/bin/env python3
"""
Скрипт для классификации последних 5 писем из Yandex почты
и отправки их в канал с метками lead/non_lead
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


async def classify_and_send_emails():
    """Получает последние 5 писем из Yandex, классифицирует и отправляет в канал"""
    try:
        from telegram import Bot
        from telegram.error import TelegramError
        from services.helpers.email_helper import check_new_emails
        from services.agents.scenario_workflows import classify_email_as_lead, send_lead_to_channel
        
        # Проверяем наличие необходимых переменных окружения
        telegram_token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        channel_id = os.getenv("TELEGRAM_LEADS_CHANNEL_ID")
        
        if not telegram_token:
            log.error("❌ TELEGRAM_TOKEN не установлен")
            log.error("   Установите переменную окружения TELEGRAM_TOKEN или TELEGRAM_BOT_TOKEN")
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
                    log.info(f"✅ Глобальная переменная TELEGRAM_LEADS_CHANNEL_ID обновлена в модуле")
                except TelegramError as e:
                    log.error(f"❌ Не удалось получить ID канала автоматически: {e}")
                    log.error(f"   Попробуйте выполнить:")
                    log.error(f"   python scripts/get_channel_id.py @HRAI_ANovoselova_Leads")
                    log.error(f"   Или установите переменную окружения:")
                    log.error(f"   export TELEGRAM_LEADS_CHANNEL_ID='-1003862655606'")
                    return False
            except Exception as e:
                log.error(f"❌ Ошибка при получении ID канала: {e}")
                import traceback
                log.error(traceback.format_exc())
                return False
        
        # Создаем бота
        bot = Bot(token=telegram_token)
        
        log.info("🚀 Начало обработки писем из Yandex")
        log.info("=" * 60)
        
        # Получаем последние 5 писем (за последние 30 дней для надежности)
        log.info("\n📧 Получение последних 5 писем из Yandex...")
        emails = await check_new_emails(folder="INBOX", since_days=30, limit=5)
        
        if not emails:
            log.warning("⚠️ Письма не найдены")
            log.info("   Проверьте:")
            log.info("   - YANDEX_EMAIL и YANDEX_PASSWORD установлены")
            log.info("   - Есть ли письма в папке INBOX за последние 30 дней")
            return False
        
        log.info(f"✅ Найдено {len(emails)} писем")
        log.info("=" * 60)
        
        # Обрабатываем каждое письмо
        for idx, email_data in enumerate(emails, 1):
            try:
                subject = email_data.get("subject", "Без темы")
                body = email_data.get("body", email_data.get("preview", ""))
                from_addr = email_data.get("from", "Неизвестно")
                email_id = email_data.get("id", "")
                
                log.info(f"\n📧 ПИСЬМО {idx}/{len(emails)}")
                log.info("-" * 60)
                log.info(f"От: {from_addr}")
                log.info(f"Тема: {subject}")
                log.info(f"Текст: {body[:100]}{'...' if len(body) > 100 else ''}")
                
                # Классифицируем письмо
                log.info("\n🤖 Классификация через LLM...")
                classification = await classify_email_as_lead(subject, body)
                label = classification.get("label", "non_lead")
                confidence = classification.get("confidence", 0.5)
                reason = classification.get("reason", "")
                
                log.info(f"✅ Классификация: {label.upper()} (уверенность: {confidence:.2f})")
                log.info(f"   Причина: {reason}")
                
                # Формируем информацию для канала
                lead_info = {
                    "source": "📧 Yandex Email",
                    "title": subject,
                    "client_name": from_addr.split("@")[0] if "@" in from_addr else from_addr,
                    "client_email": from_addr if "@" in from_addr else "",
                    "client_phone": "",
                    "message": body,
                    "score": 0,
                    "status": "processed",
                    "category": "",
                    "label": label,
                    "classification_reason": reason,
                    "classification_confidence": confidence
                }
                
                # Отправляем в канал
                log.info(f"\n📤 Отправка в канал...")
                result = await send_lead_to_channel(bot, lead_info)
                
                if result:
                    log.info(f"✅ Письмо {idx} успешно отправлено в канал с меткой {label.upper()}")
                else:
                    log.error(f"❌ Ошибка отправки письма {idx} в канал")
                
                # Небольшая задержка между письмами
                if idx < len(emails):
                    await asyncio.sleep(2)
                    
            except Exception as e:
                log.error(f"❌ Ошибка обработки письма {idx}: {e}")
                import traceback
                log.error(traceback.format_exc())
                continue
        
        log.info("\n" + "=" * 60)
        log.info(f"✅ Обработка завершена! Обработано {len(emails)} писем")
        log.info(f"Проверьте канал: https://t.me/HRAI_ANovoselova_Leads")
        
        return True
        
    except Exception as e:
        log.error(f"❌ Ошибка при обработке писем: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = asyncio.run(classify_and_send_emails())
    sys.exit(0 if success else 1)
