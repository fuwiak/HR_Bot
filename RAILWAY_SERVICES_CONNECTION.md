# 🔗 Railway: Automatyczne połączenie między serwisami

## ✅ Odpowiedź: NIE musisz ręcznie ustawiać DATABASE_URL

Railway **automatycznie** udostępnia zmienne środowiskowe do połączenia między serwisami w tym samym projekcie.

## Jak to działa na Railway

### 1. **Automatyczne zmienne środowiskowe**

Railway automatycznie tworzy zmienne środowiskowe dla każdego serwisu:

#### PostgreSQL:
```bash
DATABASE_URL="postgresql://postgres:password@railway-private-domain:5432/railway"
DATABASE_PUBLIC_URL="postgresql://postgres:password@railway-tcp-proxy-domain:port/railway"
PGHOST="railway-private-domain"
PGPORT="5432"
PGDATABASE="railway"
PGUSER="postgres"
PGPASSWORD="password"
```

#### Redis:
```bash
REDIS_URL="redis://default:password@railway-private-domain:6379"
REDIS_PUBLIC_URL="redis://default:password@railway-tcp-proxy-domain:port"
REDISHOST="railway-private-domain"
REDISPORT="6379"
REDISPASSWORD="password"
REDISUSER="default"
```

#### Qdrant:
```bash
QDRANT_HOST="railway-private-domain"
QDRANT_PORT="6333"
PORT="6333"
RAILWAY_PRIVATE_DOMAIN="railway-private-domain"
```

### 2. **Wewnętrzna sieć Railway**

Serwisy w tym samym projekcie Railway automatycznie widzą się przez **wewnętrzną sieć**:

- ✅ **Szybsze połączenia** - bezpośrednia komunikacja wewnętrzna
- ✅ **Bezpieczne** - nie wychodzi na zewnątrz
- ✅ **Automatyczne** - Railway zarządza routingiem

### 3. **Jak kod automatycznie znajduje serwisy**

#### PostgreSQL (`database.py`):
```python
# Automatycznie używa Railway zmiennych
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")
PGHOST = os.getenv("PGHOST")
PGPORT = os.getenv("PGPORT", "5432")
# ...
```

#### Redis (`redis_helper.py`):
```python
# Automatycznie używa Railway zmiennych
REDIS_URL = os.getenv("REDIS_URL") or os.getenv("REDIS_PUBLIC_URL")
REDIS_HOST = os.getenv("REDISHOST") or os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDISPORT") or os.getenv("REDIS_PORT", "6379"))
# ...
```

#### Qdrant (`qdrant_helper.py`):
```python
# Automatycznie używa Railway zmiennych
RAILWAY_QDRANT_HOST = os.getenv("QDRANT_HOST") or os.getenv("RAILWAY_PRIVATE_DOMAIN")
RAILWAY_QDRANT_PORT = os.getenv("QDRANT_PORT") or os.getenv("PORT", "6333")
# ...
```

## Co musisz zrobić

### ✅ Tylko to:

1. **Dodaj serwisy do projektu Railway:**
   - PostgreSQL
   - Redis
   - Qdrant
   - Telegram Bot

2. **Upewnij się że wszystkie są w tym samym projekcie**

3. **Railway automatycznie:**
   - Tworzy zmienne środowiskowe
   - Udostępnia je wszystkim serwisom
   - Konfiguruje wewnętrzną sieć

### ❌ NIE musisz:

- ❌ Ręcznie ustawiać `DATABASE_URL`
- ❌ Ręcznie ustawiać `REDIS_URL`
- ❌ Ręcznie ustawiać `QDRANT_HOST`
- ❌ Konfigurować połączenia między serwisami

## Przykład konfiguracji

### Railway Dashboard → Variables

Railway automatycznie pokazuje zmienne dla każdego serwisu:

```
PostgreSQL Service:
  DATABASE_URL (automatycznie)
  PGHOST (automatycznie)
  PGPORT (automatycznie)
  ...

Redis Service:
  REDIS_URL (automatycznie)
  REDISHOST (automatycznie)
  REDISPORT (automatycznie)
  ...

Qdrant Service:
  QDRANT_HOST (automatycznie)
  QDRANT_PORT (automatycznie)
  ...
```

### Telegram Bot Service

Automatycznie otrzymuje wszystkie zmienne z innych serwisów:

```
✅ DATABASE_URL (z PostgreSQL)
✅ REDIS_URL (z Redis)
✅ QDRANT_HOST (z Qdrant)
✅ ... wszystkie inne zmienne
```

## Weryfikacja

### Sprawdź logi po deploy:

```
✅ PostgreSQL connection pool создан через DATABASE_URL
✅ Redis клиент создан через REDIS_URL
✅ Используется Railway Qdrant: http://railway-private-domain:6333
```

### Jeśli widzisz błędy:

1. **Sprawdź że serwisy są w tym samym projekcie**
2. **Sprawdź że serwisy są uruchomione**
3. **Sprawdź logi Railway Dashboard → Variables**

## Ręczna konfiguracja (opcjonalna)

Jeśli chcesz ręcznie ustawić zmienne (nie jest konieczne):

### Railway Dashboard → Variables → Add Variable

```bash
# Tylko jeśli potrzebujesz nadpisać automatyczne wartości
DATABASE_URL="postgresql://..."
REDIS_URL="redis://..."
```

**Ale to nie jest konieczne!** Railway robi to automatycznie.

## Podsumowanie

| Co | Railway robi automatycznie | Musisz zrobić |
|----|---------------------------|---------------|
| Zmienne środowiskowe | ✅ Tak | ❌ Nie |
| Połączenia między serwisami | ✅ Tak | ❌ Nie |
| Wewnętrzna sieć | ✅ Tak | ❌ Nie |
| Routing | ✅ Tak | ❌ Nie |
| Dodanie serwisów | ❌ Nie | ✅ Tak (raz) |

## FAQ

### Q: Czy muszę kopiować DATABASE_URL między serwisami?
**A:** Nie! Railway automatycznie udostępnia zmienne wszystkim serwisom w projekcie.

### Q: Czy muszę ustawiać porty?
**A:** Nie! Railway automatycznie ustawia porty i udostępnia je przez zmienne.

### Q: Czy połączenia są bezpieczne?
**A:** Tak! Railway używa wewnętrznej sieci, która nie wychodzi na zewnątrz.

### Q: Co jeśli serwis nie widzi innych?
**A:** Sprawdź że wszystkie serwisy są w tym samym projekcie Railway.

## Więcej informacji

- Railway Docs: [Service Networking](https://docs.railway.app/develop/variables)
- Railway Docs: [Service Discovery](https://docs.railway.app/develop/service-discovery)
