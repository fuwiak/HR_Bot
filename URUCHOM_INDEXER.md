# ⚡ Uruchom Yandex Disk Indexer (3 komendy)

## 🏠 Lokalnie (na komputerze)

```bash
# 1. Nadaj uprawnienia (tylko raz)
chmod +x start_yadisk_indexer.sh

# 2. Uruchom
./start_yadisk_indexer.sh

# 3. Sprawdź logi
tail -f logs/yadisk_indexer.out
```

**Zatrzymaj:**
```bash
./stop_yadisk_indexer.sh
```

---

## ☁️ Railway (w chmurze)

### Option 1: Dashboard (GUI)

1. **Otwórz:** https://railway.app
2. **Nowy serwis:** `+ New Service` → `GitHub Repo` → `HR_Bot`
3. **Nazwa:** `yadisk-indexer`
4. **Settings:**
   - Build → Dockerfile Path: `Dockerfile.yadisk`
   - Deploy → Start Command: `python -u yadisk_indexer.py`
5. **Variables:** Skopiuj z telegram-bot serwisu (te same!)
   ```
   YANDEX_TOKEN
   QDRANT_URL
   QDRANT_API_KEY
   OPENROUTER_API_KEY  (lub OPENAI_API_KEY)
   ```
6. **Deploy!**

---

### Option 2: CLI (szybciej)

```bash
# 1. Link do projektu
cd /Users/user/HR_Bot
railway link

# 2. Utwórz serwis
railway service create yadisk-indexer

# 3. Skopiuj zmienne z telegram-bot
railway variables set YANDEX_TOKEN="your_yandex_token_here"
railway variables set OPENROUTER_API_KEY="sk-or-v1-..."
# ... (lub skopiuj wszystkie z głównego bota)

# 4. Deploy
railway up

# 5. Logi
railway logs
```

---

## ✅ Jak sprawdzić czy działa?

### Lokalnie:
```bash
# Proces działa?
ps aux | grep yadisk_indexer

# Logi pokazują iteracje?
tail logs/yadisk_indexer.out | grep "ИТЕРАЦИЯ"

# Są pliki w Qdrant?
python -c "from qdrant_helper import get_qdrant_client; c=get_qdrant_client(); print(c.count('hr_knowledge_base'))"
```

### Railway:
```bash
railway logs | grep "ИТЕРАЦИЯ"
```

---

## 🎯 Poprawne logi:

```log
[INFO] 🚀 Запуск Yandex Disk Indexer
[INFO] 🔄 ИТЕРАЦИЯ #1
[INFO] 🔍 Сканирование папки: /
[INFO] ✅ Найдено 5 файлов
[INFO] 📥 Скачивание: document.pdf
[INFO] 🎉 Файл успешно проиндексирован
[INFO] ✅ Обработано файлов: 5
[INFO] ⏳ Следующее сканирование через 300 секунд
```

---

## 🐛 Problemy?

**"Permission denied":**
```bash
chmod +x start_yadisk_indexer.sh
```

**"YANDEX_TOKEN not set":**
```bash
cat .env | grep YANDEX_TOKEN
# Powinno być tam!
```

**Nie widać logów:**
```bash
mkdir -p logs
./start_yadisk_indexer.sh
```

---

## 📚 Więcej info:

- **START_INDEXER.md** - pełna instrukcja
- **YADISK_QUICKSTART.md** - quick start
- **YADISK_INDEXER_GUIDE.md** - szczegóły techniczne

---

**Gotowe! Indexator pracuje w tle i indeksuje pliki co 5 minut! 🚀**
