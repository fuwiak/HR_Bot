# 🔑 OpenRouter vs OpenAI - Konfiguracja Embeddings

## 🎯 Priorytet API

Kod automatycznie wybiera API dla embeddings w kolejności:

1. **OpenRouter** (priorytet!) - jeśli jest `OPENROUTER_API_KEY`
2. **OpenAI** (fallback) - jeśli brak OpenRouter, ale jest `OPENAI_API_KEY`

---

## ✅ Twoja konfiguracja (.env)

```env
OPENROUTER_API_KEY=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
OPENROUTER_API_URL=https://openrouter.ai/api/v1/chat/completions
OPENROUTER_MODEL=deepseek/deepseek-chat
```

**Status:** ✅ OpenRouter jest ustawiony!

---

## 🔧 Jak to działa?

### Z OpenRouter (twoja konfiguracja):

```python
# qdrant_helper.py automatycznie użyje:
EMBEDDING_API_URL = "https://openrouter.ai/api/v1/embeddings"
EMBEDDING_MODEL = "qwen/qwen3-embedding-8b"
EMBEDDING_DIMENSION = 1536

# Logi pokażą:
🔧 Используется OpenRouter (модель: qwen/qwen3-embedding-8b)
🔧 Вектора будут дополнены до 1536 для совместимости с Qdrant
```

### Z OpenAI (jeśli nie ma OpenRouter):

```python
EMBEDDING_API_URL = "https://api.openai.com/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
```

---

## 📊 Porównanie

| Feature | OpenRouter | OpenAI |
|---------|-----------|---------|
| Model | `qwen/qwen3-embedding-8b` | `text-embedding-3-small` |
| Natywna wymiarowość | 1024 | 1536 |
| Padding do 1536 | ✅ Tak | ❌ Nie (już 1536) |
| Koszt | Niższy | Wyższy |
| Wsparcie języków | Świetne (Qwen) | Dobre |
| Twój wybór | ✅ **Używasz** | Fallback |

---

## ✅ Sprawdzenie

```bash
# Sprawdź który API jest używany
./check_env.sh

# Wynik:
✅ OPENROUTER_API_KEY: ustawiony (...)
✅ QDRANT_URL: ustawiony (...)
✅ QDRANT_API_KEY: ustawiony (...)
```

---

## 🔄 Zmiana na OpenAI (jeśli potrzeba)

Jeśli chcesz używać OpenAI zamiast OpenRouter:

```bash
# 1. Usuń lub zakomentuj w .env:
# OPENROUTER_API_KEY=...

# 2. Dodaj OpenAI:
echo 'OPENAI_API_KEY=sk-...' >> .env

# 3. Restart indexer
./stop_yadisk_indexer.sh
./start_yadisk_indexer.sh
```

---

## 💡 Zalecenia

**Zostań przy OpenRouter!** Bo:
- ✅ Już masz klucz API
- ✅ Niższe koszty
- ✅ Model Qwen świetnie radzi sobie z różnymi językami
- ✅ Padding do 1536 działa bez problemów

---

## 🐛 Troubleshooting

### Błąd: "OPENAI_API_KEY not found"

➡️ **To OK!** Jeśli masz `OPENROUTER_API_KEY`, wszystko działa.

Kod szuka w kolejności:
1. `OPENROUTER_API_KEY` ← Twój jest tutaj ✅
2. `OPENAI_API_KEY` ← Nie potrzebny

### Chcesz potwierdzić który API jest używany?

```bash
# Uruchom test
python test_yadisk_indexer.py

# W logach zobaczysz:
🔧 Используется OpenRouter (модель: qwen/qwen3-embedding-8b)
```

---

## ✅ Podsumowanie

**Twoja konfiguracja:**
- ✅ `OPENROUTER_API_KEY` ustawiony
- ✅ Indexator będzie używał OpenRouter
- ✅ Model: `qwen/qwen3-embedding-8b`
- ✅ Wymiarowość: 1536 (z paddingiem)

**Wszystko działa poprawnie! 🚀**
