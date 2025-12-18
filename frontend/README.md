# HR2137 Bot Frontend (Next.js)

Frontend приложение для HR2137 Bot, переписанное на Next.js 14 с сохранением всей функциональности.

## Установка

```bash
npm install
```

## Разработка

```bash
npm run dev
```

Приложение будет доступно на http://localhost:3000

**Важно**: FastAPI backend должен быть запущен на http://localhost:8081

## Переменные окружения

Создайте файл `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8081
```

## Структура

- `/app` - страницы Next.js (App Router)
  - `page.tsx` - главная страница
  - `architecture/page.tsx` - страница архитектуры
  - `rag/page.tsx` - RAG Dashboard
- `/components` - React компоненты
  - `LayoutWrapper.tsx` - общий layout с сайдбаром
- `/lib` - утилиты и API клиент
  - `api.ts` - функции для работы с FastAPI backend

## Функциональность

- ✅ Главная страница с демо формами (Email, КП, RAG поиск)
- ✅ Страница архитектуры системы
- ✅ Полный RAG Dashboard с табами:
  - Обзор (статус, быстрые действия)
  - Векторная БД (информация о коллекции)
  - Метрики (Precision@K, MRR, Groundedness)
  - Workflow (загрузка, оценка, анализ)
  - Файлы (управление документами)
  - Тест (тестовые запросы к RAG)
- ✅ Интеграция с FastAPI backend через API клиент
- ✅ Сохранены все функции оригинального интерфейса
- ✅ Адаптивный дизайн (Facebook-like UI)

## Технологии

- Next.js 14 (App Router)
- React 18
- TypeScript
- CSS Modules

## Сборка для production

```bash
npm run build
npm start
```

## Деплой

Next.js приложение можно задеплоить на:
- Vercel (рекомендуется)
- Railway
- Docker
- Любой Node.js хостинг
