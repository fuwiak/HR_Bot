#!/usr/bin/env python3
"""
Скрипт для проверки переменных окружения Qdrant в Railway
Запустите этот скрипт в контейнере для диагностики проблем с подключением к Qdrant
"""
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def check_env_variables():
    """Проверка переменных окружения для Qdrant"""
    print("=" * 80)
    print("🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ QDRANT")
    print("=" * 80)
    print()
    
    # Список переменных для проверки
    env_vars = {
        "RAILWAY_SERVICE_QDRANT_URL": "Автоматическая переменная Railway (приоритет 1)",
        "QDRANT_HOST": "Ручная настройка публичного/приватного домена (приоритет 2)",
        "QDRANT_PORT": "Порт Qdrant (по умолчанию 6333)",
        "QDRANT_URL": "Старый способ настройки (приоритет 4)",
        "QDRANT_API_KEY": "API ключ для аутентификации (опционально)",
        "RAILWAY_ENVIRONMENT": "Индикатор что мы в Railway",
        "RAILWAY_PROJECT_ID": "ID проекта Railway",
    }
    
    print("📋 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ:")
    print("-" * 80)
    
    found_vars = {}
    for var_name, description in env_vars.items():
        value = os.getenv(var_name)
        if value:
            # Скрываем чувствительные данные
            if "KEY" in var_name or "PASSWORD" in var_name:
                display_value = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"✅ {var_name:30} = {display_value}")
            print(f"   {description}")
            found_vars[var_name] = value
        else:
            print(f"❌ {var_name:30} = (не установлена)")
            print(f"   {description}")
        print()
    
    # Определяем какой URL будет использован
    print("=" * 80)
    print("🔧 ОПРЕДЕЛЕНИЕ URL QDRANT (по приоритету):")
    print("-" * 80)
    
    railway_service_qdrant_url = os.getenv("RAILWAY_SERVICE_QDRANT_URL")
    qdrant_host = os.getenv("QDRANT_HOST")
    qdrant_port = os.getenv("QDRANT_PORT", "6333")
    qdrant_url = os.getenv("QDRANT_URL")
    railway_env = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID")
    
    final_url = None
    priority = None
    
    # Приоритет 1: RAILWAY_SERVICE_QDRANT_URL
    if railway_service_qdrant_url:
        if railway_service_qdrant_url.startswith("https://"):
            final_url = railway_service_qdrant_url
        else:
            final_url = f"https://{railway_service_qdrant_url}"
        priority = "1. RAILWAY_SERVICE_QDRANT_URL (автоматическая переменная Railway)"
        print(f"✅ Используется: {priority}")
        print(f"   URL: {final_url}")
    
    # Приоритет 2: QDRANT_HOST
    elif qdrant_host:
        is_public_domain = (
            ".up.railway.app" in qdrant_host or
            ".railway.app" in qdrant_host or
            qdrant_host.startswith("https://")
        )
        
        if is_public_domain:
            if qdrant_host.startswith("https://"):
                final_url = qdrant_host
            elif qdrant_host.startswith("http://"):
                final_url = qdrant_host.replace("http://", "https://")
            else:
                final_url = f"https://{qdrant_host}"
            priority = "2. QDRANT_HOST (публичный домен Railway)"
        else:
            final_url = f"http://{qdrant_host}:{qdrant_port}"
            priority = "2. QDRANT_HOST (приватный домен Railway)"
        print(f"✅ Используется: {priority}")
        print(f"   URL: {final_url}")
    
    # Приоритет 3: Private domain в Railway
    elif railway_env:
        final_url = f"http://qdrant.railway.internal:{qdrant_port}"
        priority = "3. Private domain Railway (qdrant.railway.internal)"
        print(f"⚠️  Используется: {priority}")
        print(f"   URL: {final_url}")
        print(f"   ⚠️  QDRANT_HOST не установлен, используется fallback")
    
    # Приоритет 4: QDRANT_URL или localhost
    else:
        if qdrant_url:
            final_url = qdrant_url
            priority = "4. QDRANT_URL (старый способ)"
        else:
            final_url = "http://localhost:6333"
            priority = "4. Localhost (локальная разработка)"
        print(f"⚠️  Используется: {priority}")
        print(f"   URL: {final_url}")
    
    print()
    print("=" * 80)
    print("📊 ИТОГОВАЯ КОНФИГУРАЦИЯ:")
    print("-" * 80)
    print(f"Используемый URL: {final_url}")
    print(f"Приоритет: {priority}")
    print()
    
    # Проверка доступности
    print("=" * 80)
    print("🔗 ПРОВЕРКА ДОСТУПНОСТИ QDRANT:")
    print("-" * 80)
    
    try:
        import httpx
        health_url = final_url.rstrip('/') + '/health'
        print(f"Проверка: {health_url}")
        try:
            response = httpx.get(health_url, timeout=5.0, follow_redirects=True)
            if response.status_code == 200:
                print(f"✅ Qdrant доступен (HTTP {response.status_code})")
                print(f"   Ответ: {response.text[:100]}")
            else:
                print(f"⚠️  Qdrant отвечает, но статус: {response.status_code}")
                print(f"   Ответ: {response.text[:200]}")
        except httpx.TimeoutException:
            print(f"❌ Таймаут при подключении к {health_url}")
            print(f"   Проверьте что Qdrant сервис запущен в Railway")
        except httpx.ConnectError as e:
            print(f"❌ Ошибка подключения: {e}")
            print(f"   Проверьте URL и что Qdrant сервис доступен")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    except ImportError:
        print("⚠️  httpx не установлен, пропускаем проверку доступности")
        print("   Установите: pip install httpx")
    
    print()
    print("=" * 80)
    print("💡 РЕКОМЕНДАЦИИ:")
    print("-" * 80)
    
    if not railway_service_qdrant_url and not qdrant_host:
        print("❌ ПРОБЛЕМА: Не установлены переменные для подключения к Qdrant")
        print()
        print("РЕШЕНИЕ:")
        print("1. Убедитесь что Qdrant сервис добавлен в проект Railway")
        print("2. Убедитесь что Qdrant сервис находится в том же проекте")
        print("3. Добавьте переменную QDRANT_HOST в Railway Dashboard:")
        print("   - Для публичного домена: QDRANT_HOST=https://qdrant-production-XXXX.up.railway.app")
        print("   - Для приватного домена: QDRANT_HOST=qdrant.railway.internal")
        print("   - И установите: QDRANT_PORT=6333")
    elif not railway_service_qdrant_url:
        print("⚠️  RAILWAY_SERVICE_QDRANT_URL не установлена (но QDRANT_HOST есть)")
        print("   Это нормально, если используется ручная настройка через QDRANT_HOST")
    else:
        print("✅ Переменные окружения настроены правильно")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    check_env_variables()
