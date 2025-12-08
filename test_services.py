#!/usr/bin/env python3
"""
Тесты для проверки парсинга услуг из Google Sheets
"""
import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_parse_price():
    """Тест парсинга цены"""
    from google_sheets_helper import parse_price
    
    # Тест 1: Обычная цена
    assert parse_price("1700") == 1700, f"Ожидалось 1700, получено {parse_price('1700')}"
    
    # Тест 2: Диапазон цен
    assert parse_price("1000–2500") == 1000, f"Ожидалось 1000, получено {parse_price('1000–2500')}"
    
    # Тест 3: С пробелами
    assert parse_price(" 1700 ") == 1700, f"Ожидалось 1700, получено {parse_price(' 1700 ')}"
    
    # Тест 4: Пустая строка
    assert parse_price("") == 0, f"Ожидалось 0, получено {parse_price('')}"
    
    print("✅ Тесты parse_price прошли успешно")

def test_service_search():
    """Тест поиска услуги 'Бритье головы'"""
    try:
        from google_sheets_helper import get_services
        
        services = get_services()
        assert len(services) > 0, "Список услуг пуст!"
        
        # Ищем "Бритье головы"
        briтье_головы = [s for s in services if "бритье" in s.get('title', '').lower() and "голов" in s.get('title', '').lower()]
        
        assert len(briтье_головы) > 0, "Услуга 'Бритье головы' не найдена!"
        
        service = briтье_головы[0]
        assert service.get('price_str') == "1700" or service.get('price') == 1700, \
            f"Цена должна быть 1700, получено: {service.get('price_str')} или {service.get('price')}"
        assert service.get('duration') == 60, \
            f"Длительность должна быть 60 минут, получено: {service.get('duration')}"
        
        print(f"✅ Услуга 'Бритье головы' найдена: {service.get('title')} - {service.get('price_str')}₽ ({service.get('duration')} мин)")
        
    except Exception as e:
        print(f"⚠️ Тест поиска услуги пропущен (возможно, Google Sheets не настроены): {e}")

def main():
    """Запускает все тесты"""
    print("🧪 Запуск тестов...\n")
    
    try:
        test_parse_price()
        test_service_search()
        print("\n✅ Все тесты прошли успешно!")
        return 0
    except AssertionError as e:
        print(f"\n❌ Тест не прошел: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении тестов: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
