#!/usr/bin/env python3
"""
Скрипт для отправки тестового сообщения "test" в канал HRAI_ANovoselova_Лиды

Использование:
    python scripts/send_test_to_channel.py
    python scripts/send_test_to_channel.py --channel-id "-1001234567890"
    TELEGRAM_LEADS_CHANNEL_ID="-1001234567890" python scripts/send_test_to_channel.py
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

# Загружаем переменные окружения
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_LEADS_CHANNEL_ID = os.getenv("TELEGRAM_LEADS_CHANNEL_ID")


async def send_test_message(channel_id: str = None):
    """Отправить тестовое сообщение 'test' в канал лидов"""
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не установлен")
        print("   Установите переменную окружения TELEGRAM_TOKEN или TELEGRAM_BOT_TOKEN")
        return False
    
    # Используем переданный ID или из переменной окружения
    target_channel_id = channel_id or TELEGRAM_LEADS_CHANNEL_ID
    
    if not target_channel_id:
        print("❌ Ошибка: ID канала не указан")
        print("\n   Способы указать ID канала:")
        print("   1. Передать как аргумент: --channel-id '-1001234567890'")
        print("   2. Установить переменную окружения: TELEGRAM_LEADS_CHANNEL_ID='-1001234567890'")
        print("   3. Добавить в .env файл: TELEGRAM_LEADS_CHANNEL_ID=-1001234567890")
        print("\n   Как получить ID канала:")
        print("   - Добавьте бота в канал как администратора")
        print("   - Отправьте сообщение в канал")
        print("   - Используйте @userinfobot или @getidsbot для получения ID")
        return False
    
    try:
        # Создаем бота
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        print(f"📤 Отправка сообщения 'test' в канал {target_channel_id}...")
        
        # Отправляем сообщение
        await bot.send_message(
            chat_id=target_channel_id,
            text="test"
        )
        
        print(f"✅ Сообщение 'test' успешно отправлено в канал HRAI_ANovoselova_Лиды!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения: {e}")
        print("\n   Возможные причины:")
        print("   - Бот не добавлен в канал как администратор")
        print("   - Неверный ID канала")
        print("   - Неверный токен бота")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Отправить тестовое сообщение в канал лидов")
    parser.add_argument(
        "--channel-id",
        type=str,
        help="ID канала Telegram (например: -1001234567890)"
    )
    
    args = parser.parse_args()
    
    success = asyncio.run(send_test_message(channel_id=args.channel_id))
    sys.exit(0 if success else 1)
