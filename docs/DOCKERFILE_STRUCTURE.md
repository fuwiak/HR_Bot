# 📁 Структура Dockerfile в проекте

## ✅ Dockerfile в корне проекта

Все Dockerfile для Railway должны находиться в **корне проекта**, так как Railway ищет их там:

```
/
├── Dockerfile              # (старый, можно удалить или оставить для совместимости)
├── Dockerfile.telegram     # ✅ Для Telegram Bot сервиса
├── Dockerfile.backend      # ✅ Для Backend API сервиса
├── Dockerfile.frontend     # ✅ Для Frontend (старый, не используется)
├── Dockerfile.yadisk       # ✅ Для Yandex Disk Indexer
│
├── frontend/
│   └── Dockerfile         # ✅ Для Mini App (используется через .railway/frontend.toml)
│
├── backend/
│   └── Dockerfile         # (не используется, есть Dockerfile.backend в корне)
│
└── telegram_bot/
    └── Dockerfile         # (не используется, есть Dockerfile.telegram в корне)
```

## 🎯 Конфигурация в .railway/

Каждый сервис имеет свой файл конфигурации:

```
.railway/
├── telegram-bot.toml  → Dockerfile.telegram
├── backend.toml       → Dockerfile.backend
├── frontend.toml      → frontend/Dockerfile
└── yadisk-indexer.toml → Dockerfile.yadisk
```

## ⚠️ Важно

Railway **не может** использовать Dockerfile из подкаталогов напрямую (кроме случаев, когда это указано явно в конфигурации).

Для сервисов, которые используют Dockerfile из подкаталогов (например, `frontend/Dockerfile`), Railway:
1. Проверяет `.railway/{service}.toml`
2. Использует `dockerfilePath` из этого файла
3. Если путь относительный (например, `frontend/Dockerfile`), Railway ищет его относительно корня проекта

## 📋 Checklist

- [x] `Dockerfile.telegram` создан в корне
- [x] `Dockerfile.backend` существует в корне
- [x] `Dockerfile.yadisk` существует в корне
- [x] `frontend/Dockerfile` существует (используется для Mini App)
- [x] `.railway/telegram-bot.toml` указывает на `Dockerfile.telegram`
- [x] `.railway/backend.toml` указывает на `Dockerfile.backend`
- [x] `.railway/frontend.toml` указывает на `frontend/Dockerfile`
- [x] `.railway/yadisk-indexer.toml` указывает на `Dockerfile.yadisk`

## 🔍 Почему Railway ищет Dockerfile.telegram?

Railway может автоматически пытаться найти `Dockerfile.{service-name}`, если:
- В конфигурации указано только имя сервиса
- Или Railway использует соглашение об именовании

Поэтому лучше явно указать `Dockerfile.telegram` в `.railway/telegram-bot.toml`.
