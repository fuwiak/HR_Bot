# ⚡ Быстрая настройка Mini App URL

## 🎯 Для вашего случая

### URL Mini App:
```
https://mini-app-production-3766.up.railway.app
```

## 📋 Переменные в Railway

### 1. В сервисе **Mini App** (Frontend):

```env
PORT=3000
NODE_ENV=production
```

**Больше ничего не нужно!** Mini App не требует других переменных.

### 2. В сервисе **Telegram Bot**:

```env
MINI_APP_URL=https://mini-app-production-3766.up.railway.app
```

## ✅ Проверка

После настройки в логах Telegram Bot должно появиться:
```
🌐 Mini App URL настроен: https://mini-app-production-3766.up.railway.app
🌐 Добавлена кнопка Mini App с URL: https://mini-app-production-3766.up.railway.app
```

## 🔧 Настройка в BotFather

1. Откройте [@BotFather](https://t.me/BotFather)
2. `/mybots` → выберите бота → **Bot Settings** → **Menu Button**
3. URL: `https://mini-app-production-3766.up.railway.app`

## 📚 Полная документация

- [Переменные для Mini App](./MINIAPP_RAILWAY_VARIABLES.md)
- [Настройка через BotFather](./MINIAPP_BOTFATHER_SETUP.md)
