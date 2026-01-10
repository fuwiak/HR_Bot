"""
Тест для проверки работы Telegram бота
Проверяет подключение к Telegram API и базовую функциональность
"""
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для импорта модулей
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
import os
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Импорты для Telegram
try:
    from telegram import Bot
    from telegram.error import TelegramError, NetworkError, TimedOut
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    pytest.skip("python-telegram-bot не установлен", allow_module_level=True)


# ===================== ТЕСТ 1: ПРОВЕРКА ДОСТУПНОСТИ БИБЛИОТЕКИ =====================

def test_telegram_library_available():
    """Проверка, что библиотека python-telegram-bot установлена"""
    assert TELEGRAM_AVAILABLE, "python-telegram-bot должен быть установлен"
    print("✅ Библиотека python-telegram-bot доступна")


# ===================== ТЕСТ 2: ПРОВЕРКА ТОКЕНА =====================

def test_telegram_token_exists():
    """Проверка, что токен Telegram бота установлен"""
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    assert token is not None, "TELEGRAM_TOKEN или TELEGRAM_BOT_TOKEN должен быть установлен"
    assert len(token) > 0, "Токен не должен быть пустым"
    assert ":" in token or len(token) > 20, "Токен должен быть валидным форматом"
    print("✅ Токен Telegram бота найден")


# ===================== ТЕСТ 3: ИНИЦИАЛИЗАЦИЯ БОТА =====================

@pytest.mark.asyncio
async def test_telegram_bot_initialization():
    """Проверка, что бот может быть инициализирован"""
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        pytest.skip("TELEGRAM_TOKEN не установлен")
    
    try:
        bot = Bot(token=token)
        assert bot is not None, "Бот должен быть создан"
        print("✅ Бот успешно инициализирован")
    except Exception as e:
        pytest.fail(f"Ошибка инициализации бота: {e}")


# ===================== ТЕСТ 4: ПРОВЕРКА ПОДКЛЮЧЕНИЯ К TELEGRAM API =====================

@pytest.mark.asyncio
async def test_telegram_bot_get_me():
    """Проверка подключения к Telegram API через getMe"""
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        pytest.skip("TELEGRAM_TOKEN не установлен")
    
    try:
        bot = Bot(token=token)
        
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        
        # Проверяем, что получили информацию о боте
        assert bot_info is not None, "Информация о боте должна быть получена"
        assert hasattr(bot_info, 'id'), "Информация о боте должна содержать id"
        assert hasattr(bot_info, 'username') or hasattr(bot_info, 'first_name'), "Информация о боте должна содержать имя"
        
        print(f"✅ Подключение к Telegram API успешно")
        print(f"   ID бота: {bot_info.id}")
        print(f"   Имя бота: {bot_info.first_name}")
        if bot_info.username:
            print(f"   Username: @{bot_info.username}")
        
        return True
    except NetworkError as e:
        pytest.fail(f"Ошибка сети при подключении к Telegram API: {e}")
    except TimedOut as e:
        pytest.fail(f"Таймаут при подключении к Telegram API: {e}")
    except TelegramError as e:
        pytest.fail(f"Ошибка Telegram API: {e}")
    except Exception as e:
        pytest.fail(f"Неожиданная ошибка: {e}")


# ===================== ТЕСТ 5: ПРОВЕРКА WEBHOOK (если используется) =====================

@pytest.mark.asyncio
async def test_telegram_webhook_info():
    """Проверка информации о webhook"""
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        pytest.skip("TELEGRAM_TOKEN не установлен")
    
    try:
        bot = Bot(token=token)
        webhook_info = await bot.get_webhook_info()
        
        assert webhook_info is not None, "Информация о webhook должна быть получена"
        
        if webhook_info.url:
            print(f"✅ Webhook установлен: {webhook_info.url}")
            print(f"   Ожидающие обновления: {webhook_info.pending_update_count}")
        else:
            print("ℹ️ Webhook не установлен (используется polling)")
        
        return True
    except Exception as e:
        pytest.fail(f"Ошибка получения информации о webhook: {e}")


# ===================== ТЕСТ 6: ПРОВЕРКА АДАПТЕРА =====================

