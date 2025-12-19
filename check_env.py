#!/usr/bin/env python3
"""
Скрипт для проверки переменных окружения для email
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

print("=" * 70)
print("🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ДЛЯ EMAIL")
print("=" * 70)
print()

# Проверяем переменные
YANDEX_EMAIL = os.getenv("YANDEX_EMAIL")
YANDEX_PASSWORD = os.getenv("YANDEX_IMAP_PASSWORD") or os.getenv("YANDEX_PASSWORD")
YANDEX_IMAP_PASSWORD = os.getenv("YANDEX_IMAP_PASSWORD")
YANDEX_PASSWORD_OLD = os.getenv("YANDEX_PASSWORD")
YANDEX_SMTP_SERVER = os.getenv("YANDEX_SMTP_SERVER", "smtp.yandex.ru")
YANDEX_SMTP_PORT = int(os.getenv("YANDEX_SMTP_PORT", 465))

print(f"YANDEX_EMAIL: {YANDEX_EMAIL or '❌ НЕ УСТАНОВЛЕН'}")
print(f"YANDEX_IMAP_PASSWORD: {'✅ УСТАНОВЛЕН' if YANDEX_IMAP_PASSWORD else '❌ НЕ УСТАНОВЛЕН'} ({len(YANDEX_IMAP_PASSWORD) if YANDEX_IMAP_PASSWORD else 0} символов)")
print(f"YANDEX_PASSWORD: {'✅ УСТАНОВЛЕН' if YANDEX_PASSWORD_OLD else '❌ НЕ УСТАНОВЛЕН'} ({len(YANDEX_PASSWORD_OLD) if YANDEX_PASSWORD_OLD else 0} символов)")
print(f"Используемый пароль: {'YANDEX_IMAP_PASSWORD' if YANDEX_IMAP_PASSWORD else 'YANDEX_PASSWORD' if YANDEX_PASSWORD_OLD else 'НЕТ'}")
print(f"YANDEX_SMTP_SERVER: {YANDEX_SMTP_SERVER}")
print(f"YANDEX_SMTP_PORT: {YANDEX_SMTP_PORT}")
print()

if YANDEX_EMAIL and YANDEX_PASSWORD:
    print("✅ Все необходимые переменные установлены!")
    print(f"   Email: {YANDEX_EMAIL}")
    print(f"   Пароль: {'*' * len(YANDEX_PASSWORD)} ({len(YANDEX_PASSWORD)} символов)")
else:
    print("❌ ОШИБКА: Не все переменные установлены!")
    if not YANDEX_EMAIL:
        print("   - YANDEX_EMAIL не установлен")
    if not YANDEX_PASSWORD:
        print("   - YANDEX_IMAP_PASSWORD или YANDEX_PASSWORD не установлен")
    print()
    print("Для Railway добавьте в Variables:")
    print("   YANDEX_EMAIL=a-novoselova07@yandex.ru")
    print("   YANDEX_IMAP_PASSWORD=nyyiyzaithgesuzx")

print()
print("=" * 70)
