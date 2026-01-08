"""
Тест LangGraph RAG для точного извлечения цен
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def test_pricing_query():
    """Тест запроса о ценах"""
    from services.rag.rag_langgraph import query_with_langgraph
    
    # Список услуг для тестирования
    test_queries = [
        "Сколько стоит автоматизация HR-процессов?",
        "Какова цена стратегической сессии?",
        "Цена на HR-сопровождение компании",
        "Стоимость оптимизации оргструктуры",
        "Сколько стоит коучинг руководителей?",
    ]
    
    print("\n" + "="*70)
    print("ТЕСТ LANGGRAPH RAG - ТОЧНОЕ ИЗВЛЕЧЕНИЕ ЦЕН")
    print("="*70 + "\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'─'*70}")
        print(f"Запрос {i}/{len(test_queries)}: {query}")
        print('─'*70)
        
        try:
            result = await query_with_langgraph(query, thread_id=f"test_{i}")
            
            print(f"\n✅ ОТВЕТ:\n{result['answer']}\n")
            print(f"📊 МЕТАДАННЫЕ:")
            print(f"  - Тип запроса: {result['query_type']}")
            print(f"  - Валидация: {'✅ Прошла' if result['validated'] else '❌ Не прошла'}")
            print(f"  - Попыток: {result['retry_count']}")
            print(f"  - Найдено услуг: {len(result['sources'])}")
            
            if result['sources']:
                print(f"\n📋 НАЙДЕННЫЕ УСЛУГИ:")
                for j, source in enumerate(result['sources'][:5], 1):
                    print(f"  {j}. {source}")
            
            if result['validation_errors']:
                print(f"\n⚠️ ОШИБКИ ВАЛИДАЦИИ:")
                for error in result['validation_errors']:
                    print(f"  - {error}")
            
            pricing_info = result.get('pricing_info', {})
            if pricing_info.get('services'):
                print(f"\n💰 ТОЧНЫЕ ЦЕНЫ ИЗ БАЗЫ:")
                for service in pricing_info['services'][:3]:
                    print(f"  - {service['title']}: {service['price']}")
            
        except Exception as e:
            print(f"\n❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*70}")
    print("ТЕСТ ЗАВЕРШЕН")
    print('='*70 + "\n")


async def test_general_query():
    """Тест общего запроса (не о ценах)"""
    from services.rag.rag_langgraph import query_with_langgraph
    
    print("\n" + "="*70)
    print("ТЕСТ ОБЩЕГО ЗАПРОСА (НЕ О ЦЕНАХ)")
    print("="*70 + "\n")
    
    query = "Что такое HR консалтинг?"
    print(f"Запрос: {query}\n")
    
    try:
        result = await query_with_langgraph(query, thread_id="test_general")
        
        print(f"\n✅ ОТВЕТ:\n{result['answer']}\n")
        print(f"📊 МЕТАДАННЫЕ:")
        print(f"  - Тип запроса: {result['query_type']}")
        print(f"  - Найдено результатов: {len(result['sources'])}")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


async def test_comparison():
    """Сравнение LangGraph RAG со стандартным RAG"""
    print("\n" + "="*70)
    print("СРАВНЕНИЕ LANGGRAPH RAG И СТАНДАРТНОГО RAG")
    print("="*70 + "\n")
    
    query = "Сколько стоит стратегическая сессия?"
    
    # Тест LangGraph RAG
    print("1. LANGGRAPH RAG:\n")
    try:
        from services.rag.rag_langgraph import query_with_langgraph
        result_lg = await query_with_langgraph(query, thread_id="test_compare_lg")
        print(f"   Ответ: {result_lg['answer'][:200]}...")
        print(f"   Валидация: {'✅' if result_lg['validated'] else '❌'}")
        print(f"   Услуг: {len(result_lg['sources'])}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Тест стандартного RAG
    print("\n2. СТАНДАРТНЫЙ RAG:\n")
    try:
        from services.rag.qdrant_helper import search_service
        results = search_service(query, limit=5)
        if results:
            print(f"   Найдено: {len(results)} результатов")
            for i, r in enumerate(results[:3], 1):
                title = r.get('title', '')
                price = r.get('price_str', '') or r.get('price', '')
                print(f"   {i}. {title}: {price}")
        else:
            print("   Результатов не найдено")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    print("\n🚀 ЗАПУСК ТЕСТОВ LANGGRAPH RAG\n")
    
    # Запускаем тесты
    asyncio.run(test_pricing_query())
    asyncio.run(test_general_query())
    asyncio.run(test_comparison())
    
    print("\n✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ\n")
