# 🚀 Jak włączyć Yandex Disk Indexer?

## ❓ Czy indexator jest włączony?

### Sprawdź lokalnie:
```bash
# Sprawdź proces
ps aux | grep yadisk_indexer

# Sprawdź PID file
cat yadisk_indexer.pid 2>/dev/null

# Sprawdź logi
tail -5 logs/yadisk_indexer.out
```

### Sprawdź na Railway:
```bash
# CLI
railway logs --service yadisk-indexer

# Lub w Dashboard:
# Railway → Service "yadisk-indexer" → Logs
```

---

## 🏠 Opcja 1: Lokalnie (na swoim komputerze)

### Krok 1: Sprawdź .env
```bash
cat .env | grep YANDEX_TOKEN
# Powinno być: YANDEX_TOKEN=your_yandex_token_here
```

### Krok 2: Uruchom indexator
```bash
# Nadaj uprawnienia (raz)
chmod +x start_yadisk_indexer.sh stop_yadisk_indexer.sh

# Uruchom!
./start_yadisk_indexer.sh
```

**Wynik:**
```
🚀 Запуск Yandex Disk Indexer...
✅ Переменные окружения загружены из .env
✅ Yandex Disk Indexer запущен (PID: 12345)
📋 Логи: logs/yadisk_indexer.out и yadisk_indexer.log

Управление:
  Остановить: kill 12345
  Статус: ps -p 12345
  Логи: tail -f logs/yadisk_indexer.out
```

### Krok 3: Sprawdź logi
```bash
# Na żywo
tail -f logs/yadisk_indexer.out

# Lub szczegółowe
tail -f yadisk_indexer.log
```

**Poprawne logi:**
```log
[INFO] 🚀 Запуск Yandex Disk Indexer
[INFO] 📂 Папки для мониторинга: ['/']
[INFO] ⏱️ Интервал сканирования: 300 секунд
[INFO] 🔄 ИТЕРАЦИЯ #1 - 2024-12-19 11:00:00
[INFO] 🔍 Сканирование папки: /
[INFO] ✅ Найдено 5 файлов для обработки в /
[INFO] 📥 Скачивание: document.pdf
[INFO] ✅ Извлечено 3456 символов из document.pdf
[INFO] 🎉 Файл document.pdf успешно проиндексирован (4 точек)
[INFO] ✅ Итерация #1 завершена
[INFO] ✅ Обработано файлов: 5
[INFO] ⏳ Следующее сканирование через 300 секунд...
```

### Krok 4: Zatrzymaj (jeśli potrzeba)
```bash
./stop_yadisk_indexer.sh
```

---

## ☁️ Opcja 2: Railway (w chmurze)

### Metoda A: Railway Dashboard (łatwiejsza)

#### 1. Otwórz Railway Dashboard
```
https://railway.app
```

#### 2. Utwórz nowy serwis
- Kliknij `+ New Service`
- Wybierz `GitHub Repo`
- Wybierz repozytorium `HR_Bot`
- Nazwa serwisu: `yadisk-indexer`

#### 3. Skonfiguruj Build
**Settings → Build:**
- Builder: `Dockerfile`
- Dockerfile Path: `Dockerfile.yadisk`

#### 4. Skonfiguruj Deploy
**Settings → Deploy:**
- Start Command: `python -u yadisk_indexer.py`
- Restart Policy: `On Failure`

#### 5. Dodaj zmienne środowiskowe
**Variables:**
```env
YANDEX_TOKEN=your_yandex_token_here
QDRANT_URL=https://your-cluster.aws.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_key
OPENAI_API_KEY=your_openai_key
YADISK_WATCH_FOLDERS=/
YADISK_SCAN_INTERVAL=300
QDRANT_COLLECTION=hr_knowledge_base
```

**Te same zmienne co dla Telegram bota!**

#### 6. Deploy
- Kliknij `Deploy`
- Poczekaj 2-3 minuty na build
- Sprawdź logi

---

### Metoda B: Railway CLI (szybsza)

#### 1. Zainstaluj Railway CLI
```bash
# macOS
brew install railway

# npm
npm install -g @railway/cli

# Zaloguj się
railway login
```

#### 2. Połącz z projektem
```bash
cd /Users/user/HR_Bot
railway link
# Wybierz swój projekt
```

#### 3. Utwórz serwis
```bash
# Utwórz nowy serwis
railway service create yadisk-indexer

# Przełącz się na niego
railway service
# Wybierz "yadisk-indexer"
```

