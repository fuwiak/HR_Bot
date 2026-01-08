"""
Тест Yandex Disk Indexer
Проверяет работу индексатора без реального запуска в фоне
"""
import asyncio
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

async def test_yandex_disk_connection():
    """Тест подключения к Яндекс.Диску"""
    print("🔍 Тест 1: Подключение к Яндекс.Диску")
    print("-" * 60)
    
    from yandex_disk_helper import get_disk_info
    
    info = await get_disk_info()
    
    if info:
        print("✅ Подключение успешно!")
        print(f"   Всего места: {info.get('total_space', 0) / (1024**3):.1f} ГБ")
        print(f"   Занято: {info.get('used_space', 0) / (1024**3):.1f} ГБ")
        return True
    else:
        print("❌ Ошибка подключения")
        return False

async def test_list_files():
    """Тест получения списка файлов"""
    print("\n🔍 Тест 2: Получение списка файлов")
    print("-" * 60)
    
    from yandex_disk_helper import list_files
    
    result = await list_files(path="/", limit=10)
    
    if result:
        items = result.get("_embedded", {}).get("items", [])
        print(f"✅ Найдено файлов: {len(items)}")
        
        for i, item in enumerate(items[:5], 1):
            name = item.get("name", "")
            item_type = item.get("type", "")
            size = item.get("size", 0)
            
            type_emoji = "📁" if item_type == "dir" else "📄"
            size_mb = size / (1024**2) if size else 0
            
            print(f"   {i}. {type_emoji} {name} ({size_mb:.2f} МБ)")
        
        return True
    else:
        print("❌ Ошибка получения файлов")
        return False

async def test_qdrant_connection():
    """Тест подключения к Qdrant"""
    print("\n🔍 Тест 3: Подключение к Qdrant")
    print("-" * 60)
    
    from qdrant_helper import get_qdrant_client
    
    client = get_qdrant_client()
    
    if client:
        try:
            # Проверяем коллекцию
            collection_name = os.getenv("QDRANT_COLLECTION", "hr_knowledge_base")
            collections = client.get_collections()
            
            exists = any(c.name == collection_name for c in collections.collections)
            
            if exists:
                count = client.count(collection_name=collection_name)
                print(f"✅ Подключение к Qdrant успешно!")
                print(f"   Коллекция: {collection_name}")
                print(f"   Точек в БД: {count.count}")
            else:
                print(f"✅ Подключение к Qdrant успешно!")
                print(f"⚠️  Коллекция {collection_name} не найдена")
                print(f"   (будет создана при первой индексации)")
            
            return True
        except Exception as e:
            print(f"❌ Ошибка работы с Qdrant: {e}")
            return False
    else:
        print("❌ Не удалось подключиться к Qdrant")
        return False

async def test_embedding():
    """Тест создания эмбеддинга"""
    print("\n🔍 Тест 4: Создание эмбеддинга")
    print("-" * 60)
    
    from qdrant_helper import generate_embedding_async
    
    test_text = "Это тестовый текст для проверки эмбеддингов"
    
    embedding = await generate_embedding_async(test_text)
    
    if embedding:
        print(f"✅ Эмбеддинг создан!")
        print(f"   Размерность: {len(embedding)}")
        print(f"   Первые значения: {embedding[:5]}")
        return True
    else:
        print("❌ Ошибка создания эмбеддинга")
        return False

async def test_text_extraction():
    """Тест извлечения текста (если есть тестовые файлы)"""
    print("\n🔍 Тест 5: Извлечение текста из документов")
    print("-" * 60)
    
    from yandex_disk_helper import list_files, download_file_content
    from yadisk_indexer import extract_text_from_content
    
    # Получаем список файлов
    result = await list_files(path="/", limit=50)
    
    if not result:
        print("⚠️  Не удалось получить список файлов")
        return False
    
    items = result.get("_embedded", {}).get("items", [])
    
    # Ищем текстовый или PDF файл
    test_file = None
    for item in items:
        if item.get("type") == "file":
            name = item.get("name", "")
            ext = name.lower().split('.')[-1] if '.' in name else ''
            
            if ext in ['txt', 'pdf', 'docx', 'md']:
                test_file = item
                break
    
    if not test_file:
        print("⚠️  Не найдено подходящих файлов для теста")
        print("   (нужен .txt, .pdf, .docx или .md файл)")
        return True  # Не критично
    
    # Скачиваем и извлекаем текст
    file_name = test_file.get("name", "")
    file_path = test_file.get("path", "")
    
    print(f"📥 Скачивание тестового файла: {file_name}")
    
    content = await download_file_content(file_path)
    
    if not content:
        print(f"⚠️  Не удалось скачать {file_name}")
        return False
    
    print(f"✅ Файл скачан: {len(content)} байт")
    
    text = extract_text_from_content(content, file_name)
    
    if text:
        print(f"✅ Текст извлечен: {len(text)} символов")
        print(f"   Превью: {text[:100]}...")
        return True
    else:
        print(f"❌ Не удалось извлечь текст из {file_name}")
        return False

async def run_all_tests():
    """Запустить все тесты"""
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ YANDEX DISK INDEXER")
    print("=" * 60)
    
    results = []
    
    # Проверяем переменные окружения
    print("\n📋 Проверка переменных окружения:")
    print("-" * 60)
    
    required_vars = {
        "YANDEX_TOKEN": os.getenv("YANDEX_TOKEN") or os.getenv("YANDEX_DISK_TOKEN"),
        "QDRANT_URL": os.getenv("QDRANT_URL"),
        "QDRANT_API_KEY": os.getenv("QDRANT_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    }
    
    all_set = True
    for var, value in required_vars.items():
        if value:
            print(f"✅ {var}: установлен ({len(value)} символов)")
        else:
            print(f"❌ {var}: НЕ УСТАНОВЛЕН!")
            all_set = False
    
    if not all_set:
        print("\n❌ Не все переменные окружения установлены!")
        print("   Проверьте .env файл")
        return
    
    # Запускаем тесты
    results.append(await test_yandex_disk_connection())
    results.append(await test_list_files())
    results.append(await test_qdrant_connection())
    results.append(await test_embedding())
    results.append(await test_text_extraction())
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Пройдено: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("   Индексатор готов к запуску!")
        print("\n💡 Запустите: ./start_yadisk_indexer.sh")
    else:
        print("\n⚠️  Некоторые тесты не прошли")
        print("   Проверьте логи выше для деталей")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
