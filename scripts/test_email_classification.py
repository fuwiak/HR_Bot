#!/usr/bin/env python3
"""
Тестовый скрипт для проверки классификации email и отправки в канал
Генерирует тестовые сообщения через LLM (одно lead, одно non_lead) и отправляет их в канал
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

async def generate_test_email(is_lead: bool) -> dict:
    """
    Генерирует тестовое email сообщение через LLM
    
    Args:
        is_lead: True для генерации lead сообщения, False для non_lead
    
    Returns:
        Словарь с полями email (subject, body, from)
    """
    try:
        from services.helpers.llm_api import LLMClient
        
        llm_client = LLMClient()
        
        if is_lead:
            prompt = """Сгенерируй реалистичное email сообщение от потенциального клиента HR-консалтинга.

Требования:
- Тема письма должна быть конкретной и профессиональной
- Сообщение должно содержать запрос на услуги HR-консалтинга (например: подбор персонала, оценка сотрудников, разработка HR-стратегии, обучение персонала)
- Клиент должен выражать заинтересованность в услугах
- Укажи конкретные потребности компании
- Тон должен быть деловым и профессиональным

Ответь ТОЛЬКО в формате JSON:
{
    "subject": "тема письма",
    "body": "текст письма (3-5 предложений)",
    "from": "email@example.com"
}"""
        else:
            prompt = """Сгенерируй реалистичное email сообщение, которое НЕ является потенциальным лидом для HR-консалтинга.

Это может быть:
- Спам или реклама
- Автоматическое уведомление
- Личная переписка не связанная с бизнесом
- Техническое уведомление
- Рассылка новостей

