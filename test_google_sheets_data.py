#!/usr/bin/env python3
"""
Тесты для проверки правильности данных из Google Sheets
Запуск: python3 test_google_sheets_data.py
"""

import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google_sheets_helper import get_services, get_masters

def test_all_services_loaded():
    """Тест: проверяем, что все услуги загружены из Google Sheets"""
    print("\n" + "="*60)
    print("ТЕСТ 1: Проверка загрузки всех услуг")
    print("="*60)
    
    services = get_services()
    
    assert len(services) > 0, "❌ Не найдено ни одной услуги!"
    print(f"✅ Найдено услуг: {len(services)}")
    
    # Проверяем, что есть услуги обоих типов
    men_services = [s for s in services if s.get('type') == 'men']
    women_services = [s for s in services if s.get('type') == 'women']
    
    assert len(men_services) > 0, "❌ Не найдено услуг для мужского зала!"
    assert len(women_services) > 0, "❌ Не найдено услуг для женского зала!"
    
    print(f"✅ Мужской зал: {len(men_services)} услуг")
    print(f"✅ Женский зал: {len(women_services)} услуг")
    
    return services

def test_specific_service_briтье_головы():
    """Тест: проверяем конкретно услугу 'Бритье головы'"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Проверка услуги 'Бритье головы'")
    print("="*60)
    
    services = get_services()
    
    # Ищем услугу "Бритье головы"
    briтье_услуги = [
        s for s in services 
        if "бритье" in s.get('title', '').lower() 
        and "голов" in s.get('title', '').lower()
    ]
    
    assert len(briтье_услуги) > 0, "❌ Услуга 'Бритье головы' не найдена!"
    
    service = briтье_услуги[0]
    
    print(f"✅ Найдена услуга: '{service.get('title')}'")
    print(f"   Строка в таблице: {service.get('row_number')}")
    print(f"   Цена (строка): '{service.get('price_str')}'")
    print(f"   Цена (число): {service.get('price')}₽")
    print(f"   Длительность: {service.get('duration')} минут")
    print(f"   Мастер: {service.get('master')}")
    print(f"   Тип: {service.get('type')}")
    
    # КРИТИЧЕСКИЕ ПРОВЕРКИ
    assert service.get('price') == 1700, f"❌ НЕПРАВИЛЬНАЯ ЦЕНА! Ожидается 1700₽, получено {service.get('price')}₽"
    assert service.get('price_str') == "1700" or "1700" in service.get('price_str', ''), f"❌ НЕПРАВИЛЬНАЯ ЦЕНА (строка)! Ожидается '1700', получено '{service.get('price_str')}'"
    assert service.get('duration') == 60, f"❌ НЕПРАВИЛЬНАЯ ДЛИТЕЛЬНОСТЬ! Ожидается 60 минут, получено {service.get('duration')} минут"
    assert "роман" in service.get('master', '').lower(), f"❌ НЕПРАВИЛЬНЫЙ МАСТЕР! Ожидается 'Роман', получено '{service.get('master')}'"
    assert service.get('type') == 'men', f"❌ НЕПРАВИЛЬНЫЙ ТИП! Ожидается 'men', получено '{service.get('type')}'"
    
    print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ: цена 1700₽, длительность 60 мин, мастер Роман")
    
    return service

def test_all_expected_services():
    """Тест: проверяем наличие всех ожидаемых услуг"""
    print("\n" + "="*60)
    print("ТЕСТ 3: Проверка наличия всех ожидаемых услуг")
    print("="*60)
    
    services = get_services()
    service_titles = [s.get('title', '').lower() for s in services]
    
    # Список ожидаемых услуг (из сообщения пользователя)
    expected_services = [
        "бритье головы",
        "бритье лица",
        "восковая эпиляция",
        "детская стрижка",
        "окантовка",
        "мужская стрижка+ оформление бороды",
        "стрижка муская",
        "стрижка мужская \"площадка\"",
        "стрижка \"наголо\"",
        "стрижка \"машинкой\"",
        "тонирование головы",
        "топ стрижка детская",
        "уход за лицом",
        "камуфляж седины",
        "стрижка (мытьё + сушка)",
        "стрижка с укладкой",
        "стрижка детская",
        "стрижка чёлки",
        "сушка феном с приданием формы",
        "укладка",
        "свадебная / вечерняя укладка",
        "окрашивание простое",
        "окрашивание корней",
        "ламинирование ресниц",
        "эпиляция (одна зона)",
    ]
    
    missing_services = []
    for expected in expected_services:
        found = False
        for title in service_titles:
            # Проверяем частичное совпадение (учитываем возможные различия в регистре и кавычках)
            expected_clean = expected.lower().replace('"', '').replace('«', '').replace('»', '')
            title_clean = title.lower().replace('"', '').replace('«', '').replace('»', '')
            
            if expected_clean in title_clean or title_clean in expected_clean:
                found = True
                break
        
        if not found:
            missing_services.append(expected)
    
    if missing_services:
        print(f"⚠️ Не найдено услуг: {len(missing_services)}")
        for missing in missing_services:
            print(f"   - {missing}")
    else:
        print(f"✅ Все {len(expected_services)} ожидаемых услуг найдены!")
    
    return len(missing_services) == 0

def test_service_prices():
    """Тест: проверяем правильность цен для ключевых услуг"""
    print("\n" + "="*60)
    print("ТЕСТ 4: Проверка цен ключевых услуг")
    print("="*60)
    
    services = get_services()
    
    # Ожидаемые цены (из сообщения пользователя)
    expected_prices = {
        "бритье головы": 1700,
        "бритье лица": 1500,
        "восковая эпиляция": 500,
        "детская стрижка": 1200,
        "окантовка": 500,
        "мужская стрижка+ оформление бороды": 2500,
        "стрижка муская": 1500,
        "стрижка мужская \"площадка\"": 1500,
        "стрижка \"наголо\"": 500,
        "стрижка \"машинкой\"": 1000,
        "тонирование головы": 1800,
        "топ стрижка детская": 1200,
        "уход за лицом": 1200,
        "камуфляж седины": 1400,
        "эпиляция (одна зона)": 200,
    }
    
    errors = []
    for service in services:
        title_lower = service.get('title', '').lower()
        for expected_title, expected_price in expected_prices.items():
            expected_clean = expected_title.lower().replace('"', '').replace('«', '').replace('»', '')
            title_clean = title_lower.replace('"', '').replace('«', '').replace('»', '')
            
            if expected_clean in title_clean or title_clean in expected_clean:
                actual_price = service.get('price', 0)
                if actual_price != expected_price:
                    errors.append({
                        'title': service.get('title'),
                        'expected': expected_price,
                        'actual': actual_price,
                        'price_str': service.get('price_str')
                    })
                else:
                    print(f"✅ {service.get('title')}: {actual_price}₽ (ожидалось {expected_price}₽)")
                break
    
    if errors:
        print(f"\n❌ НАЙДЕНО ОШИБОК В ЦЕНАХ: {len(errors)}")
        for error in errors:
            print(f"   ❌ {error['title']}: получено {error['actual']}₽, ожидалось {error['expected']}₽ (строка: '{error['price_str']}')")
        return False
    else:
        print(f"\n✅ Все проверенные цены правильные!")
        return True

def test_masters():
    """Тест: проверяем наличие мастеров"""
    print("\n" + "="*60)
    print("ТЕСТ 5: Проверка мастеров")
    print("="*60)
    
    masters = get_masters()
    
    assert len(masters) > 0, "❌ Не найдено ни одного мастера!"
    
    master_names = [m.get('name', '').lower() for m in masters]
    
    assert 'роман' in master_names, "❌ Мастер 'Роман' не найден!"
    assert 'анжела' in master_names, "❌ Мастер 'Анжела' не найден!"
    
    print(f"✅ Найдено мастеров: {len(masters)}")
    for master in masters:
        print(f"   - {master.get('name')} ({master.get('specialization')})")
    
    return True

def main():
    """Запуск всех тестов"""
    print("\n" + "="*60)
    print("ЗАПУСК ТЕСТОВ ПРАВИЛЬНОСТИ ДАННЫХ ИЗ GOOGLE SHEETS")
    print("="*60)
    
    try:
        # Тест 1: Загрузка всех услуг
        services = test_all_services_loaded()
        
        # Тест 2: Конкретная услуга "Бритье головы"
        test_specific_service_briтье_головы()
        
        # Тест 3: Все ожидаемые услуги
        test_all_expected_services()
        
        # Тест 4: Правильность цен
        test_service_prices()
        
        # Тест 5: Мастера
        test_masters()
        
        print("\n" + "="*60)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("="*60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ ТЕСТ ПРОВАЛЕН: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТАХ: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

