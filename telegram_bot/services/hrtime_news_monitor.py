"""
Мониторинг новостей HR Time из "Вся лента"
Получает новости из Telegram канала @HRTime_bot и отправляет в канал лидов
"""
import os
import asyncio
import logging
from typing import Dict, Set
from datetime import datetime

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
        '%(asctime)s | %(levelname)s | [HRTIME_NEWS_MONITOR] %(message)s',
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

# Импорт системы оценки и парсера новостей
try:
    from services.services.hrtime_news_scorer import HRTimeNewsScorer
    from services.services.hrtime_news_parser import HRTimeNewsParser
    NEWS_SCORER_AVAILABLE = True
except ImportError as e:
    log.warning(f"⚠️ Не удалось импортировать систему оценки новостей: {e}")
    NEWS_SCORER_AVAILABLE = False

# Инициализация системы оценки и парсера
news_scorer = None
news_parser = None
if NEWS_SCORER_AVAILABLE:
    try:
        news_scorer = HRTimeNewsScorer()
        news_parser = HRTimeNewsParser()
        log.info("✅ Система оценки новостей инициализирована")
    except Exception as e:
        log.error(f"❌ Ошибка инициализации системы оценки: {e}")

# Импорт адаптера для получения сообщений из канала
try:
    from services.adapters.telegram_channel_adapter import TelegramChannelAdapter
    CHANNEL_ADAPTER_AVAILABLE = True
except ImportError as e:
    log.warning(f"⚠️ Не удалось импортировать TelegramChannelAdapter: {e}")
    CHANNEL_ADAPTER_AVAILABLE = False

# Канал для отправки новостей
LEADS_CHANNEL_USERNAME = "@HRAI_ANovoselova_Leads"
LEADS_CHANNEL_URL = "https://t.me/HRAI_ANovoselova_Leads"

# Канал источник новостей
HRTIME_CHANNEL_USERNAME = "@HRTime_bot"

# Глобальное состояние для отслеживания обработанных новостей
processed_news_ids: Set[int] = set()

# Интервал проверки новостей (в секундах)
news_check_interval = int(os.getenv("HRTIME_NEWS_CHECK_INTERVAL", "30"))  # 30 секунд по умолчанию


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


