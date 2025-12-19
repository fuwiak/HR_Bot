#!/usr/bin/env python3
"""
Простой тестовый скрипт для отправки email через Yandex SMTP
"""
import os
import sys
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем настройки из .env
YANDEX_EMAIL = os.getenv("YANDEX_EMAIL")
YANDEX_PASSWORD = os.getenv("YANDEX_IMAP_PASSWORD") or os.getenv("YANDEX_PASSWORD")
YANDEX_SMTP_SERVER = os.getenv("YANDEX_SMTP_SERVER", "smtp.yandex.ru")
YANDEX_SMTP_PORT = int(os.getenv("YANDEX_SMTP_PORT", 465))

print("=" * 70)
print("📧 ТЕСТ ОТПРАВКИ EMAIL ЧЕРЕЗ YANDEX SMTP")
print("=" * 70)
print(f"Email: {YANDEX_EMAIL}")
print(f"Сервер: {YANDEX_SMTP_SERVER}")
print(f"Порт: {YANDEX_SMTP_PORT}")
print(f"Пароль: {'*' * len(YANDEX_PASSWORD) if YANDEX_PASSWORD else 'НЕ УСТАНОВЛЕН'}")
print()

if not YANDEX_EMAIL or not YANDEX_PASSWORD:
    print("❌ Ошибка: YANDEX_EMAIL или YANDEX_PASSWORD не установлены в .env")
    sys.exit(1)

# Создаем тестовое письмо
to_email = "a-novoselova07@yandex.ru"
subject = "Тестовое письмо от HR Bot"
body = "Это тестовое письмо для проверки отправки email через SMTP."

message = MIMEMultipart()
message["From"] = YANDEX_EMAIL
message["To"] = to_email
message["Subject"] = subject
message.attach(MIMEText(body, "plain"))

print(f"📝 Создано письмо:")
print(f"   От: {YANDEX_EMAIL}")
print(f"   Кому: {to_email}")
print(f"   Тема: {subject}")
print()

# Устанавливаем таймаут
socket.setdefaulttimeout(30)

# Пробуем разные варианты подключения
print("🔄 Попытка 1: Порт 465 (SMTP_SSL)...")
try:
    server = smtplib.SMTP_SSL(YANDEX_SMTP_SERVER, 465, timeout=30)
    print("   ✅ Подключение установлено")
    
    server.login(YANDEX_EMAIL, YANDEX_PASSWORD)
    print("   ✅ Авторизация успешна")
    
    server.send_message(message)
    print("   ✅ Письмо отправлено")
    
    server.quit()
    print()
    print("=" * 70)
    print("✅ УСПЕХ! Письмо отправлено через порт 465")
    print("=" * 70)
    sys.exit(0)
    
except socket.timeout as e:
    print(f"   ❌ Таймаут: {e}")
except OSError as e:
    print(f"   ❌ Ошибка сети: {e}")
except smtplib.SMTPAuthenticationError as e:
    print(f"   ❌ Ошибка авторизации: {e}")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

print()
print("🔄 Попытка 2: Порт 587 (STARTTLS)...")
try:
    server = smtplib.SMTP(YANDEX_SMTP_SERVER, 587, timeout=30)
    print("   ✅ Подключение установлено")
    
    server.starttls()
    print("   ✅ STARTTLS успешно")
    
    server.login(YANDEX_EMAIL, YANDEX_PASSWORD)
    print("   ✅ Авторизация успешна")
    
    server.send_message(message)
    print("   ✅ Письмо отправлено")
    
    server.quit()
    print()
    print("=" * 70)
    print("✅ УСПЕХ! Письмо отправлено через порт 587")
    print("=" * 70)
    sys.exit(0)
    
except socket.timeout as e:
    print(f"   ❌ Таймаут: {e}")
except OSError as e:
    print(f"   ❌ Ошибка сети: {e}")
except smtplib.SMTPAuthenticationError as e:
    print(f"   ❌ Ошибка авторизации: {e}")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

print()
print("=" * 70)
print("❌ НЕУДАЧА: Не удалось отправить письмо ни через один порт")
print("=" * 70)
print()
print("Возможные причины:")
print("1. Проблемы с сетью (блокировка портов 465 и 587)")
print("2. Неправильный пароль приложения")
print("3. Проблемы с Docker контейнером (если запущено в Docker)")
print("4. Блокировка Yandex SMTP сервера")
print()
sys.exit(1)
