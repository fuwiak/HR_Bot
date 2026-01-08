"""
Тест для проверки точной цены Форсайт-сессии: от 90 000 рублей
Доказывает, что RAG правильно извлекает цены из базы данных
"""
import asyncio
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Ожидаемая цена для Форсайт-сессии
EXPECTED_SERVICE = "Форсайт - сессия"
EXPECTED_PRICE = "от 90 000 рублей"
EXPECTED_PRICE_VARIANTS = [
    "от 90 000 рублей",
    "от 90000 рублей",
    "от 90 000 руб",
    "90000",
    "90 000"
]


async def test_forsight_price_exact():
    """
    Тест 1: Проверка точной цены через LangGraph RAG
    """
    print("\n" + "="*70)
    print("ТЕСТ 1: ПРОВЕРКА ТОЧНОЙ ЦЕНЫ ФОРСАЙТ-СЕССИИ ЧЕРЕЗ LANGGRAPH RAG")
    print("="*70 + "\n")
    
    from services.rag.rag_langgraph import query_with_langgraph
    
    test_queries = [
        "Форсайт - сессия. - какая цена",
        "Сколько стоит форсайт сессия?",
        "Цена форсайт-сессии",
        "Форсайт сессия стоимость"
    ]
    
    all_passed = True
    
    for query in test_queries:
        print(f"\n🔍 Запрос: {query}")
        print("-" * 70)
        
        try:
            result = await query_with_langgraph(query, thread_id="test_forsight")
            
            answer = result.get("answer", "")
            pricing_info = result.get("pricing_info", {})
            services = pricing_info.get("services", [])
            
            # Проверяем, что найдена услуга
            found_service = None
            for service in services:
                title_lower = service.get("title", "").lower()
                if "форсайт" in title_lower and "сессия" in title_lower:
                    found_service = service
                    break
            
            if not found_service:
                # Ищем в ответе
                if "форсайт" in answer.lower() and "сессия" in answer.lower():
                    print(f"✅ Услуга найдена в ответе")
                    # Проверяем цену в ответе
                    price_found = False
                    for variant in EXPECTED_PRICE_VARIANTS:
                        if variant.lower() in answer.lower():
                            print(f"✅ Цена найдена в ответе: {variant}")
                            price_found = True
                            break
                    
                    if not price_found:
                        print(f"❌ Цена не найдена в ответе!")
                        print(f"   Ожидалось: {EXPECTED_PRICE}")
                        print(f"   Ответ: {answer[:200]}...")
                        all_passed = False
                else:
                    print(f"❌ Услуга не найдена!")
                    all_passed = False
            else:
                print(f"✅ Услуга найдена: {found_service.get('title')}")
                price = found_service.get("price", "")
                print(f"   Цена из базы: {price}")
                
                # Проверяем соответствие цены
                price_match = False
                for variant in EXPECTED_PRICE_VARIANTS:
                    if variant.lower() in price.lower() or "90000" in price.replace(" ", ""):
                        price_match = True
                        print(f"✅ Цена соответствует ожидаемой!")
                        break
                
                if not price_match:
                    print(f"❌ Цена не соответствует!")
                    print(f"   Ожидалось: {EXPECTED_PRICE}")
                    print(f"   Получено: {price}")
                    all_passed = False
            
            # Проверяем валидацию
            validated = result.get("validated", False)
            if validated:
                print(f"✅ Валидация прошла успешно")
            else:
                print(f"⚠️ Валидация не прошла")
                errors = result.get("validation_errors", [])
                if errors:
                    print(f"   Ошибки: {errors}")
            
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    print(f"\n{'='*70}")
    if all_passed:
        print("✅ ТЕСТ 1 ПРОЙДЕН: Все запросы вернули правильную цену")
    else:
        print("❌ ТЕСТ 1 НЕ ПРОЙДЕН: Некоторые запросы не вернули правильную цену")
    print('='*70 + "\n")
    
    return all_passed


async def test_forsight_price_direct_search():
    """
    Тест 2: Прямой поиск услуги в Qdrant
    """
    print("\n" + "="*70)
    print("ТЕСТ 2: ПРЯМОЙ ПОИСК УСЛУГИ В QDRANT")
    print("="*70 + "\n")
    
    from services.rag.qdrant_helper import search_service
    
    test_queries = [
        "Форсайт - сессия",
        "Форсайт сессия",
        "форсайт"
    ]
    
    all_passed = True
    
    for query in test_queries:
        print(f"\n🔍 Запрос: {query}")
        print("-" * 70)
        
        try:
            results = search_service(query, limit=10)
            
            if not results:
                print(f"❌ Результаты не найдены")
                all_passed = False
                continue
            
            print(f"✅ Найдено результатов: {len(results)}")
            
            # Ищем Форсайт-сессию
            found = False
            for result in results:
                title = result.get("title", "")
                price_str = result.get("price_str", "")
                price = result.get("price", 0)
                
                if "форсайт" in title.lower() and "сессия" in title.lower():
                    found = True
                    print(f"✅ Найдена услуга: {title}")
                    print(f"   Цена (price_str): {price_str}")
                    print(f"   Цена (price): {price}")
                    
                    # Проверяем цену
                    if price_str:
                        price_match = any(variant.lower() in price_str.lower() for variant in EXPECTED_PRICE_VARIANTS)
                        if price_match or "90000" in price_str.replace(" ", ""):
                            print(f"✅ Цена соответствует: {price_str}")
                        else:
                            print(f"❌ Цена не соответствует!")
                            print(f"   Ожидалось: {EXPECTED_PRICE}")
                            print(f"   Получено: {price_str}")
                            all_passed = False
                    elif price > 0:
                        if price == 90000:
                            print(f"✅ Цена соответствует: {price}")
                        else:
                            print(f"❌ Цена не соответствует!")
                            print(f"   Ожидалось: 90000")
                            print(f"   Получено: {price}")
                            all_passed = False
                    else:
                        print(f"❌ Цена не найдена!")
                        all_passed = False
                    break
            
            if not found:
                print(f"⚠️ Форсайт-сессия не найдена в результатах")
                print(f"   Найденные услуги:")
                for i, r in enumerate(results[:5], 1):
                    print(f"   {i}. {r.get('title', 'Без названия')} - {r.get('price_str', 'нет цены')}")
                all_passed = False
                
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    print(f"\n{'='*70}")
    if all_passed:
        print("✅ ТЕСТ 2 ПРОЙДЕН: Прямой поиск находит правильную цену")
    else:
        print("❌ ТЕСТ 2 НЕ ПРОЙДЕН: Прямой поиск не находит правильную цену")
    print('='*70 + "\n")
    
    return all_passed


