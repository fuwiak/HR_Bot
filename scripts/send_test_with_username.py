#!/usr/bin/env python3
"""
Скрипт для отправки тестового сообщения "test" в канал по username
Попробует получить ID автоматически или использовать username напрямую

Использование:
    python scripts/send_test_with_username.py @HRAI_ANovoselova_Лиды
"""
import os
import sys
import asyncio
import argparse
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

# Загружаем переменные окружения
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")


async def send_test_by_username(channel_username: str):
    """Отправить тестовое сообщение в канал по username"""
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не установлен")
        print("   Установите переменную окружения TELEGRAM_TOKEN или TELEGRAM_BOT_TOKEN")
        return False
    
    # Убираем @ если есть и добавляем обратно
    channel_username = channel_username.lstrip('@')
    if not channel_username.startswith('@'):
        channel_username = '@' + channel_username
    
    try:
        # Создаем бота
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        print(f"🔍 Попытка получить ID канала {channel_username}...")
        
        # Пытаемся получить ID канала
        try:
            chat = await bot.get_chat(channel_username)
            channel_id = chat.id
            print(f"✅ ID канала найден: {channel_id}")
        except TelegramError:
            print(f"⚠️ Не удалось получить ID канала автоматически")
            print(f"   Попробуем отправить сообщение напрямую по username...")
            channel_id = channel_username
        
        print(f"📤 Отправка сообщения 'test' в канал {channel_username} (ID: {channel_id})...")
        
        # Отправляем сообщение
        await bot.send_message(
            chat_id=channel_id,
            text="test"
        )
        
        print(f"✅ Сообщение 'test' успешно отправлено в канал {channel_username}!")
        print(f"\n📋 ID канала для будущего использования:")
        print(f"   TELEGRAM_LEADS_CHANNEL_ID={channel_id}")
        
        return True
        
    except TelegramError as e:
        print(f"❌ Ошибка отправки сообщения: {e}")
        print("\n   Возможные причины:")
        print("   - Бот не добавлен в канал как администратор")
        print("   - Канал не существует или username неверный")
        print("   - Бот не имеет прав на отправку сообщений")
        print("\n   Решение:")
        print("   1. Добавьте бота в канал @HRAI_ANovoselova_Лиды как администратора")
        print("   2. Убедитесь, что бот имеет права на отправку сообщений")
        print("   3. Проверьте правильность username канала")
        
        # Если ошибка содержит информацию об ID, попробуем извлечь его
        error_str = str(e)
        if "chat_id" in error_str.lower() or "chat" in error_str.lower():
            print("\n   💡 Попробуйте получить ID канала другим способом:")
            print("      - Используйте @userinfobot или @getidsbot")
            print("      - Или добавьте бота в канал и попробуйте снова")
        
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Отправить тестовое сообщение в канал по username")
    parser.add_argument(
        "channel_username",
        type=str,
        help="Username канала (например: @HRAI_ANovoselova_Лиды)"
    )
    
    args = parser.parse_args()
    
    success = asyncio.run(send_test_by_username(args.channel_username))
    sys.exit(0 if success else 1)