def format_news_message(parsed_news: Dict, score_result: Dict) -> str:
    """
    Форматирует сообщение для Telegram с оценкой и метриками
    
    Args:
        parsed_news: Распарсенные данные новости
        score_result: Результат оценки (stars, urgency, breakdown)
    
    Returns:
        Отформатированное сообщение
    """
    stars = score_result.get("stars", 3)
    urgency = score_result.get("urgency", "НОРМАЛЬНО")
    title = parsed_news.get("title", "Новость из HR Time")
    content = parsed_news.get("content", "")
    author = parsed_news.get("author", {})
    author_name = author.get("name", "Неизвестно")
    author_status = author.get("status", "")
    date = parsed_news.get("date")
    category = parsed_news.get("category", "Общее")
    metrics = parsed_news.get("metrics", {})
    url = parsed_news.get("url", "")
    
    # Форматируем дату
    if isinstance(date, datetime):
        date_str = date.strftime("%d %B %Y, %H:%M")
    else:
        date_str = "Не указана"
    
    # Формируем звезды
    stars_emoji = "⭐" * stars
    
    # Определяем эмодзи для типа контента
    content_type = parsed_news.get("type", "general")
    type_emoji = {
        "discussion": "💬",
        "material": "📄",
        "review": "⭐",
        "request": "📋",
        "general": "📰"
    }.get(content_type, "📰")
    
    # Определяем метку источника (в правом верхнем углу)
    # Используем пробелы для визуального выравнивания вправо
    source_label = "📢 HRTIME"
    
    # Формируем сообщение с меткой источника в правом верхнем углу
    # Используем форматирование для размещения метки справа
    header_line = f"🔔 [ОЦЕНКА: {stars_emoji}] {type_emoji} {urgency}"
    # Добавляем метку источника в конец строки с выравниванием
    message_parts = [
        f"{header_line:<50} {source_label}",
        "",
        f"📌 \"{title}\"",
        "",
        f"👤 Автор: {author_name}" + (f" ({author_status})" if author_status else ""),
        f"📅 Дата: {date_str}",
        f"📂 Категория: {category}",
        ""
    ]
    
    if content:
        message_parts.append("📝 Краткое содержание:")
        message_parts.append(content[:300] + ("..." if len(content) > 300 else ""))
        message_parts.append("")
    
    # Добавляем метрики
    views = metrics.get("views", 0)
    comments = metrics.get("comments", 0)
    rating = metrics.get("rating", 0)
    
    if views > 0 or comments > 0 or rating > 0:
        message_parts.append("📊 Метрики:")
        if views > 0:
            message_parts.append(f"👁️ Просмотров: {views}")
        if comments > 0:
            message_parts.append(f"💬 Комментариев: {comments}")
        if rating > 0:
            message_parts.append(f"⭐ Рейтинг: {rating}")
        message_parts.append("")
    
    # Добавляем URL если есть
    if url:
        message_parts.append(f"🔗 [Посмотреть полностью]({url})")
        message_parts.append("")
    
    # Добавляем информацию об оценке
    breakdown = score_result.get("breakdown", {})
    if breakdown:
        message_parts.append("---")
        message_parts.append(f"Оценка: {urgency} (⭐{stars})")
        message_parts.append(f"Релевантность: {breakdown.get('relevance', 0):.1%} | "
                            f"Популярность: {breakdown.get('popularity', 0):.1%} | "
                            f"Свежесть: {breakdown.get('freshness', 0):.1%}")
    
    return "\n".join(message_parts)


