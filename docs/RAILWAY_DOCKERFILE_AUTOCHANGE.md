# 🔧 Dlaczego Railway zmienia Dockerfile Path na "Dockerfile"?

## ❌ Problem

Podczas tworzenia nowego serwisu MINI APP, Railway automatycznie zmienia ścieżkę z `frontend/Dockerfile` na `Dockerfile` (katalog główny).

## 🔍 Przyczyna

Railway ma **domyślne zachowanie**:

1. **Przy tworzeniu nowego serwisu**, Railway:
   - Szuka konfiguracji w katalogu głównym (`railway.json` lub `railway.toml`)
   - Używa domyślnej wartości `Dockerfile` (katalog główny)
   - **NIE używa** automatycznie plików `.railway/*.toml` dla nowych serwisów

2. **Pliki `.railway/*.toml`** są używane tylko gdy:
   - Serwis jest już połączony z projektem
   - Railway wie, który plik konfiguracyjny użyć
   - Używasz Railway CLI z odpowiednim serwisem

## ✅ Rozwiązanie

### Metoda 1: Ustawienie w Railway Dashboard (Zalecane)

**Po utworzeniu nowego serwisu:**

1. **Railway Dashboard → MINI-APP → Settings → Build**
2. **Dockerfile Path:** zmień z `Dockerfile` na `frontend/Dockerfile`
3. **Zapisz** - Railway automatycznie przeładuje serwis

### Metoda 2: Zmienna środowiskowa (Działa automatycznie)

**Dodaj zmienną przed pierwszym deployem:**

```bash
railway variables --set "RAILWAY_DOCKERFILE_PATH=frontend/Dockerfile" --service MINI-APP
```

Lub w Railway Dashboard:
- **Settings → Variables → Add Variable**
- **Key:** `RAILWAY_DOCKERFILE_PATH`
- **Value:** `frontend/Dockerfile`

### Metoda 3: Poprawka w railway.json (Dla wszystkich serwisów)

Możesz zmienić domyślną konfigurację w `railway.json`, ale to wpłynie na wszystkie serwisy:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "frontend/Dockerfile"  // ⚠️ To wpłynie na wszystkie serwisy!
  }
}
```

**⚠️ Uwaga:** To nie jest zalecane, jeśli masz wiele serwisów z różnymi Dockerfile.

## 🎯 Najlepsze rozwiązanie

**Kombinacja Metody 1 i 2:**

1. **Utwórz serwis** w Railway Dashboard
2. **Natychmiast po utworzeniu:**
   - Ustaw `RAILWAY_DOCKERFILE_PATH=frontend/Dockerfile` w zmiennych środowiskowych
   - LUB zmień Dockerfile Path w Settings → Build
3. **Zapisz** - Railway użyje właściwego Dockerfile

## 📋 Checklist dla nowego serwisu

- [ ] Utworzono serwis MINI-APP w Railway
- [ ] Ustawiono `RAILWAY_DOCKERFILE_PATH=frontend/Dockerfile` w zmiennych
- [ ] LUB ustawiono Dockerfile Path w Settings → Build → `frontend/Dockerfile`
- [ ] Sprawdzono, że `.railway/frontend.toml` istnieje i jest poprawny
- [ ] Przeładowano serwis (Redeploy)

## 💡 Dlaczego Railway tak robi?

Railway zakłada, że:
- Większość projektów ma jeden Dockerfile w katalogu głównym
- Dla wielu serwisów używa się osobnych repozytoriów
- Konfiguracja per-serwis jest opcjonalna

Dlatego domyślnie używa `Dockerfile` z katalogu głównego i wymaga ręcznej konfiguracji dla niestandardowych ścieżek.

## 🔧 Automatyzacja (Opcjonalnie)

Możesz stworzyć skrypt, który automatycznie ustawia Dockerfile Path po utworzeniu serwisu:

```bash
#!/bin/bash
# auto-set-dockerfile.sh

railway link -s MINI-APP
railway variables --set "RAILWAY_DOCKERFILE_PATH=frontend/Dockerfile"
echo "✅ Dockerfile Path ustawiony na frontend/Dockerfile"
```
