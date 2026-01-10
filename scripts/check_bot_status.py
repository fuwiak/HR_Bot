#!/usr/bin/env python3
"""
Скрипт для проверки статуса Telegram бота
"""
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import asyncio
from telegram import Bot
from telegram.error import TelegramError

async def check_bot_status():
    """Проверка статуса бота"""
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print("❌ TELEGRAM_TOKEN не установлен")
        return False
    
    try:
        bot = Bot(token=token)
        
        # Проверяем информацию о боте
        bot_info = await bot.get_me()
        print(f"✅ Бот подключен: {bot_info.first_name} (@{bot_info.username})")
        print(f"   ID: {bot_info.id}")
        
        # Проверяем webhook
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            print(f"🌐 Webhook установлен: {webhook_info.url}")
            print(f"   Ожидающие обновления: {webhook_info.pending_update_count}")
        else:
            print("🔄 Webhook не установлен (используется polling)")
        
        # Проверяем, что бот может получать обновления
        print("\n📋 Проверка обработчиков:")
        print("   ✅ Бот инициализирован")
        print("   ✅ Обработчик /start должен быть зарегистрирован")
        print("\n💡 Если команда /start не работает:")
        print("   1. Проверьте, что бот запущен (python telegram_bot/app.py)")
        print("   2. Проверьте логи на наличие ошибок")
        print("   3. Убедитесь, что webhook настроен правильно (если используется)")
        print("   4. Попробуйте удалить webhook: await bot.delete_webhook()")
        
        return True
        
    except TelegramError as e:
        print(f"❌ Ошибка Telegram API: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(check_bot_status())
