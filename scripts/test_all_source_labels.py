"""
Скрипт для проверки всех меток источников (YANDEX, HRTIME, WEEEK)
Отправляет тестовые сообщения для каждого источника
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

# Импортируем функции отправки
from services.agents.scenario_workflows import send_lead_to_channel


async def test_all_labels():
    """Тестирует все метки источников"""
    
    # Получаем токен бота и ID канала
    bot_token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_LEADS_CHANNEL_ID")
    channel_username = "@HRAI_ANovoselova_Leads"
    
    if not bot_token:
        print("❌ TELEGRAM_TOKEN не установлен")
        return
    
    # Инициализируем бота
    bot = Bot(token=bot_token)
    
    # Если ID канала не установлен, пытаемся получить его автоматически
    if not channel_id:
        try:
            chat = await bot.get_chat(channel_username)
            channel_id = str(chat.id)
            print(f"✅ ID канала: {channel_id}")
        except Exception as e:
            print(f"❌ Не удалось получить ID канала: {e}")
            return
    
    print("\n🧪 Тестирование меток источников...\n")
    
    # Тест 1: YANDEX (Email)
    print("1️⃣ Тест метки 📧 YANDEX (Email)...")
    yandex_lead = {
        "source": "📧 Email",
        "title": "Тестовое письмо от клиента",
        "client_name": "test@example.com",
        "client_email": "test@example.com",
        "client_phone": "",
        "message": "Здравствуйте! Интересует услуга по рекрутингу персонала.",
        "score": 0,
        "status": "new",
        "category": "",
        "email_category": "new_lead"
    }
    try:
        await send_lead_to_channel(bot, yandex_lead)
        print("   ✅ YANDEX метка отправлена\n")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}\n")
    
    await asyncio.sleep(2)
    
    # Тест 2: HRTIME
    print("2️⃣ Тест метки 📢 HRTIME...")
    hrtime_lead = {
        "source": "📢 Канал: @HRTime_bot",
        "title": "Тестовый заказ из HR Time",
        "client_name": "Иван Иванов",
        "client_email": "ivan@example.com",
        "client_phone": "+79001234567",
        "message": "Нужна помощь с подбором HR-специалистов.",
        "score": 0.8,
        "status": "warm",
        "category": "рекрутинг",
        "email_category": "new_lead"
    }
    try:
        await send_lead_to_channel(bot, hrtime_lead)
        print("   ✅ HRTIME метка отправлена\n")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}\n")
    
    await asyncio.sleep(2)
    
    # Тест 3: WEEEK (если используется)
    print("3️⃣ Тест метки для других источников...")
    other_lead = {
        "source": "💬 Telegram бот",
        "title": "Тестовый запрос через Telegram",
        "client_name": "Пользователь",
        "client_email": "",
        "client_phone": "",
        "message": "Интересует консультация по HR-процессам.",
        "score": 0.6,
        "status": "new",
        "category": "консультация",
        "email_category": "new_lead"
    }
    try:
        await send_lead_to_channel(bot, other_lead)
        print("   ✅ Другие метки отправлены\n")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}\n")
    
    print("✅ Все тесты завершены!")
    print(f"📱 Проверьте канал: https://t.me/HRAI_ANovoselova_Leads")
    print("   Должны быть видны метки: 📧 YANDEX, 📢 HRTIME, 💬 TELEGRAM")


if __name__ == "__main__":
    asyncio.run(test_all_labels())