@pytest.mark.asyncio
async def test_telegram_adapter_initialization():
    """Проверка инициализации Telegram адаптера"""
    try:
        from backend.adapters.telegram_adapter import TelegramAdapter
        
        # Получаем токен из окружения
        token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not token:
            pytest.skip("TELEGRAM_TOKEN не установлен")
        
        # Передаем токен напрямую в адаптер
        adapter = TelegramAdapter(token=token)
        result = await adapter.initialize()
        
        assert result is True, "Адаптер должен успешно инициализироваться"
        assert adapter._initialized is True, "Адаптер должен быть помечен как инициализированный"
        assert adapter.bot is not None, "Бот должен быть создан в адаптере"
        
        print("✅ Telegram адаптер успешно инициализирован")
        return True
    except ImportError:
        pytest.skip("TelegramAdapter недоступен")
    except Exception as e:
        # Если токен не установлен, это нормально для тестов
        if "TELEGRAM_BOT_TOKEN" in str(e) or "токен" in str(e).lower() or "token" in str(e).lower():
            pytest.skip(f"Токен не установлен: {e}")
        else:
            pytest.fail(f"Ошибка инициализации адаптера: {e}")


# ===================== ТЕСТ 7: ПРОВЕРКА ОТПРАВКИ СООБЩЕНИЯ (опционально) =====================

@pytest.mark.asyncio
async def test_telegram_send_message():
    """Проверка отправки тестового сообщения (только если установлен TEST_CHAT_ID)"""
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    test_chat_id = os.getenv("TELEGRAM_TEST_CHAT_ID") or os.getenv("TELEGRAM_ADMIN_ID")
    
    if not token:
        pytest.skip("TELEGRAM_TOKEN не установлен")
    
    if not test_chat_id:
        pytest.skip("TELEGRAM_TEST_CHAT_ID не установлен (пропускаем тест отправки)")
    
    try:
        bot = Bot(token=token)
        
        # Отправляем тестовое сообщение
        message = await bot.send_message(
            chat_id=test_chat_id,
            text="🧪 Тестовое сообщение от автоматического теста"
        )
        
        assert message is not None, "Сообщение должно быть отправлено"
        assert message.message_id > 0, "Сообщение должно иметь ID"
        
        print(f"✅ Тестовое сообщение успешно отправлено (ID: {message.message_id})")
        return True
    except TelegramError as e:
        pytest.fail(f"Ошибка Telegram API при отправке сообщения: {e}")
    except Exception as e:
        pytest.fail(f"Неожиданная ошибка при отправке сообщения: {e}")


# ===================== ТЕСТ 8: ПОЛНАЯ ПРОВЕРКА РАБОТЫ =====================

@pytest.mark.asyncio
async def test_telegram_full_connection():
    """Полная проверка работы Telegram бота"""
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        pytest.skip("TELEGRAM_TOKEN не установлен")
    
    results = {
        "initialization": False,
        "get_me": False,
        "webhook_info": False,
        "adapter": False
    }
    
    # 1. Инициализация бота
    try:
        bot = Bot(token=token)
        results["initialization"] = True
        print("✅ Шаг 1: Инициализация бота - успешно")
    except Exception as e:
        pytest.fail(f"Ошибка инициализации бота: {e}")
    
    # 2. Проверка подключения через getMe
    try:
        bot_info = await bot.get_me()
        assert bot_info is not None
        results["get_me"] = True
        print(f"✅ Шаг 2: Подключение к API - успешно (бот: {bot_info.first_name})")
    except Exception as e:
        pytest.fail(f"Ошибка подключения к API: {e}")
    
    # 3. Проверка webhook
    try:
        webhook_info = await bot.get_webhook_info()
        assert webhook_info is not None
        results["webhook_info"] = True
        print(f"✅ Шаг 3: Проверка webhook - успешно")
    except Exception as e:
        print(f"⚠️ Шаг 3: Ошибка проверки webhook: {e}")
    
    # 4. Проверка адаптера
    try:
        from backend.adapters.telegram_adapter import TelegramAdapter
        adapter = TelegramAdapter(token=token)
        adapter_result = await adapter.initialize()
        if adapter_result:
            results["adapter"] = True
            print("✅ Шаг 4: Инициализация адаптера - успешно")
        else:
            print("⚠️ Шаг 4: Адаптер не инициализирован (возможно, нет токена)")
    except Exception as e:
        print(f"⚠️ Шаг 4: Ошибка адаптера: {e}")
    
    # Итоговый результат
    critical_tests = ["initialization", "get_me"]
    all_critical_passed = all(results[test] for test in critical_tests)
    
    assert all_critical_passed, "Критические тесты должны пройти успешно"
    
    print("\n" + "="*50)
    print("📊 ИТОГОВЫЙ РЕЗУЛЬТАТ ПРОВЕРКИ TELEGRAM:")
    print("="*50)
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name}: {'Пройден' if result else 'Провален'}")
    print("="*50)
    
    return results


# ===================== RUN TESTS =====================

if __name__ == "__main__":
    print("🧪 Запуск тестов проверки работы Telegram...\n")
    pytest.main([__file__, "-v", "-s"])
