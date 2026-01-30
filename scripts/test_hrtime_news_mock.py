"""
Скрипт для отправки тестового сообщения HRTime в канал HRAI_ANovoselova_Leads
Проверяет работу системы оценки и форматирования новостей с меткой источника
"""
import os
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from telegram import Bot

# Загружаем переменные окружения
load_dotenv()

# Импортируем систему оценки и форматирования
from services.services.hrtime_news_scorer import HRTimeNewsScorer
from services.services.hrtime_news_parser import HRTimeNewsParser
from telegram_bot.services.hrtime_news_monitor import format_news_message, send_news_notification


async def send_hrtime_mock_message():
    """Отправляет тестовое сообщение HRTime в канал"""
    
    # Получаем токен бота и ID канала
    bot_token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_LEADS_CHANNEL_ID")
    channel_username = "@HRAI_ANovoselova_Leads"
    
    if not bot_token:
        print("❌ TELEGRAM_TOKEN или TELEGRAM_BOT_TOKEN не установлен")
        return
    
    # Инициализируем бота
    bot = Bot(token=bot_token)
    
    # Если ID канала не установлен, пытаемся получить его автоматически
    if not channel_id:
        try:
            chat = await bot.get_chat(channel_username)
            channel_id = str(chat.id)
            print(f"✅ ID канала получен автоматически: {channel_id}")
        except Exception as e:
            print(f"❌ Не удалось получить ID канала: {e}")
            return
    else:
        print(f"✅ Используется ID канала: {channel_id}")
    
    # Создаем тестовые данные новости HRTime
    test_text = """
    Новый запрос на услуги рекрутинга
    
    Ищу HR-консультанта для подбора персонала в IT-компанию.
    Нужна помощь с разработкой процесса найма и проведения интервью.
    
    Требования:
    - Опыт работы с IT-специалистами
    - Знание современных методов рекрутинга
    - Умение проводить технические интервью
    
    Бюджет: 150 000 руб
    Срок: до 15 февраля
    
    👁️ 750 просмотров
    💬 35 комментариев
    ⭐ Рейтинг: 4.8
    """
    
    test_raw_data = {
        "message_id": "hrtime_test_456",
        "date": datetime.now() - timedelta(hours=1),  # 1 час назад
        "chat_username": "Анна Петрова ТОП-30",
        "text": test_text
    }
    
    print("\n📋 Тестовые данные HRTime:")
    print(f"   Заголовок: Новый запрос на услуги рекрутинга")
    print(f"   Автор: Анна Петрова ТОП-30")
    print(f"   Дата: {test_raw_data['date']}")
    
    # Используем функцию send_news_notification для полной обработки
    print("\n🔄 Обработка новости через систему мониторинга...")
    
    try:
        await send_news_notification(bot, test_raw_data)
        print(f"\n✅ Тестовое сообщение HRTime успешно отправлено в канал {channel_username}")
        print(f"   Проверьте канал: https://t.me/HRAI_ANovoselova_Leads")
        print(f"   Должна быть метка: 📢 HRTIME в правом верхнем углу")
    except Exception as e:
        print(f"\n❌ Ошибка отправки сообщения: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    print("🚀 Запуск теста отправки HRTime сообщения в канал...")
    asyncio.run(send_hrtime_mock_message())
