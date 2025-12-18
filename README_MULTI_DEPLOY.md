# 🚂 Деплой трех сервисов на Railway

## ✅ Что готово

Созданы отдельные Dockerfile для каждого сервиса:

- **Dockerfile.telegram** - Telegram Bot (порт 8080)
- **Dockerfile.backend** - Backend API (порт 8081)  
- **Dockerfile.frontend** - Frontend Next.js (порт 3000)

## 🚀 Быстрый деплой

### 1. Создайте проект на Railway

1. https://railway.app → **New Project** → **Empty Project**

### 2. Создайте Telegram Bot сервис

1. **"+ New"** → **"GitHub Repo"** → `HR_Bot`
2. **Settings** → **Build** → **Dockerfile Path**: `Dockerfile.telegram`
3. **Networking** → **Generate Domain**
4. **Variables**: `TELEGRAM_TOKEN`, `OPENROUTER_API_KEY`, `USE_WEBHOOK=true`, `PORT=8080`

### 3. Создайте Backend сервис

1. **"+ New"** → **"GitHub Repo"** → `HR_Bot`
2. **Settings** → **Build** → **Dockerfile Path**: `Dockerfile.backend`
3. **Networking** → **Generate Domain** → **СКОПИРУЙТЕ URL**
4. **Variables**: `WEB_INTERFACE_PORT=8081`, `PORT=8081`, `SECRET_KEY`

### 4. Создайте Frontend сервис

1. **"+ New"** → **"GitHub Repo"** → `HR_Bot`
2. **Settings** → **Build** → **Dockerfile Path**: `Dockerfile.frontend`
3. **Networking** → **Generate Domain**
4. **Variables**:
   ```
   PORT=3000
   NODE_ENV=production
   NEXT_PUBLIC_API_URL=https://ВАШ_BACKEND_URL.up.railway.app
   BACKEND_URL=https://ВАШ_BACKEND_URL.up.railway.app
   ```
   ⚠️ Замените на URL из шага 3!

### 5. Общие переменные

**Project Settings** → **Variables**:
```
QDRANT_URL=...
QDRANT_API_KEY=...
OPENROUTER_API_KEY=...
```

## 📚 Документация

- **RAILWAY_DEPLOY_MULTI.md** - полная инструкция
- **RAILWAY_QUICK_MULTI.md** - быстрый старт
- **DEPLOY_MULTI_SERVICES.md** - краткая инструкция

---

**Готово! 🚂**
