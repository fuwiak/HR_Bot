# 🔧 Fix: Indexer nie może połączyć się z Qdrant Cloud

## ❌ Problem

```
❌ Ошибка подключения к Qdrant (http://localhost:6333): [Errno 61] Connection refused
```

**Przyczyna:** Indexator próbuje połączyć się z lokalnym Qdrant zamiast Qdrant Cloud.

---

## ✅ Rozwiązanie

### Krok 1: Zatrzymaj indexator

```bash
./stop_yadisk_indexer.sh

# Lub ręcznie zabij procesy
kill 58763 58259

# Sprawdź czy zatrzymane
ps aux | grep yadisk_indexer
```

---

### Krok 2: Sprawdź .env

Musisz mieć w `.env`:

```bash
# Sprawdź co jest
cat .env | grep QDRANT

# Powinno być:
# QDRANT_URL=https://xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.aws.cloud.qdrant.io
# QDRANT_API_KEY=your_api_key_here
```

---

### Krok 3: Dodaj zmienne (jeśli brakuje)

#### Opcja A: Skopiuj z Railway

```bash
# Jeśli masz Railway CLI
railway variables --service telegram-bot | grep QDRANT

# Skopiuj wartości do .env
```

#### Opcja B: Pobierz z Qdrant Dashboard

1. Otwórz https://cloud.qdrant.io
2. Wybierz swój klaster
3. Data Access → API Keys
4. Skopiuj:
   - **Cluster URL** → `QDRANT_URL`
   - **API Key** → `QDRANT_API_KEY`

#### Opcja C: Dodaj ręcznie do .env

```bash
# Otwórz edytor
nano .env

# Dodaj (ZASTĄP swoimi wartościami!):
QDRANT_URL=https://your-cluster.aws.cloud.qdrant.io
QDRANT_API_KEY=your_api_key_here
```

---

### Krok 4: Test połączenia

```bash
# Test Qdrant
python -c "from qdrant_helper import get_qdrant_client; c=get_qdrant_client(); print('✅ Połączono!' if c else '❌ Błąd')"
```

**Oczekiwany wynik:**
```
✅ Połączono!
```

---

### Krok 5: Uruchom indexator ponownie

```bash
./start_yadisk_indexer.sh
```

---

### Krok 6: Sprawdź logi

```bash
# Logi w pliku
tail -f yadisk_indexer.log

# Lub logi na ekranie (jeśli są)
tail -f logs/yadisk_indexer.out
```

**Poprawne logi powinny pokazywać:**
```log
[INFO] 🚀 Запуск Yandex Disk Indexer
[INFO] 📂 Папки для мониторинга: ['/']
[INFO] 🔄 ИТЕРАЦИЯ #1
[INFO] 🔍 Сканирование папки: /
[INFO] ✅ Найдено файлов для обработки
```

**NIE powinno być:**
```log
❌ Ошибка подключения к Qdrant (http://localhost:6333)
```

---

## 🧪 Pełny test przed uruchomieniem

Użyj skryptu testowego:

```bash
python test_yadisk_indexer.py
```

**Wszystkie testy powinny przejść:**
```
✅ YANDEX_TOKEN: установлен
✅ QDRANT_URL: установлен
✅ QDRANT_API_KEY: установлен
✅ Подключение к Яндекс.Диску
✅ Получение списка файлов
✅ Подключение к Qdrant  ← WAŻNE!
✅ Создание эмбеддинга

🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!
```

---

## 🔍 Debug: Co jest w .env?

```bash
# Pokaż co masz (bez haseł)
echo "YANDEX_TOKEN: $(grep YANDEX_TOKEN .env | cut -d= -f1)"
echo "QDRANT_URL: $(grep QDRANT_URL .env | cut -d= -f1)"
echo "QDRANT_API_KEY: $(grep QDRANT_API_KEY .env | cut -d= -f1)"
echo "OPENAI_API_KEY: $(grep OPENAI_API_KEY .env | cut -d= -f1)"
```

**Wszystkie 4 powinny się pokazać!**

---

## 🐛 Problemy?

### "Connection refused to localhost:6333"

➡️ **Brakuje QDRANT_URL w .env**

```bash
# Dodaj do .env
echo 'QDRANT_URL=https://your-cluster.aws.cloud.qdrant.io' >> .env
echo 'QDRANT_API_KEY=your_api_key' >> .env
```

---

### "Unauthorized" lub "403"

➡️ **Zły QDRANT_API_KEY**

```bash
# Pobierz nowy z Qdrant Dashboard
# https://cloud.qdrant.io → Data Access → API Keys
```

---

### "Collection not found"

➡️ **OK! Kolekcja zostanie utworzona automatycznie przy pierwszej indeksacji**

```bash
# To jest normalne przy pierwszym uruchomieniu
# Indexator utworzy kolekcję "hr_knowledge_base"
```

---

## ✅ Szybkie rozwiązanie (Copy-Paste)

```bash
# 1. Zatrzymaj
./stop_yadisk_indexer.sh

# 2. Sprawdź zmienne
python test_yadisk_indexer.py

# 3. Jeśli brak QDRANT_URL - dodaj do .env:
# QDRANT_URL=https://your-cluster.aws.cloud.qdrant.io
# QDRANT_API_KEY=your_api_key

# 4. Test ponownie
python -c "from qdrant_helper import get_qdrant_client; c=get_qdrant_client(); print('✅ OK' if c else '❌ FAIL')"

# 5. Uruchom
./start_yadisk_indexer.sh

# 6. Sprawdź
tail -f yadisk_indexer.log
```

---

## 🎯 Podsumowanie

**Problem:** Indexator używa `localhost:6333` zamiast Qdrant Cloud

**Rozwiązanie:** Dodaj do `.env`:
```env
QDRANT_URL=https://your-cluster.aws.cloud.qdrant.io
QDRANT_API_KEY=your_api_key_here
```

**Test:**
```bash
python test_yadisk_indexer.py
```

**Gotowe!** 🚀