async def test_forsight_price_in_database():
    """
    Тест 3: Проверка, что услуга есть в базе данных с правильной ценой
    """
    print("\n" + "="*70)
    print("ТЕСТ 3: ПРОВЕРКА НАЛИЧИЯ УСЛУГИ В БАЗЕ ДАННЫХ")
    print("="*70 + "\n")
    
    from services.rag.qdrant_helper import get_qdrant_client
    
    client = get_qdrant_client()
    if not client:
        print("❌ Qdrant не подключен")
        return False
    
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        # Ищем все услуги с "форсайт" в названии
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="source_type",
                    match=MatchValue(value="service")
                )
            ]
        )
        
        # Получаем все точки с фильтром
        scroll_result = client.scroll(
            collection_name="hr2137_bot_knowledge_base",
            scroll_filter=filter_condition,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        points = scroll_result[0] if isinstance(scroll_result, tuple) else []
        
        print(f"📊 Всего услуг в базе: {len(points)}")
        
        # Ищем Форсайт-сессию
        found_services = []
        for point in points:
            payload = point.payload if hasattr(point, 'payload') else {}
            title = payload.get("title", "")
            
            if "форсайт" in title.lower() and "сессия" in title.lower():
                found_services.append({
                    "title": title,
                    "price_str": payload.get("price_str", ""),
                    "price": payload.get("price", 0),
                    "id": payload.get("id", 0)
                })
        
        if not found_services:
            print(f"❌ Форсайт-сессия не найдена в базе данных!")
            print(f"\n   Похожие услуги:")
            for point in points[:20]:
                payload = point.payload if hasattr(point, 'payload') else {}
                title = payload.get("title", "")
                if "сессия" in title.lower():
                    print(f"   - {title}: {payload.get('price_str', 'нет цены')}")
            return False
        
        print(f"✅ Найдено услуг с 'форсайт' и 'сессия': {len(found_services)}")
        
        all_passed = True
        for service in found_services:
            print(f"\n   Услуга: {service['title']}")
            print(f"   Цена (price_str): {service['price_str']}")
            print(f"   Цена (price): {service['price']}")
            
            # Проверяем цену
            price_match = False
            if service['price_str']:
                for variant in EXPECTED_PRICE_VARIANTS:
                    if variant.lower() in service['price_str'].lower() or "90000" in service['price_str'].replace(" ", ""):
                        price_match = True
                        print(f"   ✅ Цена соответствует ожидаемой!")
                        break
            elif service['price'] == 90000:
                price_match = True
                print(f"   ✅ Цена соответствует ожидаемой!")
            
            if not price_match:
                print(f"   ❌ Цена не соответствует!")
                print(f"      Ожидалось: {EXPECTED_PRICE}")
                all_passed = False
        
        print(f"\n{'='*70}")
        if all_passed:
            print("✅ ТЕСТ 3 ПРОЙДЕН: Услуга есть в базе с правильной ценой")
        else:
            print("❌ ТЕСТ 3 НЕ ПРОЙДЕН: Услуга есть, но цена неправильная")
        print('='*70 + "\n")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """
    Запуск всех тестов
    """
    print("\n" + "="*70)
    print("ТЕСТИРОВАНИЕ ЦЕНЫ ФОРСАЙТ-СЕССИИ")
    print(f"Ожидаемая услуга: {EXPECTED_SERVICE}")
    print(f"Ожидаемая цена: {EXPECTED_PRICE}")
    print("="*70 + "\n")
    
    results = []
    
    # Тест 1: LangGraph RAG
    result1 = await test_forsight_price_exact()
    results.append(("LangGraph RAG", result1))
    
    # Тест 2: Прямой поиск
    result2 = await test_forsight_price_direct_search()
    results.append(("Прямой поиск в Qdrant", result2))
    
    # Тест 3: Проверка базы данных
    result3 = await test_forsight_price_in_database()
    results.append(("Проверка базы данных", result3))
    
    # Итоговый отчет
    print("\n" + "="*70)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("="*70 + "\n")
    
    for test_name, passed in results:
        status = "✅ ПРОЙДЕН" if passed else "❌ НЕ ПРОЙДЕН"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    print(f"\n{'='*70}")
    if all_passed:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print(f"✅ Цена '{EXPECTED_PRICE}' для '{EXPECTED_SERVICE}' подтверждена!")
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        print("⚠️ Требуется проверка индексации услуг в Qdrant")
    print('='*70 + "\n")
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
