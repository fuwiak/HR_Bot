"""
Скрипт для диагностики подключения к Yandex Mail
Проверяет IMAP и SMTP подключения
"""
import os
import imaplib
import smtplib
from dotenv import load_dotenv

load_dotenv()

def test_imap_connection():
    """Тест IMAP подключения"""
    print("=" * 70)
    print("🔍 ТЕСТ IMAP ПОДКЛЮЧЕНИЯ")
    print("=" * 70)
    
    email = os.getenv("YANDEX_EMAIL")
    # Поддерживаем YANDEX_IMAP_PASSWORD или YANDEX_PASSWORD
    password = os.getenv("YANDEX_IMAP_PASSWORD") or os.getenv("YANDEX_PASSWORD")
    server = os.getenv("YANDEX_IMAP_SERVER", "imap.yandex.ru")
    port = int(os.getenv("YANDEX_IMAP_PORT", 993))
    
    if not email or not password:
        print("❌ YANDEX_EMAIL или YANDEX_PASSWORD не установлены в .env")
        return False
    
    print(f"📧 Email: {email}")
    print(f"🌐 Сервер: {server}:{port}")
    
    # Определяем источник пароля
    password_source = "YANDEX_IMAP_PASSWORD" if os.getenv("YANDEX_IMAP_PASSWORD") else "YANDEX_PASSWORD"
    print(f"🔑 Пароль: {'*' * len(password)} ({len(password)} символов) из {password_source}")
    
    # Анализ пароля
    print("\n📋 АНАЛИЗ ПАРОЛЯ:")
    if len(password) == 16 or (len(password) == 19 and password.count('-') == 3):
        print("   ✅ Длина соответствует паролю приложения (16 символов)")
        if '-' in password:
            print("   ✅ Формат с дефисами (пароль приложения)")
        else:
            print("   ✅ Формат без дефисов (пароль приложения)")
    else:
        print(f"   ⚠️ Длина: {len(password)} символов (пароль приложения обычно 16)")
        print("   ⚠️ Похоже на обычный пароль, а не пароль приложения")
        if "HRAI" in password or "Novoselova" in password:
            print("   ❌ Содержит слова - это обычный пароль, не пароль приложения!")
            print("   💡 Нужен пароль приложения: https://id.yandex.ru/security/app-passwords")
    print()
    
    try:
        print("🔌 Подключение к серверу...")
        imap = imaplib.IMAP4_SSL(server, port)
        print("✅ Подключение установлено")
        
        print("🔐 Попытка авторизации...")
        imap.login(email, password)
        print("✅ Авторизация успешна!")
        
        print("📁 Проверка папок...")
        status, folders = imap.list()
        if status == "OK":
            print(f"✅ Найдено папок: {len(folders)}")
            print("   Доступные папки:")
            for folder in folders[:5]:  # Показываем первые 5
                print(f"   - {folder.decode()}")
        
        print("📬 Выбор папки INBOX...")
        status, messages = imap.select("INBOX")
        if status == "OK":
            num_messages = int(messages[0])
            print(f"✅ INBOX доступен. Писем в папке: {num_messages}")
        
        imap.logout()
        print("\n🎉 IMAP подключение работает корректно!")
        return True
        
    except imaplib.IMAP4.error as e:
        error_msg = str(e)
        print(f"\n❌ Ошибка IMAP: {error_msg}")
        
        if "AUTHENTICATIONFAILED" in error_msg or "LOGIN" in error_msg:
            print("\n💡 ДИАГНОСТИКА ПРОБЛЕМЫ:")
            
            # Проверяем формат пароля
            is_app_password = (len(password) == 16 or (len(password) == 19 and password.count('-') == 3))
            is_regular_password = any(word in password for word in ["HRAI", "Novoselova", "123"])
            
            if is_regular_password:
                print("\n   ❌ ПРОБЛЕМА: Используется ОБЫЧНЫЙ ПАРОЛЬ вместо пароля приложения!")
                print("\n   📝 РЕШЕНИЕ:")
                print("   1. Откройте: https://id.yandex.ru/security/app-passwords")
                print("   2. Создайте пароль приложения для 'Почта'")
                print("   3. Замените YANDEX_PASSWORD в .env на пароль приложения")
                print("   4. Пароль приложения выглядит как: abcd-efgh-ijkl-mnop (16 символов)")
            else:
                print("\n   ⚠️ Пароль похож на пароль приложения, но все равно ошибка")
                print("\n   📝 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
                print("   1. Пароль приложения отозван или неверный")
                print("   2. IMAP не включен в настройках (проверьте еще раз)")
                print("   3. Пароль скопирован с ошибкой (лишние пробелы)")
            
            print("\n   🔗 Ссылки:")
            print("   - Пароли приложений: https://id.yandex.ru/security/app-passwords")
            print("   - Настройки почты: https://mail.yandex.ru")
            print("   - Безопасность: https://id.yandex.ru/security")
        
        return False
        
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_smtp_connection():
    """Тест SMTP подключения"""
    print("\n" + "=" * 70)
    print("🔍 ТЕСТ SMTP ПОДКЛЮЧЕНИЯ")
    print("=" * 70)
    
    email = os.getenv("YANDEX_EMAIL")
    # Поддерживаем YANDEX_IMAP_PASSWORD или YANDEX_PASSWORD
    password = os.getenv("YANDEX_IMAP_PASSWORD") or os.getenv("YANDEX_PASSWORD")
    server = os.getenv("YANDEX_SMTP_SERVER", "smtp.yandex.ru")
    port = int(os.getenv("YANDEX_SMTP_PORT", 465))
    
    if not email or not password:
        print("❌ YANDEX_EMAIL или YANDEX_PASSWORD не установлены в .env")
        return False
    
    print(f"📧 Email: {email}")
    print(f"🌐 Сервер: {server}:{port}")
    
    # Определяем источник пароля
    password_source = "YANDEX_IMAP_PASSWORD" if os.getenv("YANDEX_IMAP_PASSWORD") else "YANDEX_PASSWORD"
    print(f"🔑 Пароль: {'*' * len(password)} ({len(password)} символов) из {password_source}")
    
    # Анализ пароля
    print("\n📋 АНАЛИЗ ПАРОЛЯ:")
    if len(password) == 16 or (len(password) == 19 and password.count('-') == 3):
        print("   ✅ Длина соответствует паролю приложения (16 символов)")
    else:
        print(f"   ⚠️ Длина: {len(password)} символов (пароль приложения обычно 16)")
        if "HRAI" in password or "Novoselova" in password:
            print("   ❌ Содержит слова - это обычный пароль, не пароль приложения!")
    print()
    
    try:
        print("🔌 Подключение к серверу...")
        smtp = smtplib.SMTP_SSL(server, port)
        print("✅ Подключение установлено")
        
        print("🔐 Попытка авторизации...")
        smtp.login(email, password)
        print("✅ Авторизация успешна!")
        
        smtp.quit()
        print("\n🎉 SMTP подключение работает корректно!")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ Ошибка авторизации SMTP: {e}")
        
        # Проверяем формат пароля
        is_regular_password = any(word in password for word in ["HRAI", "Novoselova", "123"])
        
        if is_regular_password:
            print("\n💡 ПРОБЛЕМА: Используется ОБЫЧНЫЙ ПАРОЛЬ!")
            print("   📝 Нужен пароль приложения: https://id.yandex.ru/security/app-passwords")
        else:
            print("\n💡 ВОЗМОЖНЫЕ РЕШЕНИЯ:")
            print("   1. Используйте пароль приложения (если включена 2FA)")
            print("   2. Проверьте правильность пароля")
            print("   3. Убедитесь, что нет лишних пробелов в .env")
        return False
        
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Главная функция"""
    print("\n" + "=" * 70)
    print("🧪 ДИАГНОСТИКА ПОДКЛЮЧЕНИЯ К YANDEX MAIL")
    print("=" * 70)
    print()
    
    imap_ok = test_imap_connection()
    smtp_ok = test_smtp_connection()
    
    print("\n" + "=" * 70)
    print("📊 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ")
    print("=" * 70)
    print(f"IMAP: {'✅ Работает' if imap_ok else '❌ Ошибка'}")
    print(f"SMTP: {'✅ Работает' if smtp_ok else '❌ Ошибка'}")
    
    if not imap_ok or not smtp_ok:
        print("\n" + "=" * 70)
        print("📝 ИНСТРУКЦИЯ ПО ИСПРАВЛЕНИЮ")
        print("=" * 70)
        print("\n1. ВКЛЮЧИТЕ IMAP В YANDEX MAIL:")
        print("   - Откройте https://mail.yandex.ru")
        print("   - Настройки → Почтовые программы")
        print("   - Включите 'С сервера imap.yandex.ru по протоколу IMAP'")
        print("   - Сохраните изменения")
        print("\n2. ЕСЛИ ВКЛЮЧЕНА 2FA (двухфакторная аутентификация):")
        print("   - Откройте https://id.yandex.ru/security/app-passwords")
        print("   - Создайте пароль приложения для 'Почта'")
        print("   - Используйте этот пароль в .env вместо обычного пароля")
        print("\n3. ПРОВЕРЬТЕ ПАРОЛЬ В .env:")
        print("   - Убедитесь, что пароль правильный")
        print("   - Нет лишних пробелов")
        print("   - Используется пароль приложения (если 2FA включена)")
        print("\n4. ПЕРЕЗАПУСТИТЕ ТЕСТ:")
        print("   python test_email_connection.py")
        print()
    else:
        print("\n🎉 ВСЕ ПОДКЛЮЧЕНИЯ РАБОТАЮТ!")
        print("✅ Можно использовать email функции в боте")
        print()

if __name__ == "__main__":
    main()