Ответь ТОЛЬКО в формате JSON:
{
    "subject": "тема письма",
    "body": "текст письма (2-4 предложения)",
    "from": "email@example.com"
}"""
        
        response = await llm_client.generate(
            prompt=prompt,
            system_prompt="Ты помощник для генерации тестовых email сообщений. Отвечай только в формате JSON.",
            temperature=0.7,
            max_tokens=500
        )
        
        if response.error:
            log.error(f"❌ Ошибка генерации тестового email: {response.error}")
            # Возвращаем дефолтное сообщение
            if is_lead:
                return {
                    "subject": "Запрос на услуги HR-консалтинга",
                    "body": "Здравствуйте! Наша компания заинтересована в услугах по подбору персонала. У нас открыта вакансия на позицию HR-менеджера и мы хотели бы обсудить возможность сотрудничества. Можете ли вы предоставить информацию о ваших услугах и стоимости?",
                    "from": "test_lead@example.com"
                }
            else:
                return {
                    "subject": "Автоматическое уведомление",
                    "body": "Это автоматическое уведомление о том, что ваш аккаунт был успешно создан. Спасибо за регистрацию!",
                    "from": "noreply@example.com"
                }
        
        # Парсим JSON ответ
        import json
        import re
        
        content = response.content.strip()
        json_match = re.search(r'\{[^{}]*"subject"[^{}]*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
            else:
                json_str = content
        
        try:
            email_data = json.loads(json_str)
            log.info(f"✅ Сгенерировано тестовое email сообщение (is_lead={is_lead})")
            return email_data
        except json.JSONDecodeError as e:
            log.error(f"❌ Ошибка парсинга JSON: {e}, ответ: {content[:200]}")
            # Возвращаем дефолтное сообщение
            if is_lead:
                return {
                    "subject": "Запрос на услуги HR-консалтинга",
                    "body": "Здравствуйте! Наша компания заинтересована в услугах по подбору персонала.",
                    "from": "test_lead@example.com"
                }
            else:
                return {
                    "subject": "Автоматическое уведомление",
                    "body": "Это автоматическое уведомление.",
                    "from": "noreply@example.com"
                }
                
    except Exception as e:
        log.error(f"❌ Исключение при генерации тестового email: {e}")
        import traceback
        log.error(traceback.format_exc())
        # Возвращаем дефолтное сообщение
        if is_lead:
            return {
                "subject": "Запрос на услуги HR-консалтинга",
                "body": "Здравствуйте! Наша компания заинтересована в услугах по подбору персонала.",
                "from": "test_lead@example.com"
            }
        else:
            return {
                "subject": "Автоматическое уведомление",
                "body": "Это автоматическое уведомление.",
                "from": "noreply@example.com"
            }


async def test_email_classification():
    """Тестирует классификацию и отправку email в канал"""
    try:
        from telegram import Bot
        from telegram.error import TelegramError
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
                # Пробуем получить ID канала по username
                channel_username = "@HRAI_ANovoselova_Leads"
                try:
                    chat = await bot_temp.get_chat(channel_username)
                    channel_id = str(chat.id)
                    log.info(f"✅ ID канала получен автоматически: {channel_id}")
                    # Устанавливаем переменную окружения для текущей сессии
                    os.environ["TELEGRAM_LEADS_CHANNEL_ID"] = channel_id
                    # Обновляем глобальную переменную в модуле scenario_workflows
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
        
        log.info("🚀 Начало тестирования классификации email")
        log.info("=" * 60)
        
        # Тест 1: Генерация и отправка LEAD сообщения
        log.info("\n📧 ТЕСТ 1: Генерация LEAD сообщения")
        log.info("-" * 60)
        lead_email = await generate_test_email(is_lead=True)
        log.info(f"Тема: {lead_email['subject']}")
        log.info(f"От: {lead_email['from']}")
        log.info(f"Текст: {lead_email['body'][:100]}...")
        
        # Классифицируем
        classification = await classify_email_as_lead(lead_email['subject'], lead_email['body'])
        log.info(f"\n✅ Классификация: {classification['label']} (уверенность: {classification['confidence']:.2f})")
        log.info(f"Причина: {classification['reason']}")
        
        # Отправляем в канал
        lead_info = {
            "source": "📧 Email (ТЕСТ)",
            "title": lead_email['subject'],
            "client_name": lead_email['from'].split("@")[0],
            "client_email": lead_email['from'],
            "client_phone": "",
            "message": lead_email['body'],
            "score": 0,
            "status": "test",
            "category": "",
            "label": classification['label'],
            "classification_reason": classification['reason'],
            "classification_confidence": classification['confidence']
        }
        
        result = await send_lead_to_channel(bot, lead_info)
        if result:
            log.info("✅ LEAD сообщение успешно отправлено в канал")
        else:
            log.error("❌ Ошибка отправки LEAD сообщения в канал")
        
        # Ждем немного перед следующим тестом
        await asyncio.sleep(2)
        
        # Тест 2: Генерация и отправка NON_LEAD сообщения
        log.info("\n📧 ТЕСТ 2: Генерация NON_LEAD сообщения")
        log.info("-" * 60)
        non_lead_email = await generate_test_email(is_lead=False)
        log.info(f"Тема: {non_lead_email['subject']}")
        log.info(f"От: {non_lead_email['from']}")
        log.info(f"Текст: {non_lead_email['body'][:100]}...")
        
        # Классифицируем
        classification = await classify_email_as_lead(non_lead_email['subject'], non_lead_email['body'])
        log.info(f"\n✅ Классификация: {classification['label']} (уверенность: {classification['confidence']:.2f})")
        log.info(f"Причина: {classification['reason']}")
        
        # Отправляем в канал
        lead_info = {
            "source": "📧 Email (ТЕСТ)",
            "title": non_lead_email['subject'],
            "client_name": non_lead_email['from'].split("@")[0],
            "client_email": non_lead_email['from'],
            "client_phone": "",
            "message": non_lead_email['body'],
            "score": 0,
            "status": "test",
            "category": "",
            "label": classification['label'],
            "classification_reason": classification['reason'],
            "classification_confidence": classification['confidence']
        }
        
        result = await send_lead_to_channel(bot, lead_info)
        if result:
            log.info("✅ NON_LEAD сообщение успешно отправлено в канал")
        else:
            log.error("❌ Ошибка отправки NON_LEAD сообщения в канал")
        
        log.info("\n" + "=" * 60)
        log.info("✅ Тестирование завершено!")
        log.info(f"Проверьте канал: https://t.me/HRAI_ANovoselova_Leads")
        
        return True
        
    except Exception as e:
        log.error(f"❌ Ошибка при тестировании: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = asyncio.run(test_email_classification())
    sys.exit(0 if success else 1)
