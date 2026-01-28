#!/usr/bin/env python3
"""
Скрипт для попытки отправки тестового сообщения с несколькими вариантами username
"""
import os
import sys
import asyncio
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")


async def try_send_test():
    """Попробовать отправить тестовое сообщение с разными вариантами"""
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не установлен")
        return False
    
    # Варианты username для попытки
    variants = [
        "@HRAI_ANovoselova_Лиды",
        "HRAI_ANovoselova_Лиды",
        "@HRAI_ANovoselova_Лиды",
    ]
    
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    print("🔍 Попытка отправить сообщение 'test' в канал...")
    print("   Проверяю несколько вариантов username...\n")
    
    for variant in variants:
        try:
            # Пытаемся получить информацию о канале
            print(f"   Пробую: {variant}...")
            chat = await bot.get_chat(variant)
            channel_id = chat.id
            
            print(f"   ✅ Найден ID: {channel_id}")
            print(f"   📤 Отправляю сообщение 'test'...")
            
            # Отправляем сообщение
            await bot.send_message(
                chat_id=channel_id,
                text="test"
            )
            
            print(f"\n✅ УСПЕХ! Сообщение 'test' отправлено в канал!")
            print(f"\n📋 ID канала для использования:")
            print(f"   TELEGRAM_LEADS_CHANNEL_ID={channel_id}")
            print(f"\n   Добавьте в .env файл:")
            print(f"   TELEGRAM_LEADS_CHANNEL_ID={channel_id}")
            
            return True
            
        except TelegramError as e:
            error_msg = str(e)
            if "Chat not found" in error_msg:
                print(f"   ❌ Канал не найден: {variant}")
            elif "Not enough rights" in error_msg or "rights" in error_msg.lower():
                print(f"   ⚠️ Недостаточно прав для {variant}")
                print(f"      Убедитесь, что бот имеет права на отправку сообщений")
            else:
                print(f"   ❌ Ошибка для {variant}: {error_msg}")
            continue
        except Exception as e:
            print(f"   ❌ Неожиданная ошибка для {variant}: {e}")
            continue
    
    print("\n❌ Не удалось отправить сообщение ни одним из способов")
    print("\n💡 Возможные решения:")
    print("   1. Убедитесь, что бот @HR2137_bot добавлен в канал как администратор")
    print("   2. Проверьте, что бот имеет права на отправку сообщений")
    print("   3. Проверьте правильность username канала")
    print("   4. Попробуйте получить ID канала через @userinfobot")
    print("\n   Если у вас есть ID канала (начинается с -100), используйте:")
    print("   python scripts/send_test_to_channel.py --channel-id '-1001234567890'")
    
    return False


if __name__ == "__main__":
    success = asyncio.run(try_send_test())
    sys.exit(0 if success else 1)
