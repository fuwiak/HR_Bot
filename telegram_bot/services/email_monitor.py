"""
Email monitoring state и фоновая задача
"""
import os
import asyncio
import logging
from typing import Dict
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

# Цветное логирование для Railway (поддерживает ANSI цвета)
class ColoredFormatter(logging.Formatter):
    """Форматтер с цветами для Railway логов"""
    
    # ANSI цветовые коды
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Добавляем цвет к уровню логирования
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        # Форматируем сообщение
        formatted = super().format(record)
        
        # Восстанавливаем оригинальный уровень для следующего вызова
        record.levelname = levelname
        
        return formatted

# Настройка логирования с цветами
log = logging.getLogger(__name__)
if not log.handlers:
    handler = logging.StreamHandler()
    formatter = ColoredFormatter(
        '%(asctime)s | %(levelname)s | [EMAIL_MONITOR] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.INFO)

# Импорт функции классификации и отправки в канал
try:
    from services.agents.scenario_workflows import classify_email_type, send_lead_to_channel
    import services.agents.scenario_workflows as sw_module
    SCENARIO_WORKFLOWS_AVAILABLE = True
except ImportError as e:
    log.warning(f"⚠️ Не удалось импортировать scenario_workflows: {e}")
    SCENARIO_WORKFLOWS_AVAILABLE = False
    sw_module = None

# Канал для отправки писем
LEADS_CHANNEL_USERNAME = "@HRAI_ANovoselova_Leads"
LEADS_CHANNEL_URL = "https://t.me/HRAI_ANovoselova_Leads"

# Глобальное состояние для отслеживания обработанных писем
processed_email_ids: set = set()

# Подавление подробных INFO-логов (для Railway). По умолчанию включено — меньше шума в логах.
# Чтобы включить подробные логи: SUPPRESS_VERBOSE_EMAIL_MONITOR_LOGS=0 или false
SUPPRESS_VERBOSE_EMAIL_MONITOR_LOGS = os.getenv("SUPPRESS_VERBOSE_EMAIL_MONITOR_LOGS", "true").lower() not in ("0", "false", "no")

# Интервал проверки почты (в секундах)
email_check_interval = int(os.getenv("EMAIL_CHECK_INTERVAL", "10"))  # 10 секунд по умолчанию

# Максимальный возраст письма для отправки в канал (в часах)
# Письма старше этого возраста не будут отправляться
EMAIL_MAX_AGE_HOURS = int(os.getenv("EMAIL_MAX_AGE_HOURS", "1"))  # 1 час по умолчанию

# Хранилище состояния ответа на email для каждого пользователя
email_reply_state: Dict[int, Dict] = {}  # {user_id: {'email_id': ..., 'to': ..., 'subject': ...}}


async def ensure_channel_id_set(bot):
    """Убедиться, что ID канала установлен, если нет - получить автоматически"""
    if not SCENARIO_WORKFLOWS_AVAILABLE or not sw_module:
        return False
    
    # Проверяем, установлен ли ID канала
    if not sw_module.TELEGRAM_LEADS_CHANNEL_ID:
        log.warning(f"⚠️ TELEGRAM_LEADS_CHANNEL_ID не установлен, пытаюсь получить автоматически...")
        try:
            from telegram.error import TelegramError
            try:
                chat = await bot.get_chat(LEADS_CHANNEL_USERNAME)
                channel_id = str(chat.id)
                log.info(f"✅ ID канала получен автоматически: {channel_id}")
                os.environ["TELEGRAM_LEADS_CHANNEL_ID"] = channel_id
                sw_module.TELEGRAM_LEADS_CHANNEL_ID = channel_id
                return True
            except TelegramError as e:
                log.error(f"❌ Не удалось получить ID канала автоматически: {e}")
                log.error(f"   Убедитесь, что бот добавлен в канал {LEADS_CHANNEL_USERNAME} как администратор")
                return False
        except Exception as e:
            log.error(f"❌ Ошибка при получении ID канала: {e}")
            return False
    return True


async def send_email_notification(bot, email_data: Dict):
    """Отправка нового письма в канал лидов с классификацией lead/non_lead
    
    Все новые письма автоматически отправляются в канал https://t.me/HRAI_ANovoselova_Leads
    с метками LEAD или NON_LEAD на основе классификации через LLM.
    """
    try:
        log.info("=" * 80)
        log.info("📨 НАЧАЛО ОБРАБОТКИ ПИСЬМА")
        log.info(f"📤 Канал назначения: {LEADS_CHANNEL_URL}")
        log.info("=" * 80)
        
        subject = email_data.get("subject", "Без темы")
        from_email = email_data.get("from", "Неизвестный отправитель")
        email_id = email_data.get("id", "")
        preview = email_data.get("preview", "")[:200]  # Первые 200 символов
        body = email_data.get("body", email_data.get("preview", ""))
        
        log.info(f"📧 От: {from_email}")
        log.info(f"📝 Тема: {subject}")
        log.info(f"🆔 ID: {email_id}")
        log.info(f"📄 Длина текста: {len(body)} символов")
        
        # Убеждаемся, что ID канала установлен
        if not await ensure_channel_id_set(bot):
            log.error("❌ Не удалось установить ID канала, письмо не будет отправлено")
            return
        
        # Формируем lead_info для проверки дедупликации
        lead_info = {
            "source": "📧 Email",
            "title": subject or "Без темы",
            "client_name": from_email.split("@")[0] if "@" in from_email else from_email,
            "client_email": from_email if "@" in from_email else "",
            "client_phone": "",
            "message": body or preview or ""
        }
        
        # Проверяем на дубликаты ПЕРЕД отправкой в канал
        try:
            from services.helpers.channel_deduplicator import is_duplicate
            is_dup, reason = is_duplicate(lead_info, check_content=True)
            if is_dup:
                log.info("=" * 80)
                log.info(f"⏭️  ПРОПУСК ДУБЛИКАТА: {reason}")
                log.info("=" * 80)
                return  # Не отправляем дубликат
        except ImportError:
            log.warning("⚠️ Модуль channel_deduplicator недоступен, проверка дубликатов отключена")
        except Exception as e:
            log.warning(f"⚠️ Ошибка проверки дубликатов: {e}, продолжаем отправку")
        
        # Отправляем ВСЕ письма в канал лидов с классификацией
        if SCENARIO_WORKFLOWS_AVAILABLE:
            try:
                # Классифицируем email через LLM на три категории
                log.info("🤖 Запуск классификации через LLM...")
                classification = await classify_email_type(subject, body)
                email_category = classification.get("category", "service")
                confidence = classification.get("confidence", 0.5)
                reason = classification.get("reason", "")
                
                # Маппинг категорий для логирования
                category_names = {
                    "new_lead": "НОВЫЙ ЛИД",
                    "followup": "ПРОДОЛЖЕНИЕ ДИАЛОГА",
                    "service": "СЛУЖЕБНАЯ ИНФОРМАЦИЯ"
                }
                category_name = category_names.get(email_category, email_category.upper())
                
                log.info(f"✅ Классификация завершена:")
                log.info(f"   🏷️  Категория: {category_name}")
                log.info(f"   📊 Уверенность: {confidence:.2f}")
                log.info(f"   💭 Причина: {reason}")
                
                # Обновляем lead_info с классификацией
                lead_info.update({
                    "score": 0,
                    "status": "new",
                    "category": "",
                    "email_category": email_category,
                    "classification_reason": reason,
                    "classification_confidence": confidence
                })
                
                # Отправляем в канал (ТОЛЬКО в канал, без отправки подписчикам бота)
                # send_lead_to_channel уже имеет встроенную проверку дедупликации
                log.info(f"📤 Отправка в канал {LEADS_CHANNEL_URL}...")
                result = await send_lead_to_channel(bot, lead_info)
                if result:
                    log.info("=" * 80)
                    log.info(f"✅ ПИСЬМО УСПЕШНО ОТПРАВЛЕНО В КАНАЛ {LEADS_CHANNEL_URL}")
                    log.info(f"   🏷️  Категория: {category_name}")
                    log.info(f"   📊 Уверенность: {confidence:.2f}")
                    log.info("=" * 80)
                else:
                    log.error("=" * 80)
                    log.error(f"❌ НЕ УДАЛОСЬ ОТПРАВИТЬ ПИСЬМО В КАНАЛ")
                    log.error("=" * 80)
            except Exception as e:
                log.error("=" * 80)
                log.error(f"❌ ОШИБКА ОТПРАВКИ ПИСЬМА В КАНАЛ:")
                log.error(f"❌ {str(e)}")
                log.error("=" * 80)
                import traceback
                log.error(traceback.format_exc())
                log.error("=" * 80)
        else:
            log.warning("=" * 80)
            log.warning("⚠️ SCENARIO_WORKFLOWS недоступен, письмо не отправлено в канал")
            log.warning("=" * 80)
                
    except Exception as e:
        log.error("=" * 80)
        log.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА ОБРАБОТКИ ПИСЬМА:")
        log.error(f"❌ {str(e)}")
        log.error("=" * 80)
        import traceback
        log.error(traceback.format_exc())
        log.error("=" * 80)


async def email_monitor_task(bot):
    """
    Фоновая задача для мониторинга новых писем
    
    Args:
        bot: Telegram Bot instance
    """
    global processed_email_ids
    
    log.info("=" * 80)
    log.info(f"🚀 ЗАПУСК ФОНОВОЙ ЗАДАЧИ МОНИТОРИНГА ПОЧТЫ")
    log.info(f"📧 Интервал проверки: {email_check_interval} секунд")
    log.info(f"📅 Период проверки: 7 дней (для поиска)")
    log.info(f"⏰ Максимальный возраст письма для отправки: {EMAIL_MAX_AGE_HOURS} часов")
    log.info(f"📊 Обработано писем: {len(processed_email_ids)}")
    log.info(f"📤 Канал для отправки: {LEADS_CHANNEL_URL}")
    
    # Проверяем и устанавливаем ID канала при запуске
    if bot:
        await ensure_channel_id_set(bot)
        if sw_module and sw_module.TELEGRAM_LEADS_CHANNEL_ID:
            log.info(f"✅ ID канала установлен: {sw_module.TELEGRAM_LEADS_CHANNEL_ID}")
        else:
            log.warning(f"⚠️ ID канала не установлен, будет попытка получить автоматически при первом письме")
    
    log.info("=" * 80)
    
    iteration = 0
    
    while True:
        iteration += 1
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not SUPPRESS_VERBOSE_EMAIL_MONITOR_LOGS:
                log.info(f"\n🔄 Итерация #{iteration} | {current_time}")
                log.info(f"📬 Проверка новых писем...")
            
            from services.helpers.email_helper import check_new_emails
            
            # Проверяем только самое новое письмо (limit=1 для скорости)
            # Увеличиваем период до 7 дней для надежности
            emails = await check_new_emails(since_days=7, limit=1)
            
            if emails:
                # Берем только самое новое письмо (первое в списке)
                email_data = emails[0]
                email_id = email_data.get("id", "")
                subject = email_data.get("subject", "Без темы")
                from_addr = email_data.get("from", "Неизвестно")
                date_str = email_data.get("date", "")
                
                # Сразу пропускаем, если это письмо уже обрабатывали (в т.ч. как "слишком старое") — не спамим лог
                if email_id and email_id in processed_email_ids:
                    if not SUPPRESS_VERBOSE_EMAIL_MONITOR_LOGS:
                        log.info(f"⏭️  Письмо ID={email_id} уже в обработанных, пропускаю")
                    await asyncio.sleep(email_check_interval)
                    continue
                
                if not SUPPRESS_VERBOSE_EMAIL_MONITOR_LOGS:
                    log.info(f"📧 Найдено письмо: ID={email_id}, От={from_addr}, Тема={subject[:50]}")
                    log.info(f"📋 Обработано писем в памяти: {len(processed_email_ids)}")
                
                # Парсим дату письма и проверяем, что оно новое
                email_date = None
                if date_str:
                    try:
                        email_date = parsedate_to_datetime(date_str)
                        # Приводим к локальному времени без часового пояса для сравнения
                        if email_date.tzinfo:
                            # Если есть часовой пояс, приводим к локальному времени
                            email_date = email_date.astimezone().replace(tzinfo=None)
                        # Если нет часового пояса, считаем локальным временем
                    except Exception as e:
                        log.warning(f"⚠️ Не удалось распарсить дату письма '{date_str}': {e}")
                
                # Проверяем возраст письма - отправляем только новые письма
                if email_date:
                    now = datetime.now()
                    age = now - email_date
                    age_hours = age.total_seconds() / 3600
                    
                    if not SUPPRESS_VERBOSE_EMAIL_MONITOR_LOGS:
                        log.info(f"📅 Дата письма: {email_date.strftime('%Y-%m-%d %H:%M:%S')}")
                        log.info(f"⏰ Возраст письма: {age_hours:.2f} часов")
                    
                    if age_hours > EMAIL_MAX_AGE_HOURS:
                        if email_id:
                            processed_email_ids.add(email_id)
                        log.info(f"⏭️  Письмо слишком старое ({age_hours:.2f} ч > {EMAIL_MAX_AGE_HOURS} ч), добавлено в обработанные, пропускаю")
                        continue
                else:
                    # Если дату не удалось распарсить, все равно проверяем по ID
                    log.warning(f"⚠️ Не удалось определить дату письма, проверяю только по ID")
                
                # Проверяем, не обрабатывали ли уже это письмо по email_id
                # Но также проверяем дедупликацию в send_email_notification
                if email_id and email_id not in processed_email_ids:
                    log.info(f"✅ НОВОЕ ПИСЬМО! Начинаю обработку...")
                    # Отправляем уведомление только о самом новом письме
                    # send_email_notification проверит дедупликацию через channel_deduplicator
                    await send_email_notification(bot, email_data)
                    # Помечаем как обработанное только если оно действительно было отправлено
                    # (если это был дубликат, send_email_notification вернется раньше)
                    processed_email_ids.add(email_id)
                    log.info(f"✅ Письмо обработано и добавлено в список обработанных")
                    log.info(f"📊 Всего обработано: {len(processed_email_ids)}")
                else:
                    if email_id in processed_email_ids and not SUPPRESS_VERBOSE_EMAIL_MONITOR_LOGS:
                        log.info(f"⏭️  Письмо уже обработано ранее (ID: {email_id}), пропускаю")
                    else:
                        log.warning(f"⚠️  Email ID пустой или некорректный")
            else:
                if not SUPPRESS_VERBOSE_EMAIL_MONITOR_LOGS:
                    log.info(f"📭 Новых писем не найдено")
            if not SUPPRESS_VERBOSE_EMAIL_MONITOR_LOGS:
                log.info(f"⏳ Ожидание {email_check_interval} секунд до следующей проверки...")
            
            # Ждем перед следующей проверкой
            await asyncio.sleep(email_check_interval)
            
        except Exception as e:
            log.error("=" * 80)
            log.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в мониторинге почты!")
            log.error(f"❌ Ошибка: {str(e)}")
            log.error("=" * 80)
            import traceback
            log.error(traceback.format_exc())
            log.error("=" * 80)
            if not SUPPRESS_VERBOSE_EMAIL_MONITOR_LOGS:
                log.info(f"⏳ Повторная попытка через {email_check_interval} секунд...")
            # При ошибке ждем перед следующей попыткой
            await asyncio.sleep(email_check_interval)
