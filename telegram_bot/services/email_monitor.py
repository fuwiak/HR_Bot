"""
Email monitoring state и фоновая задача
"""
import os
import asyncio
import logging
from typing import Dict

log = logging.getLogger(__name__)

# Импорт функции классификации и отправки в канал
try:
    from services.agents.scenario_workflows import classify_email_as_lead, send_lead_to_channel
    SCENARIO_WORKFLOWS_AVAILABLE = True
except ImportError as e:
    log.warning(f"⚠️ Не удалось импортировать scenario_workflows: {e}")
    SCENARIO_WORKFLOWS_AVAILABLE = False

# Глобальное состояние для отслеживания обработанных писем
processed_email_ids: set = set()

# Интервал проверки почты (в секундах)
email_check_interval = int(os.getenv("EMAIL_CHECK_INTERVAL", "10"))  # 10 секунд по умолчанию

# Хранилище состояния ответа на email для каждого пользователя
email_reply_state: Dict[int, Dict] = {}  # {user_id: {'email_id': ..., 'to': ..., 'subject': ...}}


async def send_email_notification(bot, email_data: Dict):
    """Отправка нового письма в канал лидов с классификацией lead/non_lead
    
    Все новые письма автоматически отправляются в канал https://t.me/HRAI_ANovoselova_Leads
    с метками LEAD или NON_LEAD на основе классификации через LLM.
    """
    try:
        subject = email_data.get("subject", "Без темы")
        from_email = email_data.get("from", "Неизвестный отправитель")
        email_id = email_data.get("id", "")
        preview = email_data.get("preview", "")[:200]  # Первые 200 символов
        body = email_data.get("body", email_data.get("preview", ""))
        
        # Отправляем ВСЕ письма в канал лидов с классификацией
        if SCENARIO_WORKFLOWS_AVAILABLE:
            try:
                # Классифицируем email через LLM
                log.info(f"🤖 Классификация письма: {subject[:50]}...")
                classification = await classify_email_as_lead(subject, body)
                label = classification.get("label", "non_lead")
                confidence = classification.get("confidence", 0.5)
                reason = classification.get("reason", "")
                
                log.info(f"✅ Email классифицирован как {label.upper()} (уверенность: {confidence:.2f})")
                
                # Формируем информацию для канала
                lead_info = {
                    "source": "📧 Email",
                    "title": subject or "Без темы",
                    "client_name": from_email.split("@")[0] if "@" in from_email else from_email,
                    "client_email": from_email if "@" in from_email else "",
                    "client_phone": "",
                    "message": body or preview or "",
                    "score": 0,
                    "status": "new",
                    "category": "",
                    "label": label,
                    "classification_reason": reason,
                    "classification_confidence": confidence
                }
                
                # Отправляем в канал (ТОЛЬКО в канал, без отправки подписчикам бота)
                await send_lead_to_channel(bot, lead_info)
                log.info(f"✅ Письмо отправлено в канал лидов с меткой {label.upper()}")
            except Exception as e:
                log.error(f"❌ Ошибка отправки письма в канал лидов: {e}")
                import traceback
                log.error(traceback.format_exc())
        else:
            log.warning("⚠️ SCENARIO_WORKFLOWS недоступен, письмо не отправлено в канал")
                
    except Exception as e:
        log.error(f"❌ Ошибка обработки письма: {e}")
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
            # Увеличиваем период до 7 дней для надежности
            emails = await check_new_emails(since_days=7, limit=1)
            
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
