"""
Скрипт для отправки тестового сообщения в канал HRAI_ANovoselova_Leads
Проверяет работу системы оценки и форматирования новостей
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
from telegram_bot.services.hrtime_news_monitor import format_news_message


async def send_test_message():
    """Отправляет тестовое сообщение в канал"""
    
    # Получаем токен бота и ID канала
    bot_token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_LEADS_CHANNEL_ID")
    channel_username = "@HRAI_ANovoselova_Leads"
    
    if not bot_token:
        print("❌ TELEGRAM_TOKEN или TELEGRAM_BOT_TOKEN не установлен")
        print("   Проверьте файл .env или переменные окружения")
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
            print(f"   Убедитесь, что бот добавлен в канал {channel_username} как администратор")
            return
    else:
        print(f"✅ Используется ID канала: {channel_id}")
    
    # Создаем тестовые данные новости
    test_text = """
    Вопрос по рекрутингу персонала
    
    Нужна помощь с подбором HR-специалистов для нашего проекта. 
    Как правильно провести интервью? Какие вопросы задавать?
    
    Бюджет: 100 000 руб
    Срок: до конца месяца
    
    👁️ 500 просмотров
    💬 25 комментариев
    ⭐ Рейтинг: 4.5
    """
    
    test_raw_data = {
        "message_id": "test_123",
        "date": datetime.now() - timedelta(hours=2),
        "chat_username": "Иван Иванов ТОП-30",
        "text": test_text
    }
    
    # Парсим новость
    parser = HRTimeNewsParser()
    parsed_news = parser.parse_news(test_text, test_raw_data)
    
    print("\n📋 Распарсенные данные:")
    print(f"   Заголовок: {parsed_news.get('title')}")
    print(f"   Автор: {parsed_news.get('author', {}).get('name')}")
    print(f"   Категория: {parsed_news.get('category')}")
    print(f"   Метрики: {parsed_news.get('metrics')}")
    
    # Оцениваем новость
    scorer = HRTimeNewsScorer()
    score_result = scorer.calculate_total_score(parsed_news)
    
    print(f"\n⭐ Оценка новости:")
    print(f"   Звезд: {score_result.get('stars')}")
    print(f"   Срочность: {score_result.get('urgency')}")
    print(f"   Общая оценка: {score_result.get('total_score'):.2%}")
    print(f"   Детализация:")
    breakdown = score_result.get('breakdown', {})
    for key, value in breakdown.items():
        print(f"      {key}: {value:.2%}")
    
    # Форматируем сообщение
    formatted_message = format_news_message(parsed_news, score_result)
    
    print(f"\n📤 Отправка сообщения в канал {channel_username}...")
    print("=" * 80)
    print(formatted_message)
    print("=" * 80)
    
    try:
        # Отправляем сообщение
        await bot.send_message(
            chat_id=channel_id,
            text=formatted_message,
            parse_mode="Markdown",
            disable_web_page_preview=False
        )
        print(f"\n✅ Тестовое сообщение успешно отправлено в канал {channel_username}")
        print(f"   Проверьте канал: https://t.me/HRAI_ANovoselova_Leads")
    except Exception as e:
        print(f"\n❌ Ошибка отправки сообщения: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    print("🚀 Запуск теста отправки сообщения в канал...")
    asyncio.run(send_test_message())
