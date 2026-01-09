# 🔧 Исправление ошибки entrypoint.sh в Mini App

## ❌ Проблема

Mini App пытается запустить `/entrypoint.sh`, который проверяет `DATABASE_URL`:
```
🔍 Проверка DATABASE_URL...
❌ ОШИБКА: DATABASE_URL не установлен!
/entrypoint.sh: 6: Bad substitution
```

## 🔍 Причина

Railway использует неправильный Dockerfile для Mini App. Вместо `frontend/Dockerfile` (который просто запускает `node server.js`), используется главный `Dockerfile` (который имеет entrypoint.sh для backend).

## ✅ Решение

### 1. Проверьте Dockerfile Path в Railway

**Mini App сервис → Settings → Build → Dockerfile Path:**

Должно быть:
```
frontend/Dockerfile
```

**НЕ должно быть:**
- ❌ `Dockerfile` (главный, для Telegram Bot)
- ❌ `Dockerfile.backend` (для Backend API)
- ❌ `Dockerfile.frontend` (старый, в корне)

### 2. Проверьте .railway/frontend.toml

Файл `.railway/frontend.toml` должен содержать:
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "frontend/Dockerfile"
```

### 3. Убедитесь, что frontend/Dockerfile правильный

`frontend/Dockerfile` должен:
- ✅ Использовать `node:18-alpine`
- ✅ Иметь `CMD ["node", "server.js"]`
- ❌ НЕ иметь `ENTRYPOINT ["/entrypoint.sh"]`
- ❌ НЕ проверять `DATABASE_URL`

### 4. Пересоберите сервис

После изменения Dockerfile Path:
1. Сохраните изменения
2. Railway автоматически пересоберет сервис
3. Или: Deployments → Redeploy

## 📋 Правильная конфигурация

**frontend/Dockerfile:**
```dockerfile
FROM node:18-alpine AS base
# ... build steps ...
CMD ["node", "server.js"]  # ✅ Правильно
```

**НЕ должно быть:**
```dockerfile
ENTRYPOINT ["/entrypoint.sh"]  # ❌ Это для backend!
```

## 🔍 Проверка

После исправления в логах должно быть:
```
Starting Container
Ready on http://0.0.0.0:3000
```

**НЕ должно быть:**
```
🔍 Проверка DATABASE_URL...
❌ ОШИБКА: DATABASE_URL не установлен!
```