#### 4. Dodaj zmienne
```bash
# Skopiuj z głównego bota
railway variables --service telegram-bot > vars.txt

# Lub dodaj ręcznie
railway variables set YANDEX_TOKEN="your_yandex_token_here"
railway variables set QDRANT_URL="https://..."
railway variables set QDRANT_API_KEY="..."
railway variables set OPENAI_API_KEY="..."
railway variables set YADISK_SCAN_INTERVAL="300"
railway variables set YADISK_WATCH_FOLDERS="/"
```

#### 5. Deploy
```bash
railway up --detach
```

#### 6. Sprawdź logi
```bash
railway logs --follow
```

---

## 🧪 Test przed uruchomieniem

Sprawdź czy wszystko działa:

```bash
# Test połączenia
python test_yadisk_indexer.py
```

**Oczekiwany wynik:**
```
============================================================
🧪 ТЕСТИРОВАНИЕ YANDEX DISK INDEXER
============================================================

📋 Проверка переменных окружения:
✅ YANDEX_TOKEN: установлен (82 символов)
✅ QDRANT_URL: установлен
✅ QDRANT_API_KEY: установлен
✅ OPENAI_API_KEY: установлен

🔍 Тест 1: Подключение к Яндекс.Диску
✅ Подключение успешно!

🔍 Тест 2: Получение списка файлов
✅ Найдено файлов: 10

🔍 Тест 3: Подключение к Qdrant
✅ Подключение к Qdrant успешно!

🔍 Тест 4: Создание эмбеддинга
✅ Эмбеддинг создан!

============================================================
📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ
✅ Пройдено: 5/5

🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!
```

---

## 📊 Jak sprawdzić czy działa?

### 1. Logi pokazują iteracje
```bash
tail -f logs/yadisk_indexer.out | grep "ИТЕРАЦИЯ"
```

### 2. Pliki w Qdrant
```python
from qdrant_helper import get_qdrant_client

client = get_qdrant_client()
count = client.count(collection_name="hr_knowledge_base")
print(f"Punktów w Qdrant: {count.count}")

# Sprawdź źródło
results = client.scroll(
    collection_name="hr_knowledge_base",
    scroll_filter={"must": [{"key": "source", "match": {"value": "yadisk"}}]},
    limit=10
)
print(f"Plików z Yandex Disk: {len(results[0])}")
```

### 3. Test w bocie
```bash
# W Telegram bot
/search договор
/search документ
```

---

## ⚙️ Konfiguracja

### Zmień interwał skanowania

**Lokalnie (.env):**
```env
YADISK_SCAN_INTERVAL=60    # Co 1 minutę (szybko)
YADISK_SCAN_INTERVAL=300   # Co 5 minut (normalnie)
YADISK_SCAN_INTERVAL=3600  # Co 1 godzinę (rzadko)
```

**Railway:**
```bash
railway variables set YADISK_SCAN_INTERVAL="600"
```

### Zmień foldery do monitorowania

**Lokalnie (.env):**
```env
YADISK_WATCH_FOLDERS=/                        # Wszystko
YADISK_WATCH_FOLDERS=/Dokumenty,/KP,/Umowy   # Konkretne foldery
```

**Railway:**
```bash
railway variables set YADISK_WATCH_FOLDERS="/Dokumenty,/KP"
```

---

## 🐛 Problemy?

### Błąd: "YANDEX_TOKEN not set"
```bash
# Sprawdź .env
cat .env | grep YANDEX_TOKEN

# Dodaj jeśli brak
echo 'YANDEX_TOKEN=your_yandex_token_here' >> .env
```

### Błąd: "Cannot connect to Qdrant"
```bash
# Sprawdź credentials
cat .env | grep QDRANT

# Test połączenia
python -c "from qdrant_helper import get_qdrant_client; print(get_qdrant_client())"
```

### Błąd: "Permission denied"
```bash
# Nadaj uprawnienia
chmod +x start_yadisk_indexer.sh stop_yadisk_indexer.sh

# Uruchom ponownie
./start_yadisk_indexer.sh
```

### Nie indeksuje plików
```bash
# Sprawdź logi
grep "ERROR" yadisk_indexer.log
grep "❌" logs/yadisk_indexer.out

# Zwiększ limit rozmiaru
echo 'YADISK_MAX_FILE_SIZE=100' >> .env
```

---

## 🎯 Szybki start (TL;DR)

### Lokalnie:
```bash
chmod +x start_yadisk_indexer.sh
./start_yadisk_indexer.sh
tail -f logs/yadisk_indexer.out
```

### Railway:
```bash
railway service create yadisk-indexer
railway variables set YANDEX_TOKEN="your_yandex_token_here"
railway up
railway logs
```

---

## ✅ Gotowe!

**Indexator indeksuje pliki z Yandex Disk co 5 minut!**

**Wszystkie dokumenty dostępne dla RAG w bocie! 🚀**