async def send_news_notification(bot, news_data: Dict):
    """Отправка новой новости в канал лидов с классификацией и оценкой
    
    Все новые новости автоматически отправляются в канал https://t.me/HRAI_ANovoselova_Leads
    с оценкой от 1 до 5 звезд и метриками.
    """
    try:
        log.info("=" * 80)
        log.info("📰 НАЧАЛО ОБРАБОТКИ НОВОСТИ HR TIME")
        log.info(f"📤 Канал назначения: {LEADS_CHANNEL_URL}")
        log.info("=" * 80)
        
        message_id = news_data.get("message_id", "")
        text = news_data.get("text", "")
        date = news_data.get("date")
        chat_username = news_data.get("chat_username", "")
        
        log.info(f"📰 ID сообщения: {message_id}")
        log.info(f"📄 Длина текста: {len(text)} символов")
        log.info(f"📅 Дата: {date}")
        
        # Убеждаемся, что ID канала установлен
        if not await ensure_channel_id_set(bot):
            log.error("❌ Не удалось установить ID канала, новость не будет отправлена")
            return
        
        # Парсим новость
        parsed_news = None
        if news_parser:
            try:
                parsed_news = news_parser.parse_news(text, news_data)
                log.info(f"✅ Новость распарсена: {parsed_news.get('title', 'Без заголовка')}")
            except Exception as e:
                log.warning(f"⚠️ Ошибка парсинга новости: {e}")
                parsed_news = {
                    "id": message_id,
                    "title": text[:100] if text else "Новость из HR Time",
                    "content": text[:300] if text else "",
                    "author": {"name": chat_username or "HR Time"},
                    "date": date,
                    "type": "general",
                    "url": "",
                    "category": "Общее",
                    "metrics": {}
                }
        else:
            # Базовый парсинг без парсера
            parsed_news = {
                "id": message_id,
                "title": text[:100] if text else "Новость из HR Time",
                "content": text[:300] if text else "",
                "author": {"name": chat_username or "HR Time"},
                "date": date,
                "type": "general",
                "url": "",
                "category": "Общее",
                "metrics": {}
            }
        
        # Оцениваем новость
        score_result = None
        if news_scorer:
            try:
                score_result = news_scorer.calculate_total_score(parsed_news)
                stars = score_result.get("stars", 3)
                urgency = score_result.get("urgency", "НОРМАЛЬНО")
                log.info(f"✅ Новость оценена: ⭐{stars} ({urgency})")
                
                # Проверяем, нужно ли публиковать
                if not news_scorer.should_publish(parsed_news, min_stars=2):
                    log.info(f"⏭️  Новость не соответствует критериям публикации (минимум 2 звезды)")
                    return
            except Exception as e:
                log.warning(f"⚠️ Ошибка оценки новости: {e}")
                score_result = {
                    "stars": 3,
                    "urgency": "НОРМАЛЬНО",
                    "breakdown": {}
                }
        else:
            score_result = {
                "stars": 3,
                "urgency": "НОРМАЛЬНО",
                "breakdown": {}
            }
        
        # Классифицируем через LLM (дополнительно)
        news_category = "service"
        confidence = 0.5
        reason = ""
        if SCENARIO_WORKFLOWS_AVAILABLE:
            try:
                title = parsed_news.get("title", "")
                body = parsed_news.get("content", text)
                classification = await classify_email_type(title, body)
                news_category = classification.get("category", "service")
                confidence = classification.get("confidence", 0.5)
                reason = classification.get("reason", "")
                log.info(f"✅ LLM классификация: {news_category} (уверенность: {confidence:.2f})")
            except Exception as e:
                log.warning(f"⚠️ Ошибка LLM классификации: {e}")
        
        # Формируем сообщение
        if score_result:
            formatted_message = format_news_message(parsed_news, score_result)
        else:
            # Fallback форматирование
            formatted_message = f"📰 {parsed_news.get('title', 'Новость из HR Time')}\n\n{parsed_news.get('content', '')}"
        
        # Отправляем в канал
        if sw_module and sw_module.TELEGRAM_LEADS_CHANNEL_ID:
            try:
                await bot.send_message(
                    chat_id=sw_module.TELEGRAM_LEADS_CHANNEL_ID,
                    text=formatted_message,
                    parse_mode="Markdown",
                    disable_web_page_preview=False
                )
                log.info("=" * 80)
                log.info(f"✅ НОВОСТЬ УСПЕШНО ОТПРАВЛЕНА В КАНАЛ {LEADS_CHANNEL_URL}")
                log.info(f"   ⭐ Оценка: {score_result.get('stars', 3)} звезд")
                log.info(f"   🏷️  Категория: {news_category}")
                log.info(f"   📊 Уверенность: {confidence:.2f}")
                log.info("=" * 80)
            except Exception as e:
                log.error("=" * 80)
                log.error(f"❌ ОШИБКА ОТПРАВКИ НОВОСТИ В КАНАЛ:")
                log.error(f"❌ {str(e)}")
                log.error("=" * 80)
                import traceback
                log.error(traceback.format_exc())
                log.error("=" * 80)
        else:
            log.warning("=" * 80)
            log.warning("⚠️ ID канала не установлен, новость не отправлена")
            log.warning("=" * 80)
                
    except Exception as e:
        log.error("=" * 80)
        log.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА ОБРАБОТКИ НОВОСТИ:")
        log.error(f"❌ {str(e)}")
        log.error("=" * 80)
        import traceback
        log.error(traceback.format_exc())
        log.error("=" * 80)


