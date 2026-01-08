# ⚡ Быстрый деплой трех сервисов на Railway

Минимальная инструкция для деплоя Telegram Bot, Backend и Frontend как отдельных сервисов.

## 🎯 За 15 минут

### 1. Создайте проект на Railway (2 мин)

1. https://railway.app → **New Project** → **Empty Project**

### 2. Создайте Telegram Bot сервис (3 мин)

1. **"+ New"** → **"GitHub Repo"** → `HR_Bot`
2. **Settings** → **Build** → **Dockerfile Path**: `Dockerfile.telegram`
3. **Networking** → **Generate Domain**
4. **Variables**:
   ```
   TELEGRAM_TOKEN=your_token
   OPENROUTER_API_KEY=your_key
   USE_WEBHOOK=true
   PORT=8080
   ```

### 3. Создайте Backend сервис (3 мин)

1. **"+ New"** → **"GitHub Repo"** → `HR_Bot`
2. **Settings** → **Build** → **Dockerfile Path**: `Dockerfile.backend`
3. **Networking** → **Generate Domain** → **СКОПИРУЙТЕ URL**
4. **Variables**:
   ```
   WEB_INTERFACE_PORT=8081
   PORT=8081
   SECRET_KEY=random-secret-key
   ```

### 4. Создайте Frontend сервис (4 мин)

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
   ⚠️ **Замените на URL из шага 3!**

### 5. Общие переменные (3 мин)

**Project Settings** → **Variables**:
```
QDRANT_URL=your_url
QDRANT_API_KEY=your_key
OPENROUTER_API_KEY=your_key
```

## ✅ Готово!

- Telegram Bot: работает на своем домене
- Backend: работает на своем домене  
- Frontend: работает на своем домене и подключается к Backend

## 🔍 Проверка

1. Telegram: отправьте `/start`
2. Backend: `https://backend-url/health`
3. Frontend: `https://frontend-url`

---

**⏱️ Время: ~15 минут**

**📖 Подробнее**: 
- `RAILWAY_DEPLOY_MULTI.md` - полная инструкция
- `RAILWAY_AUTO_SETUP.md` - автоматическая настройка Dockerfile Path

**🔧 Автоматическая настройка**:
```bash
# Используйте скрипт для автоматической настройки
./setup_railway_services.sh
```
