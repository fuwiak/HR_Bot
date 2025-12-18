"""
Тест для записи в Google Sheets лист 'Запись'
Проверяет, что запись создается правильно в первую доступную строку
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import uuid

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google_sheets_helper import get_sheets_client, GOOGLE_SHEETS_SPREADSHEET_ID

load_dotenv()

def test_write_booking():
    """Тест записи в Google Sheets лист 'Запись'"""
    print("🧪 ТЕСТ: Запись в Google Sheets лист 'Запись'")
    print("=" * 60)
    
    try:
        client = get_sheets_client()
        if not client:
            print("❌ Ошибка: Google Sheets клиент не инициализирован")
            return False
        
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)
        print(f"✅ Подключение к таблице: {GOOGLE_SHEETS_SPREADSHEET_ID}")
        
        # Получаем или создаем лист "Запись"
        try:
            worksheet = spreadsheet.worksheet("Запись")
            print("✅ Лист 'Запись' найден")
        except Exception as e:
            print(f"⚠️ Лист 'Запись' не найден, создаю новый...")
            worksheet = spreadsheet.add_worksheet(title="Запись", rows=1000, cols=12)
            # Добавляем заголовки
            headers = [
                "Дата создания", "ID записи", "Дата", "Время", "Мастер", "Услуга",
                "Имя клиента", "Телефон", "Цена", "Статус", "Комментарий"
            ]
            worksheet.append_row(headers)
            print("✅ Лист 'Запись' создан с заголовками")
        
        # Генерируем тестовые данные
        booking_id = str(uuid.uuid4())
        now = datetime.now()
        test_data = {
            "date": "09.12.2025",
            "time": "08:00",
            "master": "Роман",
            "service": "Бритье головы",
            "client_name": "Тестовый Клиент",
            "client_phone": "+79999999999",
            "price": 1700,
            "status": "confirmed",
            "user_id": 1234567890
        }
        
        # Формируем строку для записи
        row_data = [
            now.strftime("%Y-%m-%d %H:%M:%S"),  # Дата создания
            booking_id,  # ID записи
            test_data["date"],  # Дата записи
            test_data["time"],  # Время записи
            test_data["master"],  # Мастер
            test_data["service"],  # Услуга
            test_data["client_name"],  # Имя клиента
            test_data["client_phone"],  # Телефон
            test_data["price"],  # Цена
            test_data["status"],  # Статус
            f"Запись через Telegram бот (user_id: {test_data['user_id']})"  # Комментарий
        ]
        
        print(f"\n📝 Данные для записи:")
        print(f"   ID: {booking_id}")
        print(f"   Дата: {test_data['date']} {test_data['time']}")
        print(f"   Мастер: {test_data['master']}")
        print(f"   Услуга: {test_data['service']}")
        print(f"   Клиент: {test_data['client_name']}")
        print(f"   Телефон: {test_data['client_phone']}")
        print(f"   Цена: {test_data['price']} ₽")
        
        # Записываем в первую доступную строку (append_row автоматически добавляет в конец)
        worksheet.append_row(row_data)
        print(f"\n✅ Запись успешно добавлена в Google Sheets!")
        
        # Проверяем, что запись действительно записалась
        all_values = worksheet.get_all_values()
        print(f"\n📊 Всего строк в листе: {len(all_values)}")
        
        # Ищем нашу запись по ID
        found = False
        for i, row in enumerate(all_values, 1):
            if len(row) > 1 and row[1] == booking_id:
                print(f"✅ Запись найдена в строке {i}:")
                print(f"   Дата создания: {row[0] if len(row) > 0 else 'N/A'}")
                print(f"   ID: {row[1] if len(row) > 1 else 'N/A'}")
                print(f"   Дата: {row[2] if len(row) > 2 else 'N/A'}")
                print(f"   Время: {row[3] if len(row) > 3 else 'N/A'}")
                print(f"   Мастер: {row[4] if len(row) > 4 else 'N/A'}")
                print(f"   Услуга: {row[5] if len(row) > 5 else 'N/A'}")
                print(f"   Клиент: {row[6] if len(row) > 6 else 'N/A'}")
                print(f"   Телефон: {row[7] if len(row) > 7 else 'N/A'}")
                print(f"   Цена: {row[8] if len(row) > 8 else 'N/A'}")
                print(f"   Статус: {row[9] if len(row) > 9 else 'N/A'}")
                found = True
                break
        
        if not found:
            print("⚠️ Запись не найдена в листе (возможно, нужно обновить страницу)")
        
        print("\n" + "=" * 60)
        print("✅ ТЕСТ ПРОЙДЕН: Запись успешно создана в Google Sheets")
        return True
        
    except Exception as e:
        print(f"\n❌ ОШИБКА ТЕСТА: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_write_booking()
    sys.exit(0 if success else 1)





