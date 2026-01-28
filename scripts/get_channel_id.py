#!/usr/bin/env python3
"""
Скрипт для получения ID канала Telegram по его username

Использование:
    python scripts/get_channel_id.py @HRAI_ANovoselova_Лиды
    python scripts/get_channel_id.py HRAI_ANovoselova_Лиды
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


async def get_channel_id(channel_username: str):
    """Получить ID канала по его username"""
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не установлен")
        print("   Установите переменную окружения TELEGRAM_TOKEN или TELEGRAM_BOT_TOKEN")
        return None
    
    # Убираем @ если есть
    channel_username = channel_username.lstrip('@')
    
    # Добавляем @ для Telegram API
    if not channel_username.startswith('@'):
        channel_username = '@' + channel_username
    
    try:
        # Создаем бота
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        print(f"🔍 Поиск информации о канале {channel_username}...")
        
        # Получаем информацию о канале
        chat = await bot.get_chat(channel_username)
        
        print(f"\n✅ Информация о канале:")
        print(f"   Название: {chat.title}")
        print(f"   Username: {chat.username}")
        print(f"   ID канала: {chat.id}")
        print(f"   Тип: {chat.type}")
        
        if chat.id:
            print(f"\n📋 Используйте этот ID для отправки сообщений:")
            print(f"   TELEGRAM_LEADS_CHANNEL_ID={chat.id}")
            print(f"\n   Или передайте как аргумент:")
            print(f"   python scripts/send_test_to_channel.py --channel-id '{chat.id}'")
        
        return chat.id
        
    except TelegramError as e:
        print(f"❌ Ошибка получения информации о канале: {e}")
        print("\n   Возможные причины:")
        print("   - Канал не существует или username неверный")
        print("   - Бот не добавлен в канал")
        print("   - Канал приватный и бот не имеет доступа")
        print("\n   Решение:")
        print("   1. Убедитесь, что канал существует: " + channel_username)
        print("   2. Добавьте бота в канал как администратора")
        print("   3. Если канал приватный, убедитесь, что бот имеет доступ")
        return None
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Получить ID канала Telegram по username")
    parser.add_argument(
        "channel_username",
        type=str,
        help="Username канала (например: @HRAI_ANovoselova_Лиды или HRAI_ANovoselova_Лиды)"
    )
    
    args = parser.parse_args()
    
    channel_id = asyncio.run(get_channel_id(args.channel_username))
    sys.exit(0 if channel_id else 1)
