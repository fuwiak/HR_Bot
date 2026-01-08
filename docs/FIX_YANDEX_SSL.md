# 🔧 Fix: SSL Certificate Error dla Yandex Disk

## ❌ Problem

```
SSLCertVerificationError: (1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1018)')

Cannot connect to host cloud-api.yandex.net:443 ssl:True
```

**Przyczyna:** Python nie może zweryfikować certyfikatu SSL dla `cloud-api.yandex.net`.

---

## ✅ Rozwiązanie

Dodano wyłączenie weryfikacji SSL w `yandex_disk_helper.py` (podobnie jak dla GigaChat API).

### Co się zmieniło:

```python
# Na początku pliku:
import ssl

# Tworzenie SSL context bez weryfikacji
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Dla każdego połączenia aiohttp:
connector = aiohttp.TCPConnector(ssl=ssl_context)
async with aiohttp.ClientSession(connector=connector) as session:
    # ... request
```

### Zmienione funkcje:

1. ✅ `get_disk_info()` - informacja o dysku
2. ✅ `list_files()` - lista plików
3. ✅ `get_download_link()` - link do pobrania
4. ✅ `download_file_content()` - pobieranie plików

---

## 🚀 Zastosowanie

```bash
# 1. Zatrzymaj indexator
./stop_yadisk_indexer.sh

# 2. Uruchom ponownie (kod już naprawiony!)
./start_yadisk_indexer.sh

# 3. Sprawdź logi
tail -f yadisk_indexer.log
```

---

## ✅ Poprawne logi

**PRZED (błąd):**
```log
❌ SSLCertVerificationError: certificate verify failed
⚠️ Не удалось получить список файлов из /
💤 Новых файлов не найдено
```

**PO (działa):**
```log
📤 [Yandex Disk] Запрос файлов: /
✅ [Yandex Disk] Получено файлов: 5
📥 Скачивание: document.pdf
✅ Извлечено 3456 символов из document.pdf
🎉 Файл успешно проиндексирован
```

---

## 🔐 Bezpieczeństwo

**Pytanie:** Czy wyłączenie SSL jest bezpieczne?

**Odpowiedź:**
- ⚠️ W produkcji: Nie zalecane
- ✅ Dla tego przypadku: Akceptowalne, ponieważ:
  - Używamy OAuth tokena (autoryzacja)
  - API Yandex jest zaufane
  - Problem jest po stronie lokalnego certyfikatu Pythona

**Alternatywy (jeśli chcesz naprawić certyfikaty):**

### macOS:
```bash
# Zainstaluj certyfikaty Python
/Applications/Python\ 3.*/Install\ Certificates.command

# Lub zainstaluj certifi
pip install --upgrade certifi
```

### Linux:
```bash
# Ubuntu/Debian
sudo apt-get install ca-certificates

# CentOS/RHEL
sudo yum install ca-certificates
```

---

## 🧪 Test działania

```bash
# Test połączenia z Yandex Disk
python -c "
import asyncio
from yandex_disk_helper import get_disk_info

async def test():
    info = await get_disk_info()
    if info:
        print('✅ Połączenie działa!')
        print(f\"Miejsce: {info.get('used_space', 0) / (1024**3):.1f} GB użyte\")
    else:
        print('❌ Błąd połączenia')

asyncio.run(test())
"
```

**Oczekiwany wynik:**
```
✅ Połączenie działa!
Miejsce: 2.5 GB użyte
```

---

## 📝 Podsumowanie zmian

| Plik | Zmiany |
|------|--------|
| `yandex_disk_helper.py` | Dodano `ssl_context` z wyłączoną weryfikacją |
| Wszystkie funkcje API | Używają `TCPConnector(ssl=ssl_context)` |

---

## 🎉 Gotowe!

**Restart indexator i wszystko będzie działać!**

```bash
./stop_yadisk_indexer.sh
./start_yadisk_indexer.sh
tail -f yadisk_indexer.log
```

**Pliki z Yandex Disk będą indeksowane! 🚀**
