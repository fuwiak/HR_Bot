# Email Manager — скилл агента AnythingLLM

Проверка последних N писем в Yandex и ответы на них. Агент вызывает скилл с параметрами; письма забираются через backend HR_Bot (IMAP Yandex).

## Требования

- Node.js 18+
- AnythingLLM с поддержкой custom agent skills (формат `runtime` + `entrypoint`)
- **Backend HR_Bot** с настроенной почтой Yandex и эндпоинтами:
  - `GET /api/email/recent?limit=N`
  - `POST /api/email/reply` (body: `to_email`, `subject`, `content`)

## Настройка

1. В AnythingLLM: **Agents → Skills** → включите скилл **«Email Manager»**.

2. В настройках скилла (Setup) укажите **HR_BOT_BACKEND_URL** — URL бэкенда **без слэша в конце**, например:  
   `https://backend-production-099b.up.railway.app`  
   (альтернативно можно задать переменную окружения AnythingLLM.)

3. Агент будет вызывать скилл по параметрам. Примеры фраз в чате, на которые агент должен вызвать скилл:
   - «Покажи последние 5 писем с Yandex» → `action=list`, `limit=5`
   - «Проверь почту» / «Покажи последние письма» → `action=list`, `limit=10`
   - «Покажи письмо номер 1» → `action=get`, `email_number=1`
   - «Ответь на письмо 2: Добрый день, высылаю информацию.» → `action=reply`, `email_number=2`, `reply_text=...`

## Параметры вызова (entrypoint)

| Параметр       | Тип    | Описание |
|----------------|--------|----------|
| **action**     | string | `list` — список писем, `get` — показать одно письмо, `reply` — отправить ответ |
| **limit**      | number | Для `action=list`: сколько писем показать (по умолчанию 10, макс. 20) |
| **email_number** | number | Номер письма в списке (1 = самое новое). Для `get` и `reply` |
| **reply_text** | string | Текст ответа. Для `action=reply` |

## Примеры вызовов (для агента)

- Список последних 5 писем:  
  `{"action": "list", "limit": 5}`

- Список последних 10 писем:  
  `{"action": "list", "limit": 10}`

- Показать письмо №1 (последнее):  
  `{"action": "get", "email_number": 1}`

- Ответить на письмо №2:  
  `{"action": "reply", "email_number": 2, "reply_text": "Добрый день, высылаю информацию по запросу."}`

В `plugin.json` заданы примеры (examples), чтобы LLM понимал, когда и с какими параметрами вызывать скилл.

## Где это работает

- **Чат AnythingLLM** — пользователь пишет «покажи последние 5 писем», «письмо 1», «ответь на письмо 2: …»; агент вызывает Email Manager с нужными параметрами и возвращает результат.
- **Telegram** — по-прежнему доступны `/email_check`, уведомления в канал и кнопка «Подготовить ответ».
