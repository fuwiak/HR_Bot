# 🔧 Исправление ошибки '/frontend': not found в Railway

## ❌ Проблема

Railway не может найти каталог `frontend/` при сборке:
```
Build Failed: failed to calculate checksum: "/frontend": not found
```

## 🔍 Причина

Railway использует **корень проекта** как build context, но когда Dockerfile находится в `frontend/Dockerfile`, Railway может неправильно обрабатывать пути.

## ✅ Решение

Использовать `Dockerfile.frontend` из **корня проекта** вместо `frontend/Dockerfile`:

### Изменение в `.railway/frontend.toml`:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile.frontend"  # ✅ В корне проекта
```

**Вместо:**
```toml
dockerfilePath = "frontend/Dockerfile"  # ❌ В подкаталоге
```

## 📁 Структура

```
/
├── Dockerfile.frontend     # ✅ Используется для Mini App
├── frontend/
│   ├── Dockerfile          # (не используется Railway, только для локальной разработки)
│   ├── package.json
│   └── ...
```

## 🎯 Почему это работает

1. **Dockerfile.frontend** находится в корне проекта
2. Railway использует корень как build context
3. Пути `COPY frontend/package.json` работают правильно
4. Нет проблем с поиском каталога `frontend/`

## 📋 Проверка

После изменения в `.railway/frontend.toml`:

1. Railway автоматически пересоберет сервис
2. В логах должно быть:
   ```
   Building with Dockerfile: Dockerfile.frontend
   COPY frontend/package.json frontend/package-lock.json* ./
   ✅ package.json найден
   ```

3. **НЕ должно быть:**
   ```
   "/frontend": not found
   ```

## 💡 Альтернативное решение

Если нужно использовать `frontend/Dockerfile`, можно:
1. Установить build context в Railway Dashboard
2. Но проще использовать `Dockerfile.frontend` из корня
