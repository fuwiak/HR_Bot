# ⚡ Быстрая настройка Mini App через BotFather

## 🎯 За 3 шага

### 1️⃣ Получите URL Frontend в Railway
```
Railway Dashboard → Frontend → Settings → Networking → Public Domain
Скопируйте: https://frontend-xxxx.up.railway.app
Добавьте /miniapp: https://frontend-xxxx.up.railway.app/miniapp
```

### 2️⃣ Настройте BotFather
```
1. Откройте @BotFather в Telegram
2. Отправьте: /mybots
3. Выберите вашего бота
4. Bot Settings → Menu Button → Configure Menu Button
5. Текст: 🌐 Открыть Mini App
6. URL: https://frontend-xxxx.up.railway.app/miniapp
```

### 3️⃣ Добавьте переменную в Railway
```
Railway Dashboard → Telegram Bot → Settings → Variables
Добавьте:
MINI_APP_URL=https://frontend-xxxx.up.railway.app/miniapp
```

## ✅ Готово!

Теперь в боте появится кнопка "🌐 Открыть Mini App" внизу экрана.

## 📝 Примечание

Кнопка также автоматически добавится в меню `/start`, если `MINI_APP_URL` настроен.

---
📚 Полная инструкция: [MINIAPP_BOTFATHER_SETUP.md](./MINIAPP_BOTFATHER_SETUP.md)
