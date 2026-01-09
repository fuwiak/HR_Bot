# 🔧 Ustawienie Dockerfile Path dla Mini App w Railway

## ✅ Metoda 1: Przez Railway Dashboard (Zalecane)

1. **Otwórz Railway Dashboard:**
   - Przejdź do projektu: https://railway.app/project/32ed5051-0f81-493a-8fb0-ae1cf75f37d2
   - Wybierz serwis **MINI-APP**

2. **Ustaw Dockerfile Path:**
   - **Settings → Build → Dockerfile Path**
   - Wpisz: `frontend/Dockerfile`
   - Zapisz zmiany

3. **Przeładuj serwis:**
   - Railway automatycznie przeładuje serwis
   - Lub: **Deployments → Redeploy**

## ✅ Metoda 2: Przez zmienną środowiskową

1. **Dodaj zmienną środowiskową:**
   - **Settings → Variables → Add Variable**
   - **Key:** `RAILWAY_DOCKERFILE_PATH`
   - **Value:** `frontend/Dockerfile`
   - Zapisz

2. **Przeładuj serwis**

## ✅ Metoda 3: Plik .railway/frontend.toml (Już skonfigurowane)

Plik `.railway/frontend.toml` już zawiera:
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "frontend/Dockerfile"
```

Railway powinien automatycznie używać tego pliku, jeśli:
- Serwis jest połączony z projektem
- Plik jest w repozytorium Git

## 🔍 Weryfikacja

Po ustawieniu Dockerfile Path, w logach build powinno być:
```
Building with Dockerfile: frontend/Dockerfile
```

**NIE powinno być:**
```
Building with Dockerfile: Dockerfile
```

## 📋 Szybkie sprawdzenie

1. **Railway Dashboard → MINI-APP → Settings → Build**
2. Sprawdź **Dockerfile Path** - powinno być: `frontend/Dockerfile`
3. Jeśli nie, zmień i zapisz

## 💡 Uwaga

Jeśli używasz `.railway/frontend.toml`, upewnij się, że:
- Plik jest w repozytorium Git
- Railway jest połączony z repozytorium
- Serwis jest poprawnie skonfigurowany
