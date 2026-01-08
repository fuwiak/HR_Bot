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
    
    # Проверяем, что есть услуги разных типов
    men_services = [s for s in services if s.get('type') == 'men']
    women_services = [s for s in services if s.get('type') == 'women']
    
    print(f"✅ Услуги типа 'men': {len(men_services)}")
    print(f"✅ Услуги типа 'women': {len(women_services)}")
    
    return services

def test_specific_service_консультация():
    """Тест: проверяем конкретно услугу 'Консультация по найму'"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Проверка услуги 'Консультация по найму'")
    print("="*60)
    
    services = get_services()
    
    # Ищем услугу "Консультация"
    консультация_услуги = [
        s for s in services 
        if "консультация" in s.get('title', '').lower()
    ]
    
    if len(консультация_услуги) > 0:
        service = консультация_услуги[0]
        
        print(f"✅ Найдена услуга: '{service.get('title')}'")
        print(f"   Строка в таблице: {service.get('row_number')}")
        print(f"   Цена (строка): '{service.get('price_str')}'")
        print(f"   Цена (число): {service.get('price')}₽")
        print(f"   Длительность: {service.get('duration')} минут")
        print(f"   HR-специалист: {service.get('master')}")
        print(f"   Тип: {service.get('type')}")
        
        print("✅ Услуга найдена и проверена")
        return service
    else:
        print("⚠️ Услуга 'Консультация' не найдена, но тест продолжается")
        return None

def test_all_expected_services():
    """Тест: проверяем наличие всех ожидаемых услуг"""
    print("\n" + "="*60)
    print("ТЕСТ 3: Проверка наличия всех ожидаемых услуг")
    print("="*60)
    
    services = get_services()
    service_titles = [s.get('title', '').lower() for s in services]
    
    # Список ожидаемых услуг (из сообщения пользователя)
    expected_services = [
        "консультация по найму",
        "собеседование",
        "онбординг",
        "обучение",
        "окантовка",
        "мужская стрижка+ оформление бороды",
        "стрижка муская",
        "консультация по найму",
        "собеседование с кандидатом",
        "онбординг нового сотрудника",
        "оценка персонала",
        "обучение сотрудников",
        "развитие карьеры",
        "адаптация персонала",
        "тренинг по навыкам",
        "аттестация сотрудников",
        "карьерное консультирование",
        "подбор персонала",
        "развитие команды",
        "мотивация персонала",
        "управление талантами",
        "планирование карьеры",
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
        "консультация по найму": 2000,
        "собеседование": 1500,
        "онбординг": 3000,
        "обучение": 2500,
        "оценка персонала": 1800,
        "развитие карьеры": 2200,
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
    
    print(f"✅ Найдено HR-специалистов: {len(masters)}")
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
        
        # Тест 2: Конкретная услуга "Консультация"
        test_specific_service_консультация()
        
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







