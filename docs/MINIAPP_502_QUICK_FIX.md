# 🚨 Быстрое исправление 502 ошибки Mini App

## ❌ Проблема

```
https://mini-app-production-153f.up.railway.app/ → 502 Bad Gateway
```

## ✅ Решение (по порядку)

### 1. **Уберите ненужные переменные из Mini App**

Mini App **НЕ нужны** эти переменные:
- ❌ `DATABASE_URL` 
- ❌ `QDRANT_HOST`
- ❌ `TELEGRAM_TOKEN`

**Оставьте ТОЛЬКО:**
```env
PORT=3000
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://hrbot-production-f67c.up.railway.app
BACKEND_URL=https://hrbot-production-f67c.up.railway.app
```

### 2. **Проверьте Dockerfile Path**

**Mini App сервис → Settings → Build → Dockerfile Path:**

Должно быть:
```
frontend/Dockerfile
```

### 3. **Проверьте Port**

**Mini App сервис → Settings → Networking → Port:**

Должно быть:
```
3000
```

### 4. **Проверьте Root Directory (если используется)**

**Mini App сервис → Settings → Source → Root Directory:**

Должно быть:
```
frontend
```

Или оставьте пустым, если Dockerfile Path: `frontend/Dockerfile`

### 5. **Проверьте логи сборки**

**Mini App → Deployments → последний deployment → Logs**

Ищите:
- ✅ `npm ci` - успешно
- ✅ `npm run build` - успешно  
- ✅ `Creating an optimized production build`
- ✅ `Ready on http://0.0.0.0:3000`

Если есть ошибки - исправьте их.

### 6. **Пересоберите сервис**

**Mini App → Deployments → Redeploy**

## 🔍 Типичные ошибки

### Ошибка 1: "Cannot find module '@twa-dev/sdk'"

**Решение:** 
- Проверьте `package.json` - должен быть `"@twa-dev/sdk": "^1.0.0"`
- Пересоберите сервис

### Ошибка 2: "Cannot find module './server.js'"

**Решение:**
- Убедитесь, что `next.config.js` имеет `output: 'standalone'`
- Пересоберите сервис

### Ошибка 3: "Port 3000 is already in use"

**Решение:**
- Убедитесь, что в Railway Port = 3000
- Убедитесь, что `PORT=3000` в переменных

## 📋 Чеклист для Mini App

**Settings → Variables:**
- ✅ `PORT=3000`
- ✅ `NODE_ENV=production`
- ✅ `NEXT_PUBLIC_API_URL=https://hrbot-production-f67c.up.railway.app`
- ✅ `BACKEND_URL=https://hrbot-production-f67c.up.railway.app`
- ❌ УДАЛИТЬ: `DATABASE_URL`
- ❌ УДАЛИТЬ: `QDRANT_HOST`
- ❌ УДАЛИТЬ: `TELEGRAM_TOKEN`

**Settings → Build:**
- ✅ Dockerfile Path: `frontend/Dockerfile`

**Settings → Networking:**
- ✅ Port: `3000`

## 🎯 После исправления

1. Сохраните изменения
2. Railway автоматически пересоберет сервис
3. Дождитесь завершения сборки
4. Проверьте: `https://mini-app-production-153f.up.railway.app/`
5. Должна открыться главная страница Next.js