async def hrtime_news_monitor_task(bot):
    """
    Фоновая задача для мониторинга новых новостей из HR Time
    
    Получает новости из Telegram канала @HRTime_bot и отправляет их в канал лидов
    с классификацией через LLM.
    
    Args:
        bot: Telegram Bot instance
    """
    global processed_news_ids
    
    log.info("=" * 80)
    log.info(f"🚀 ЗАПУСК ФОНОВОЙ ЗАДАЧИ МОНИТОРИНГА НОВОСТЕЙ HR TIME")
    log.info(f"📰 Интервал проверки: {news_check_interval} секунд")
    log.info(f"📊 Обработано новостей: {len(processed_news_ids)}")
    log.info(f"📤 Канал для отправки: {LEADS_CHANNEL_URL}")
    log.info(f"📢 Источник новостей: {HRTIME_CHANNEL_USERNAME}")
    
    # Проверяем и устанавливаем ID канала при запуске
    if bot:
        await ensure_channel_id_set(bot)
        if sw_module and sw_module.TELEGRAM_LEADS_CHANNEL_ID:
            log.info(f"✅ ID канала установлен: {sw_module.TELEGRAM_LEADS_CHANNEL_ID}")
        else:
            log.warning(f"⚠️ ID канала не установлен, будет попытка получить автоматически при первой новости")
    
    # Инициализируем адаптер для получения сообщений из канала
    channel_adapter = None
    if CHANNEL_ADAPTER_AVAILABLE:
        try:
            channel_adapter = TelegramChannelAdapter()
            log.info(f"✅ Адаптер канала инициализирован")
        except Exception as e:
            log.error(f"❌ Ошибка инициализации адаптера канала: {e}")
    else:
        log.warning(f"⚠️ Адаптер канала недоступен")
    
    log.info("=" * 80)
    
    iteration = 0
    
    while True:
        iteration += 1
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.info(f"\n🔄 Итерация #{iteration} | {current_time}")
            log.info(f"📬 Проверка новых новостей из {HRTIME_CHANNEL_USERNAME}...")
            
            if not channel_adapter:
                log.warning("⚠️ Адаптер канала недоступен, пропускаю проверку")
                await asyncio.sleep(news_check_interval)
                continue
            
            # Получаем обновления из канала
            # Используем get_channel_updates для получения новых сообщений
            updates = await channel_adapter.get_channel_updates(limit=50)
            
            if updates:
                log.info(f"📰 Найдено {len(updates)} сообщений из канала")
                
                # Фильтруем только новые сообщения
                new_news = []
                for news in updates:
                    message_id = news.get("message_id", 0)
                    if message_id and message_id not in processed_news_ids:
                        # Проверяем, что это сообщение из нужного канала
                        if channel_adapter.is_channel_message(news):
                            new_news.append(news)
                
                if new_news:
                    log.info(f"✅ Найдено {len(new_news)} новых новостей!")
                    
                    # Обрабатываем каждую новость
                    for news in new_news:
                        message_id = news.get("message_id", 0)
                        if message_id:
                            log.info(f"📰 Обработка новости ID: {message_id}")
                            await send_news_notification(bot, news)
                            processed_news_ids.add(message_id)
                            log.info(f"✅ Новость обработана и добавлена в список обработанных")
                            
                            # Небольшая задержка между обработкой новостей
                            await asyncio.sleep(1)
                    
                    log.info(f"📊 Всего обработано: {len(processed_news_ids)}")
                else:
                    log.info(f"📭 Новых новостей не найдено")
            else:
                log.info(f"📭 Сообщений из канала не получено")
            
            log.info(f"⏳ Ожидание {news_check_interval} секунд до следующей проверки...")
            
            # Ждем перед следующей проверкой
            await asyncio.sleep(news_check_interval)
            
        except Exception as e:
            log.error("=" * 80)
            log.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в мониторинге новостей HR Time!")
            log.error(f"❌ Ошибка: {str(e)}")
            log.error("=" * 80)
            import traceback
            log.error(traceback.format_exc())
            log.error("=" * 80)
            log.info(f"⏳ Повторная попытка через {news_check_interval} секунд...")
            # При ошибке ждем перед следующей попыткой
            await asyncio.sleep(news_check_interval)
