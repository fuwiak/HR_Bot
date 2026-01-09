# 🔴 Переменные Redis для Telegram Bot сервиса

## Проблема
В Telegram Bot сервисе отсутствуют переменные Redis, поэтому сообщения не попадают в Redis.

## Решение: Добавьте эти переменные в Telegram Bot сервис

### Способ 1: Использование ссылок на Redis сервис (рекомендуется)

В Railway Dashboard → Telegram Bot сервис → Variables → Add Variable

Добавьте эти переменные (используя синтаксис Railway для ссылки на Redis сервис):

```bash
REDIS_URL="${{Redis.REDIS_URL}}"
REDIS_PUBLIC_URL="${{Redis.REDIS_PUBLIC_URL}}"
REDISHOST="${{Redis.REDISHOST}}"
REDISPORT="${{Redis.REDISPORT}}"
REDISPASSWORD="${{Redis.REDISPASSWORD}}"
REDISUSER="${{Redis.REDISUSER}}"
```

### Способ 2: Прямые значения (если способ 1 не работает)

Если синтаксис `${{Redis.Variable}}` не работает, используйте прямые значения из Redis сервиса:

```bash
REDIS_URL="redis://default:dOtplDwxGYbSFNteobFpQttOxwaMbnEx@${{RAILWAY_PRIVATE_DOMAIN}}:6379"
REDIS_PUBLIC_URL="redis://default:dOtplDwxGYbSFNteobFpQttOxwaMbnEx@${{RAILWAY_TCP_PROXY_DOMAIN}}:${{RAILWAY_TCP_PROXY_PORT}}"
REDISHOST="${{RAILWAY_PRIVATE_DOMAIN}}"
REDISPORT="6379"
REDISPASSWORD="dOtplDwxGYbSFNteobFpQttOxwaMbnEx"
REDISUSER="default"
```

### Способ 3: Через Railway Shared Variables (автоматически)

Railway должен автоматически предоставлять переменные Redis другим сервисам. Если этого не происходит:

1. Убедитесь, что Redis и Telegram Bot сервисы в **одном проекте Railway**
2. Railway Dashboard → Redis сервис → Settings → убедитесь, что "Share Variables" включено
3. Перезапустите Telegram Bot сервис

## Проверка

После добавления переменных:

1. Перезапустите Telegram Bot сервис (Redeploy)
2. Проверьте логи - должны увидеть:
   ```
   ✅ Redis клиент создан через REDIS_URL
   ✅ Redis подключение успешно через REDIS_URL
   🔄 Запущена фоновая синхронизация Redis -> PostgreSQL
   ```

## Текущие переменные Redis сервиса

Из вашего списка:
- `REDIS_PASSWORD="dOtplDwxGYbSFNteobFpQttOxwaMbnEx"`
- `REDIS_URL="redis://default:${{REDIS_PASSWORD}}@${{RAILWAY_PRIVATE_DOMAIN}}:6379"`
- `REDIS_PUBLIC_URL="redis://default:${{REDIS_PASSWORD}}@${{RAILWAY_TCP_PROXY_DOMAIN}}:${{RAILWAY_TCP_PROXY_PORT}}"`
- `REDISHOST="${{RAILWAY_PRIVATE_DOMAIN}}"`
- `REDISPORT="6379"`
- `REDISUSER="default"`

Эти переменные должны быть доступны в Telegram Bot сервисе!
