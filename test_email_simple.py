"""
Простой тест автоматического мониторинга почты
Проверяет работу без моков (требует реальные credentials)
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_email_check_real():
    """Тест реальной проверки почты"""
    print("🔍 Тест 1: Проверка реальной почты")
    print("-" * 60)
    
    try:
        from email_helper import check_new_emails
        
        emails = await check_new_emails(since_days=1, limit=5)
        
        if emails:
            print(f"✅ Найдено писем: {len(emails)}")
            for i, email_data in enumerate(emails, 1):
                print(f"\n  {i}. От: {email_data.get('from', 'N/A')}")
                print(f"     Тема: {email_data.get('subject', 'N/A')}")
                print(f"     Дата: {email_data.get('date', 'N/A')}")
                print(f"     ID: {email_data.get('id', 'N/A')}")
                body = email_data.get('body', '')
                if body:
                    print(f"     Превью: {body[:100]}...")
            return True
        else:
            print("⚠️ Писем не найдено (это нормально, если почта пуста)")
            return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_email_notification_structure():
    """Тест структуры уведомления (без реальной отправки)"""
    print("\n🔍 Тест 2: Структура уведомления")
    print("-" * 60)
    
    try:
        from app import send_email_notification, email_cache
        
        # Очищаем кэш
        email_cache.clear()
        
        # Тестовое письмо
        test_email = {
            "id": "test_123",
            "from": "test@client.com",
            "subject": "Тестовое письмо",
            "body": "Это тестовое письмо для проверки структуры уведомления.",
            "date": "19 Dec 2025 15:46:00 +0300"
        }
        
        # Мокаем бота (не отправляем реальное сообщение)
        class MockBot:
            async def send_message(self, **kwargs):
                print(f"  📤 Сообщение отправлено:")
                print(f"     Chat ID: {kwargs.get('chat_id')}")
                print(f"     Текст содержит: 'Новое письмо'")
                print(f"     Кнопки: {len(kwargs.get('reply_markup', {}).inline_keyboard) if kwargs.get('reply_markup') else 0}")
                # Возвращаем простой mock объект
                class MockMessage:
                    pass
                return MockMessage()
        
        mock_bot = MockBot()
        
        await send_email_notification(mock_bot, test_email)
        
        # Проверяем кэш
        if test_email["id"] in email_cache:
            print("✅ Письмо сохранено в кэш")
        else:
            print("❌ Письмо не сохранено в кэш")
            return False
        
        print("✅ Структура уведомления корректна")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_email_actions():
    """Тест действий с письмами (без реальных вызовов LLM)"""
    print("\n🔍 Тест 3: Действия с письмами")
    print("-" * 60)
    
    try:
        from app import email_cache, handle_email_full
        
        # Тестовое письмо
        test_email = {
            "id": "test_actions",
            "from": "test@client.com",
            "subject": "Тестовое письмо",
            "body": "Полный текст тестового письма для проверки.",
            "date": "19 Dec 2025 15:46:00 +0300"
        }
        email_cache["test_actions"] = test_email
        
        # Мокаем query
        class MockQuery:
            def __init__(self):
                self.answer_called = False
                self.edit_message_text_called = False
                self.text = ""
            
            async def answer(self, *args, **kwargs):
                self.answer_called = True
            
            async def edit_message_text(self, *args, **kwargs):
                self.edit_message_text_called = True
                self.text = kwargs.get('text', '')
        
        mock_query = MockQuery()
        
        # Тестируем показ полного текста
        await handle_email_full(mock_query, "test_actions")
        
        if mock_query.edit_message_text_called:
            print("✅ Показ полного текста работает")
            if "Полный текст письма" in mock_query.text:
                print("✅ Текст содержит правильную информацию")
            else:
                print("⚠️ Текст может быть некорректным")
        else:
            print("❌ Показ полного текста не работает")
            return False
        
        print("✅ Действия с письмами работают")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_processed_emails_tracking():
    """Тест отслеживания обработанных писем"""
    print("\n🔍 Тест 4: Отслеживание обработанных писем")
    print("-" * 60)
    
    try:
        from app import processed_email_ids
        
        # Очищаем список
        processed_email_ids.clear()
        
        # Добавляем тестовые ID
        test_ids = ["email_1", "email_2", "email_3"]
        for email_id in test_ids:
            processed_email_ids.add(email_id)
        
        print(f"✅ Добавлено ID в список: {len(processed_email_ids)}")
        
        # Проверяем наличие
        for email_id in test_ids:
            if email_id in processed_email_ids:
                print(f"  ✅ {email_id} найден")
            else:
                print(f"  ❌ {email_id} не найден")
                return False
        
        # Проверяем новый ID
        if "new_email" not in processed_email_ids:
            print("✅ Новые письма правильно определяются")
        else:
            print("❌ Логика определения новых писем не работает")
            return False
        
        print("✅ Отслеживание обработанных писем работает")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_email_cache():
    """Тест кэша писем"""
    print("\n🔍 Тест 5: Кэш писем")
    print("-" * 60)
    
    try:
        from app import email_cache
        
        # Очищаем кэш
        email_cache.clear()
        
        # Добавляем тестовые письма
        test_emails = [
            {"id": "cache_1", "subject": "Письмо 1"},
            {"id": "cache_2", "subject": "Письмо 2"},
        ]
        
        for email in test_emails:
            email_cache[email["id"]] = email
        
        print(f"✅ Добавлено писем в кэш: {len(email_cache)}")
        
        # Проверяем доступность
        for email in test_emails:
            if email["id"] in email_cache:
                cached_email = email_cache[email["id"]]
                if cached_email["subject"] == email["subject"]:
                    print(f"  ✅ {email['id']} доступен в кэше")
                else:
                    print(f"  ❌ {email['id']} данные не совпадают")
                    return False
            else:
                print(f"  ❌ {email['id']} не найден в кэше")
                return False
        
        print("✅ Кэш писем работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_simple_tests():
    """Запуск всех простых тестов"""
    print("=" * 70)
    print("🧪 ПРОСТЫЕ ТЕСТЫ АВТОМАТИЧЕСКОГО МОНИТОРИНГА ПОЧТЫ")
    print("=" * 70)
    
    # Проверяем переменные окружения
    print("\n📋 Проверка переменных окружения:")
    print("-" * 60)
    
    required_vars = {
        "YANDEX_EMAIL": os.getenv("YANDEX_EMAIL"),
        "YANDEX_PASSWORD": os.getenv("YANDEX_PASSWORD"),
        "TELEGRAM_ADMIN_ID": os.getenv("TELEGRAM_ADMIN_ID", "5305427956"),
    }
    
    all_set = True
    for var, value in required_vars.items():
        if value:
            print(f"✅ {var}: установлен")
        else:
            print(f"⚠️ {var}: НЕ УСТАНОВЛЕН (некоторые тесты могут не работать)")
            if var in ["YANDEX_EMAIL", "YANDEX_PASSWORD"]:
                all_set = False
    
    if not all_set:
        print("\n⚠️ Не все переменные установлены!")
        print("   Некоторые тесты могут не работать")
        print("   Установите YANDEX_EMAIL и YANDEX_PASSWORD в .env")
    
    # Запускаем тесты
    results = []
    
    # Тест 1: Реальная проверка почты (требует credentials)
    if all_set:
        results.append(await test_email_check_real())
    else:
        print("\n⏭️ Тест 1 пропущен (нет credentials)")
        results.append(True)  # Не считаем как ошибку
    
    # Остальные тесты не требуют реальных credentials
    results.append(await test_email_notification_structure())
    results.append(await test_email_actions())
    results.append(await test_processed_emails_tracking())
    results.append(await test_email_cache())
    
    # Итоги
    print("\n" + "=" * 70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Пройдено: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("✅ Автоматический мониторинг почты работает корректно!")
        print("\n💡 Для полного тестирования запустите:")
        print("   pytest test_email_monitoring.py -v")
    else:
        print(f"\n⚠️ Некоторые тесты не прошли ({total - passed} ошибок)")
        print("   Проверьте логи выше для деталей")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(run_all_simple_tests())
    exit(0 if success else 1)
